<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, fileUrl } from '../api'

const route = useRoute()
const id = route.params.id
const article = ref(null)
const edit = ref({ title: '', body: '', image_prompt: '' })
const candidates = ref([])
const pickedTitle = ref('')
const regenCount = ref(1)
const busy = ref('')
const statusText = { draft: '草稿', approved: '已通过', published: '已发布' }

async function load() {
  const { data } = await api.get(`/articles/${id}`)
  article.value = data
  edit.value.title = data.title
  edit.value.body = data.body
  edit.value.image_prompt = data.image_prompt
  const flat = []
  for (const c of data.title_candidates || []) {
    for (const t of c.titles || []) flat.push({ conflict: c.conflict, title: t })
  }
  candidates.value = flat.filter((x) => x.title !== data.title)
}

async function saveField(field) {
  busy.value = `save_${field}`
  try {
    const { data } = await api.patch(`/articles/${id}`, { [field]: edit.value[field] })
    article.value = data
    if (field === 'title') {
      candidates.value = candidates.value.filter((x) => x.title !== data.title)
    }
    ElMessage.success('已保存')
  } finally {
    busy.value = ''
  }
}

async function regen(kind, payload) {
  busy.value = kind
  try {
    const url = `/articles/${id}/regen-${kind}`
    let data
    if (payload) {
      ;({ data } = await api.post(url, payload))
    } else {
      ;({ data } = await api.post(url))
    }
    article.value = data
    if (kind === 'body') {
      edit.value.body = data.body
    }
  } catch {
    ElMessage.error('生成失败，请重试')
  } finally {
    busy.value = ''
  }
}

async function adoptTitle() {
  if (!pickedTitle.value) return
  edit.value.title = pickedTitle.value
  await saveField('title')
}

async function setStatus(status) {
  busy.value = 'status'
  try {
    const { data } = await api.post(`/articles/${id}/status`, { status })
    article.value = data
  } finally {
    busy.value = ''
  }
}

function copyText() {
  const text = `${article.value.title}\n\n${article.value.body}`
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('已复制标题与正文'),
    () => ElMessage.error('复制失败，请手动选择文本'),
  )
}

const previewImages = computed(() =>
  (article.value?.image_paths || []).map((p) => fileUrl(p)),
)

onMounted(load)
</script>

<template>
  <div v-if="article">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <el-tag :type="article.status === 'draft' ? 'info' : article.status === 'approved' ? 'success' : 'warning'">
        {{ statusText[article.status] }}
      </el-tag>
      <el-radio-group :model-value="article.status" size="small" @change="setStatus">
        <el-radio-button value="draft">草稿</el-radio-button>
        <el-radio-button value="approved">通过</el-radio-button>
        <el-radio-button value="published">已发布</el-radio-button>
      </el-radio-group>
      <div style="flex:1"></div>
      <el-button @click="copyText">复制文案</el-button>
      <a :href="`/api/articles/${id}/export.zip`">
        <el-button type="primary" plain>下载 zip</el-button>
      </a>
    </div>

    <el-row :gutter="20">
      <el-col :span="10">
        <el-card header="公众号预览">
          <div style="background:#fff;padding:16px;border-radius:6px">
            <h2 style="font-size:18px;line-height:1.5;margin:0 0 12px">{{ article.title }}</h2>
            <p style="color:#555;line-height:1.8;white-space:pre-wrap;margin:0 0 12px">{{ article.body }}</p>
            <el-image
              v-for="(src, i) in previewImages"
              :key="i"
              :src="src"
              fit="cover"
              style="width:100%;margin-bottom:8px;display:block"
              :preview-src-list="previewImages"
              :initial-index="i"
            />
            <div style="color:#999;font-size:12px;text-align:center">{{ article.mood }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card header="标题">
          <el-input v-model="edit.title" />
          <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center">
            <el-select v-model="pickedTitle" placeholder="候选标题" clearable style="flex:1;min-width:260px">
              <el-option v-for="c in candidates" :key="c.title" :label="`${c.title}（${c.conflict}）`" :value="c.title" />
            </el-select>
            <el-button @click="adoptTitle">采用</el-button>
            <el-button type="primary" :loading="busy === 'save_title'" @click="saveField('title')">保存标题</el-button>
          </div>
        </el-card>

        <el-card header="正文（30–60字）" style="margin-top:16px">
          <el-input v-model="edit.body" type="textarea" :rows="4" />
          <div style="margin-top:10px;display:flex;gap:10px">
            <span style="color:#999;font-size:12px;line-height:32px">当前字数：{{ edit.body.length }}</span>
            <div style="flex:1"></div>
            <el-button :loading="busy === 'body'" @click="regen('body')">重写正文</el-button>
            <el-button type="primary" :loading="busy === 'save_body'" @click="saveField('body')">保存正文</el-button>
          </div>
        </el-card>

        <el-card header="配图" style="margin-top:16px">
          <el-input v-model="edit.image_prompt" type="textarea" :rows="3" placeholder="图片提示词，可手动修改后重新生图" />
          <div style="margin-top:10px;display:flex;gap:10px;align-items:center">
            <span>数量</span>
            <el-input-number v-model="regenCount" :min="1" :max="3" />
            <el-button :loading="busy === 'images'" @click="saveField('image_prompt')">保存提示词</el-button>
            <el-button type="primary" :loading="busy === 'images'" @click="regen('images', { count: regenCount })">
              重新生图
            </el-button>
          </div>
          <el-row :gutter="8" style="margin-top:12px">
            <el-col v-for="(src, i) in previewImages" :key="i" :span="8">
              <el-image :src="src" fit="cover" style="width:100%;height:160px" />
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
