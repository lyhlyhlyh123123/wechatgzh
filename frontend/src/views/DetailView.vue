<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref, watch } from 'vue'
import { api, fileUrl } from '../api'

const props = defineProps({ articleId: Number })
const article = ref(null)
const busy = ref('')
const statusText = { draft: '草稿', approved: '已通过', published: '已发布' }
const editTitle = ref('')
const editBody = ref('')
const previewVisible = ref(false)
const previewIndex = ref(0)

async function load() {
  if (!props.articleId) return
  const { data } = await api.get(`/articles/${props.articleId}`)
  article.value = data
  editTitle.value = data.title
  editBody.value = data.body
}

function pickTitle(t) {
  editTitle.value = t
}

async function saveTitle() {
  busy.value = 'save_title'
  try {
    const { data } = await api.patch(`/articles/${props.articleId}`, { title: editTitle.value })
    article.value = data
    ElMessage.success('标题已保存')
  } finally { busy.value = '' }
}

async function saveBody() {
  busy.value = 'save_body'
  try {
    const { data } = await api.patch(`/articles/${props.articleId}`, { body: editBody.value })
    article.value = data
    ElMessage.success('正文已保存')
  } finally { busy.value = '' }
}

async function setStatus(status) {
  busy.value = 'status'
  try {
    const { data } = await api.patch(`/articles/${props.articleId}`, { status })
    article.value = data
    ElMessage.success('已更新')
  } finally { busy.value = '' }
}

async function remove() {
  await api.delete(`/articles/${props.articleId}`)
  ElMessage.success('已删除')
  article.value = null
}

function copyText() {
  const text = `${article.value.title}\n\n${article.value.body}`
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('已复制'),
    () => ElMessage.error('复制失败'),
  )
}

function openPreview(i) { previewIndex.value = i; previewVisible.value = true }

function previewImages() {
  return (article.value?.image_paths || []).map(p => fileUrl(p))
}

watch(() => props.articleId, load)
onMounted(load)
</script>

<template>
  <div v-if="article" style="padding:24px;max-width:640px;margin:0 auto">

    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
      <el-tag :type="{draft:'info',approved:'success',published:'warning'}[article.status]" size="small">{{ statusText[article.status] }}</el-tag>
      <span style="color:#999;font-size:12px">{{ new Date(article.created_at).toLocaleString('zh-CN') }}</span>
    </div>

    <!-- 标题候选 -->
    <div v-if="article.title_candidates" style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">标题候选（点击选用）</div>
      <div v-for="(t,i) in (Array.isArray(article.title_candidates)?article.title_candidates:[])" :key="i"
        style="padding:6px 8px;font-size:14px;border-radius:4px;cursor:pointer;transition:background .15s;border-bottom:1px solid #f5f5f5"
        @click="pickTitle(typeof t==='string'?t:(t.titles?t.titles[0]:t))">
        <template v-if="typeof t==='string'">
          <span :style="{color: t===editTitle?'#409eff':'#303133',fontWeight: t===editTitle?'600':'400'}">{{ t }}</span>
        </template>
        <template v-else-if="t.titles">
          <div v-for="(tt,j) in t.titles" :key="j"
            style="padding:3px 0"
            :style="{color: tt===editTitle?'#409eff':'#303133',fontWeight: tt===editTitle?'600':'400'}">
            {{ tt }}
          </div>
        </template>
      </div>
    </div>

    <!-- 标题编辑 -->
    <div style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="display:flex;gap:8px;align-items:center">
        <el-input v-model="editTitle" size="small" placeholder="标题" />
        <el-button type="primary" size="small" :loading="busy==='save_title'" @click="saveTitle">保存标题</el-button>
      </div>
    </div>

    <!-- 正文编辑 -->
    <div style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">正文（{{ editBody.length }}字）</div>
      <el-input v-model="editBody" type="textarea" :rows="5" placeholder="正文内容" />
      <div style="margin-top:8px;text-align:right">
        <el-button type="primary" size="small" :loading="busy==='save_body'" @click="saveBody">保存正文</el-button>
      </div>
    </div>

    <!-- 情绪标签 -->
    <div v-if="article.mood" style="background:#fff;border-radius:8px;padding:10px 14px;margin-bottom:10px;border:1px solid #ebeef5">
      <span style="font-size:12px;color:#909399">情绪标签：</span>
      <el-tag size="small">{{ article.mood }}</el-tag>
    </div>

    <!-- 图片提示词 -->
    <div style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">图片提示词</div>
      <div style="font-size:13px;color:#606266;line-height:1.6;word-break:break-all">{{ article.image_prompt }}</div>
    </div>

    <!-- 生成图片 -->
    <div v-if="article.image_paths?.length" style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:8px">生成图片（点击查看大图）</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <el-image v-for="(p,i) in article.image_paths" :key="i" :src="fileUrl(p)" fit="cover"
          style="width:180px;height:240px;border-radius:8px;cursor:pointer"
          @click="openPreview(i)"
          :preview-src-list="previewImages()" :initial-index="i" hide-on-click-modal />
      </div>
    </div>

    <!-- 操作按钮 -->
    <div style="display:flex;gap:8px;margin-top:14px">
      <el-button v-if="article.status==='draft'" type="success" size="small" @click="setStatus('approved')">通过</el-button>
      <el-button v-if="article.status==='approved'" type="warning" size="small" @click="setStatus('published')">发布</el-button>
      <el-button v-if="article.status==='published'" size="small" @click="setStatus('draft')">撤回</el-button>
      <el-button size="small" @click="copyText">复制文案</el-button>
      <div style="flex:1"></div>
      <el-button type="danger" size="small" @click="remove">删除</el-button>
    </div>
  </div>
  <div v-else-if="props.articleId" v-loading="true" style="padding:40px"></div>
  <div v-else style="text-align:center;color:#c0c4cc;padding-top:100px">
    <div style="font-size:48px;margin-bottom:12px">📝</div>
    <div>选择历史记录查看详情</div>
  </div>
</template>
