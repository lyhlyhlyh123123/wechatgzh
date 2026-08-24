<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const step = ref(0)
const topics = ref([])
const presets = ref([])
const form = reactive({ topic_id: null, idea: '', size: '', count: 1 })
const candidates = ref([])
const sel = reactive({ c: 0, t: 0 })
const drafting = ref(false)
const building = ref(false)

const currentCandidate = computed(() => candidates.value[sel.c] || null)
const currentTitle = computed(() => currentCandidate.value?.titles[sel.t] || '')

onMounted(async () => {
  const [t, p, s] = await Promise.all([
    api.get('/topics', { params: { enabled: true } }),
    api.get('/presets'),
    api.get('/settings'),
  ])
  topics.value = t.data.items
  presets.value = p.data
  form.size = p.data[0]?.size || '1080x1620'
  form.count = s.data.image_count_default || 1
})

async function draft() {
  if (!form.topic_id && !form.idea.trim()) {
    ElMessage.warning('请选择一个主题，或输入你的想法')
    return
  }
  drafting.value = true
  try {
    const { data } = await api.post('/generation/draft-conflicts', {
      topic_id: form.topic_id,
      idea: form.idea,
    })
    candidates.value = data.candidates
    sel.c = 0
    sel.t = 0
    step.value = 1
  } catch {
    ElMessage.error('生成冲突失败，请检查 API 配置或重试')
  } finally {
    drafting.value = false
  }
}

async function build() {
  building.value = true
  try {
    const { data } = await api.post('/generation/build', {
      topic_id: form.topic_id,
      conflict: currentCandidate.value.conflict,
      title: currentTitle.value,
      image_size: form.size,
      image_count: form.count,
      candidates: candidates.value,
    })
    router.push(`/articles/${data.id}`)
  } catch {
    ElMessage.error('成稿失败，请重试')
  } finally {
    building.value = false
  }
}
</script>

<template>
  <el-card>
    <el-steps :active="step" align-center finish-status="success" style="margin-bottom:24px">
      <el-step title="选主题" />
      <el-step title="挑冲突与标题" />
      <el-step title="成稿" />
    </el-steps>

    <div v-if="step === 0" v-loading="drafting" style="max-width:640px;margin:0 auto">
      <el-form label-width="90px">
        <el-form-item label="主题库">
          <el-select v-model="form.topic_id" placeholder="从主题库选择（可选）" clearable filterable style="width:100%">
            <el-option
              v-for="t in topics"
              :key="t.id"
              :label="`[${t.drive_type}] ${t.category} · ${t.conflict}`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="自由想法">
          <el-input v-model="form.idea" type="textarea" :rows="2" placeholder="不选主题时，直接写你想要的冲突方向" />
        </el-form-item>
        <el-form-item label="图片尺寸">
          <el-select v-model="form.size" style="width:100%">
            <el-option v-for="p in presets" :key="p.size" :label="`${p.label}（${p.size}）`" :value="p.size" />
          </el-select>
        </el-form-item>
        <el-form-item label="图片数量">
          <el-input-number v-model="form.count" :min="1" :max="3" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="drafting" @click="draft">生成冲突与标题</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-else-if="step === 1" v-loading="building">
      <h3>第一步：选一个冲突</h3>
      <el-radio-group v-model="sel.c" style="display:flex;flex-direction:column;gap:10px">
        <el-radio v-for="(c, i) in candidates" :key="i" :value="i" border style="margin:0;padding:12px;height:auto">
          {{ c.conflict }}
        </el-radio>
      </el-radio-group>

      <h3 style="margin-top:20px">第二步：选一个标题</h3>
      <el-radio-group v-model="sel.t" style="display:flex;flex-direction:column;gap:10px">
        <el-radio v-for="(t, i) in currentCandidate?.titles || []" :key="i" :value="i" border style="margin:0;padding:12px;height:auto">
          {{ t }}
        </el-radio>
      </el-radio-group>

      <div style="margin-top:20px;display:flex;gap:12px">
        <el-button @click="step = 0">上一步</el-button>
        <el-button type="primary" :disabled="!currentTitle" :loading="building" @click="build">
          一键成稿（正文+配图）
        </el-button>
      </div>
    </div>
  </el-card>
</template>
