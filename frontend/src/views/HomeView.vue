<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api, fileUrl } from '../api'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const status = ref('all')
const q = ref('')
const loading = ref(false)
const activeId = ref(null)

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
        page_size: 50,
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
  if (activeId.value === item.id) activeId.value = null
  load()
}

const creating = ref(false)
const showPrefs = ref(false)

const prefs = ref({
  发型: '长发自然散落',
  脸型: '鹅蛋脸',
  年龄: '25~35岁',
  身材: '微胖有肉感',
  穿搭: '紧身吊带',
  场景: '奶茶店',
  看哪里: '直视镜头',
})

const opts = {
  发型: ['长发自然散落', '短发干练', '卷发慵懒', '马尾', '披肩发', '盘发'],
  脸型: ['鹅蛋脸', '瓜子脸', '圆脸', '方脸'],
  年龄: ['20~25岁', '25~30岁', '30~35岁', '35~40岁'],
  身材: ['微胖有肉感', '苗条纤细', '丰满圆润', '匀称健康'],
  穿搭: ['紧身吊带', '低胸T恤', '修身连衣裙', '包臀裙', '紧身牛仔裤', '旗袍', '露肩上衣', '衬衫'],
  场景: ['奶茶店', '咖啡厅', '商场', '家里沙发', '卧室床上', '阳台', '地下车库', '街边', '车内', '办公室', '健身房', '超市'],
  看哪里: ['直视镜头', '侧脸', '低头', '背影', '看窗外'],
}

const presets = [
  { label: '居家慵懒', values: { 发型:'长发自然散落', 脸型:'鹅蛋脸', 年龄:'25~30岁', 身材:'微胖有肉感', 穿搭:'紧身吊带', 场景:'卧室床上', 看哪里:'直视镜头' }},
  { label: '逛街随拍', values: { 发型:'披肩发', 脸型:'瓜子脸', 年龄:'25~35岁', 身材:'匀称健康', 穿搭:'紧身牛仔裤', 场景:'街边', 看哪里:'直视镜头' }},
  { label: '办公室', values: { 发型:'马尾', 脸型:'鹅蛋脸', 年龄:'30~35岁', 身材:'丰满圆润', 穿搭:'衬衫', 场景:'办公室', 看哪里:'直视镜头' }},
  { label: '咖啡时光', values: { 发型:'卷发慵懒', 脸型:'瓜子脸', 年龄:'25~30岁', 身材:'苗条纤细', 穿搭:'修身连衣裙', 场景:'咖啡厅', 看哪里:'看窗外' }},
  { label: '旗袍韵味', values: { 发型:'盘发', 脸型:'鹅蛋脸', 年龄:'30~35岁', 身材:'丰满圆润', 穿搭:'旗袍', 场景:'咖啡厅', 看哪里:'直视镜头' }},
]

function applyPreset(p) {
  Object.assign(prefs.value, p.values)
}

const activeArticle = ref(null)

async function selectItem(item) {
  activeId.value = item.id
  try {
    const { data } = await api.get(`/articles/${item.id}`)
    activeArticle.value = data
  } catch {
    activeArticle.value = item
  }
}

async function createOne() {
  showPrefs.value = true
}

async function doCreate() {
  showPrefs.value = false
  creating.value = true
  try {
    const resp = await api.post('/creation/one-shot', {
      image_preferences: { ...prefs.value },
    })
    ElMessage.success('已生成')
    await load()
    selectItem(resp.data)
  } finally {
    creating.value = false
  }
}

async function changeStatus(item, newStatus) {
  await api.patch(`/articles/${item.id}`, { status: newStatus })
  ElMessage.success('已更新')
  load()
  if (activeArticle.value?.id === item.id) {
    activeArticle.value.status = newStatus
  }
}

