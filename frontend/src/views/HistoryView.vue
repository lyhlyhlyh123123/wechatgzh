<script setup>
import { ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { api, fileUrl } from '../api'

const emit = defineEmits(['select'])
const items = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/articles', { params: { page_size: 100 } })
    items.value = data.items
  } finally { loading.value = false }
}

function cover(item) { return item.image_paths?.length ? fileUrl(item.image_paths[0]) : '' }

async function remove(item, e) {
  e.stopPropagation()
  await ElMessageBox.confirm(`确定删除「${item.title}」？`, '删除', { type: 'warning' })
  await api.delete(`/articles/${item.id}`)
  load()
}

onMounted(load)
</script>

<template>
  <div style="padding:24px;max-width:720px;margin:0 auto">
    <h2 style="font-size:18px;margin:0 0 16px">历史记录</h2>
    <div v-loading="loading">
      <div v-if="!items.length" style="text-align:center;color:#c0c4cc;padding:40px 0">还没有内容</div>
      <div v-for="item in items" :key="item.id"
        style="display:flex;gap:12px;padding:12px;background:#fff;border-radius:8px;border:1px solid #ebeef5;margin-bottom:8px;cursor:pointer"
        @click="emit('select', item.id)">
        <el-image :src="cover(item)" fit="cover" style="width:64px;height:64px;border-radius:6px;flex-shrink:0">
          <template #error><div style="width:64px;height:64px;background:#f5f5f5;border-radius:6px"></div></template>
        </el-image>
        <div style="flex:1;min-width:0">
          <div style="font-weight:500;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.title }}</div>
          <div style="display:flex;gap:6px;align-items:center;margin-top:4px">
            <el-tag :type="{draft:'info',approved:'success',published:'warning'}[item.status]" size="small">{{ {draft:'草稿',approved:'已通过',published:'已发布'}[item.status] }}</el-tag>
            <span style="color:#999;font-size:12px">{{ new Date(item.created_at).toLocaleString('zh-CN') }}</span>
          </div>
        </div>
        <el-button link type="danger" size="small" @click="remove(item, $event)">删除</el-button>
      </div>
    </div>
  </div>
</template>
