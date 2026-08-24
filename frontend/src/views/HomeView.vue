<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, fileUrl } from '../api'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const status = ref('all')
const q = ref('')
const loading = ref(false)

const statusText = { draft: '草稿', approved: '已通过', published: '已发布' }
const statusType = { draft: 'info', approved: 'success', published: 'warning' }

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/articles', {
      params: {
        status: status.value === 'all' ? undefined : status.value,
        q: q.value || undefined,
        page: page.value,
        page_size: 12,
      },
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function cover(item) {
  return item.image_paths && item.image_paths.length ? fileUrl(item.image_paths[0]) : ''
}

async function remove(item) {
  await ElMessageBox.confirm(`确定删除「${item.title}」？`, '删除', { type: 'warning' })
  await api.delete(`/articles/${item.id}`)
  load()
}

const creating = ref(false)

async function createOne() {
  creating.value = true
  try {
    const resp = await api.post('/creation/one-shot')
    ElMessage.success('已生成，请审查')
    router.push(`/articles/${resp.data.id}`)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display:flex;gap:12px;align-items:center;margin-bottom:8px">
      <el-tabs v-model="status" @tab-change="page=1;load()">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="草稿" name="draft" />
        <el-tab-pane label="已通过" name="approved" />
        <el-tab-pane label="已发布" name="published" />
      </el-tabs>
      <div style="flex:1"></div>
      <el-input v-model="q" placeholder="搜索标题" clearable style="width:220px" @keyup.enter="page=1;load()" @clear="load()" />
      <el-button type="primary" @click="page=1;load()">搜索</el-button>
      <el-button type="primary" :loading="creating" @click="createOne">一键创作</el-button>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!items.length" description="还没有内容包，点右上角一键创作" />
      <el-row :gutter="16">
        <el-col v-for="item in items" :key="item.id" :span="6" style="margin-bottom:16px">
          <el-card shadow="hover" :body-style="{ padding: '0px' }">
            <div style="cursor:pointer" @click="router.push(`/articles/${item.id}`)">
              <el-image :src="cover(item)" fit="cover" style="width:100%;height:220px;display:block">
                <template #error><div style="height:220px;background:#eee"></div></template>
              </el-image>
              <div style="padding:12px">
                <div style="font-weight:500;margin-bottom:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.title }}</div>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <el-tag :type="statusType[item.status]" size="small">{{ statusText[item.status] }}</el-tag>
                  <span style="color:#999;font-size:12px">{{ new Date(item.created_at).toLocaleString('zh-CN') }}</span>
                </div>
              </div>
            </div>
            <div style="padding:0 12px 12px;text-align:right">
              <el-button link type="danger" size="small" @click="remove(item)">删除</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-pagination
        v-model:current-page="page"
        :page-size="12"
        :total="total"
        layout="prev, pager, next"
        @current-change="load"
      />
    </div>
  </div>
</template>
