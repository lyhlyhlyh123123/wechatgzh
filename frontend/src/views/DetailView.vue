<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref, watch } from 'vue'
import { api, fileUrl } from '../api'

const props = defineProps({ articleId: Number })
const article = ref(null)
const busy = ref('')
const statusText = { draft: '草稿', approved: '已通过', published: '已发布' }

async function load() {
  if (!props.articleId) return
  const { data } = await api.get(`/articles/${props.articleId}`)
  article.value = data
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

async function exportArticle() {
  try {
    const resp = await api.get(`/articles/${props.articleId}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a'); a.href = url; a.download = `${article.value.title||'article'}.html`; a.click()
    URL.revokeObjectURL(url)
  } catch { ElMessage.error('导出失败') }
}

function copyText() {
  const text = `${article.value.title}\n\n${article.value.body}`
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('已复制'),
    () => ElMessage.error('复制失败'),
  )
}

watch(() => props.articleId, load)
onMounted(load)
</script>

<template>
  <div v-if="article" style="padding:24px;max-width:640px;margin:0 auto">
    <h2 style="font-size:18px;margin:0 0 8px">{{ article.title }}</h2>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:16px">
      <el-tag :type="{draft:'info',approved:'success',published:'warning'}[article.status]" size="small">{{ statusText[article.status] }}</el-tag>
      <span style="color:#999;font-size:12px">{{ new Date(article.created_at).toLocaleString('zh-CN') }}</span>
    </div>

    <div v-if="article.title_candidates" style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">标题候选</div>
      <div v-for="(t,i) in (Array.isArray(article.title_candidates)?article.title_candidates:[])" :key="i" style="padding:4px 0;font-size:14px;border-bottom:1px solid #f5f5f5">
        <template v-if="typeof t==='string'">{{ t }}</template>
        <template v-else-if="t.titles"><div v-for="(tt,j) in t.titles" :key="j" style="padding:2px 0">{{ tt }}</div></template>
      </div>
    </div>

    <div style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">正文</div>
      <div style="font-size:15px;line-height:1.8;white-space:pre-wrap">{{ article.body }}</div>
    </div>

    <div v-if="article.mood" style="background:#fff;border-radius:8px;padding:10px 14px;margin-bottom:10px;border:1px solid #ebeef5">
      <span style="font-size:12px;color:#909399">情绪标签：</span>
      <el-tag size="small">{{ article.mood }}</el-tag>
    </div>

    <div style="background:#fff;border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid #ebeef5">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">图片提示词</div>
      <div style="font-size:13px;color:#606266;line-height:1.6;word-break:break-all">{{ article.image_prompt }}</div>
    </div>

    <div v-if="article.image_paths?.length" style="margin-bottom:10px">
      <div style="font-size:12px;color:#909399;margin-bottom:6px">生成图片</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <el-image v-for="(p,i) in article.image_paths" :key="i" :src="fileUrl(p)" fit="cover" style="width:180px;height:240px;border-radius:8px">
          <template #error><div style="width:180px;height:240px;background:#f5f5f5;border-radius:8px"></div></template>
        </el-image>
      </div>
    </div>

    <div style="display:flex;gap:8px;margin-top:14px">
      <el-button v-if="article.status==='draft'" type="success" size="small" @click="setStatus('approved')">通过</el-button>
      <el-button v-if="article.status==='approved'" type="warning" size="small" @click="setStatus('published')">发布</el-button>
      <el-button v-if="article.status==='published'" size="small" @click="setStatus('draft')">撤回</el-button>
      <el-button size="small" @click="copyText">复制文案</el-button>
      <el-button size="small" @click="exportArticle">导出</el-button>
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