async function exportArticle(item) {
  try {
    const resp = await api.get(`/articles/${item.id}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${item.title || 'article'}.html`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('导出失败')
  }
}

onMounted(load)
</script>

<template>
  <div style="display:flex;height:calc(100vh - 60px);gap:0">
    <!-- 左侧：历史记录 -->
    <div style="width:320px;border-right:1px solid #e4e7ed;display:flex;flex-direction:column;flex-shrink:0">
      <div style="padding:12px;border-bottom:1px solid #e4e7ed">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
          <el-button type="primary" :loading="creating" @click="createOne" style="flex:1">一键创作</el-button>
        </div>
        <el-tabs v-model="status" @tab-change="page=1;load()" style="margin-bottom:0">
          <el-tab-pane label="全部" name="all" />
          <el-tab-pane label="草稿" name="draft" />
          <el-tab-pane label="已通过" name="approved" />
          <el-tab-pane label="已发布" name="published" />
        </el-tabs>
        <el-input v-model="q" placeholder="搜索" clearable size="small" @keyup.enter="page=1;load()" @clear="load()" style="margin-top:8px" />
      </div>
      <div style="flex:1;overflow-y:auto;padding:8px" v-loading="loading">
        <div v-if="!items.length" style="text-align:center;color:#999;padding:40px 0">还没有内容，点上方一键创作</div>
        <div v-for="item in items" :key="item.id"
          :style="{padding:'10px 12px',border:'1px solid '+(activeId===item.id?'#409eff':'#e4e7ed'),borderRadius:'8px',marginBottom:'6px',cursor:'pointer',background:activeId===item.id?'#ecf5ff':'#fff'}"
          @click="selectItem(item)">
          <div style="display:flex;gap:8px;align-items:center">
            <el-image :src="cover(item)" fit="cover" style="width:40px;height:40px;border-radius:4px;flex-shrink:0">
              <template #error><div style="width:40px;height:40px;background:#f0f0f0;border-radius:4px"></div></template>
            </el-image>
            <div style="flex:1;min-width:0">
              <div style="font-size:13px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.title }}</div>
              <div style="display:flex;gap:6px;align-items:center;margin-top:2px">
                <el-tag :type="statusType[item.status]" size="small" style="font-size:11px">{{ statusText[item.status] }}</el-tag>
                <span style="color:#999;font-size:11px">{{ new Date(item.created_at).toLocaleDateString('zh-CN') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：文案详情 -->
    <div style="flex:1;overflow-y:auto;padding:24px;background:#fafafa">
      <div v-if="!activeArticle" style="text-align:center;color:#999;padding-top:120px">
        <div style="font-size:48px;margin-bottom:16px">📝</div>
        <div>选择左侧历史记录查看详情</div>
      </div>
      <div v-else style="max-width:680px;margin:0 auto">
        <!-- 标题 -->
        <div style="margin-bottom:16px">
          <h2 style="font-size:20px;margin:0 0 8px">{{ activeArticle.title }}</h2>
          <div style="display:flex;gap:8px;align-items:center">
            <el-tag :type="statusType[activeArticle.status]" size="small">{{ statusText[activeArticle.status] }}</el-tag>
            <span style="color:#999;font-size:12px">{{ new Date(activeArticle.created_at).toLocaleString('zh-CN') }}</span>
          </div>
        </div>

        <!-- 标题候选 -->
        <div v-if="activeArticle.title_candidates" style="background:#fff;border-radius:8px;padding:16px;margin-bottom:12px;border:1px solid #e4e7ed">
          <div style="font-size:13px;color:#909399;margin-bottom:8px">标题候选</div>
          <div v-for="(t,i) in (Array.isArray(activeArticle.title_candidates) ? activeArticle.title_candidates : [])" :key="i" style="padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:14px">
            <template v-if="typeof t === 'string'">{{ i+1 }}. {{ t }}</template>
            <template v-else-if="t.titles">
              <div v-for="(tt,j) in t.titles" :key="j" style="padding:2px 0">{{ i+1 }}{{ j>0?'.'+(j+1):'' }}. {{ tt }}</div>
            </template>
          </div>
        </div>

        <!-- 正文 -->
        <div style="background:#fff;border-radius:8px;padding:16px;margin-bottom:12px;border:1px solid #e4e7ed">
          <div style="font-size:13px;color:#909399;margin-bottom:8px">正文</div>
          <div style="font-size:15px;line-height:1.8;white-space:pre-wrap">{{ activeArticle.body }}</div>
        </div>

        <!-- 情绪标签 -->
        <div v-if="activeArticle.mood" style="background:#fff;border-radius:8px;padding:12px 16px;margin-bottom:12px;border:1px solid #e4e7ed">
          <span style="font-size:13px;color:#909399">情绪标签：</span>
          <el-tag size="small">{{ activeArticle.mood }}</el-tag>
        </div>

        <!-- 图片提示词 -->
        <div style="background:#fff;border-radius:8px;padding:16px;margin-bottom:12px;border:1px solid #e4e7ed">
          <div style="font-size:13px;color:#909399;margin-bottom:8px">图片提示词</div>
          <div style="font-size:13px;color:#606266;line-height:1.6;word-break:break-all">{{ activeArticle.image_prompt }}</div>
        </div>

        <!-- 图片 -->
        <div v-if="activeArticle.image_paths && activeArticle.image_paths.length" style="margin-bottom:12px">
          <div style="font-size:13px;color:#909399;margin-bottom:8px">生成图片</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <el-image v-for="(p,i) in activeArticle.image_paths" :key="i" :src="fileUrl(p)" fit="cover" style="width:200px;height:260px;border-radius:8px">
              <template #error><div style="width:200px;height:260px;background:#f0f0f0;border-radius:8px"></div></template>
            </el-image>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div style="display:flex;gap:8px;margin-top:16px">
          <el-button v-if="activeArticle.status==='draft'" type="success" @click="changeStatus(activeArticle,'approved')">通过</el-button>
          <el-button v-if="activeArticle.status==='approved'" type="warning" @click="changeStatus(activeArticle,'published')">发布</el-button>
          <el-button v-if="activeArticle.status==='published'" @click="changeStatus(activeArticle,'draft')">撤回</el-button>
          <el-button @click="exportArticle(activeArticle)">导出</el-button>
          <div style="flex:1"></div>
          <el-button type="danger" @click="remove(activeArticle)">删除</el-button>
        </div>
      </div>
    </div>

    <!-- 人物设定弹窗 -->
    <el-dialog v-model="showPrefs" title="人物设定" width="560px">
      <div style="margin-bottom:12px">
        <div style="font-size:13px;color:#909399;margin-bottom:8px">快速预设</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <el-button v-for="p in presets" :key="p.label" size="small" @click="applyPreset(p)">{{ p.label }}</el-button>
        </div>
      </div>
      <el-divider style="margin:12px 0" />
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div v-for="(options, key) in opts" :key="key">
          <div style="font-size:13px;color:#606266;margin-bottom:4px">{{ key }}</div>
          <el-select v-model="prefs[key]" style="width:100%" size="default">
            <el-option v-for="o in options" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="showPrefs=false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="doCreate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>
