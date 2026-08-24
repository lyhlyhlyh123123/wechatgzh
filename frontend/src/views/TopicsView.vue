<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const items = ref([])
const driveFilter = ref('')
const dialogVisible = ref(false)
const saving = ref(false)

const DRIVE_TYPES = ['欲望', '比较', '恐惧', '窥私', '站队']
const CATEGORIES = ['情感关系', '婚姻', '女性成长', '成年人的现实', '两性关系', '年龄变化', '人生阶段']

const form = reactive({ id: null, drive_type: '欲望', category: '情感关系', conflict: '' })

async function load() {
  const { data } = await api.get('/topics', {
    params: { drive_type: driveFilter.value || undefined },
  })
  items.value = data.items
}

function openCreate() {
  Object.assign(form, { id: null, drive_type: '欲望', category: '情感关系', conflict: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, row)
  dialogVisible.value = true
}

async function save() {
  if (!form.conflict.trim()) {
    ElMessage.warning('请填写冲突描述')
    return
  }
  saving.value = true
  try {
    if (form.id) {
      await api.patch(`/topics/${form.id}`, form)
    } else {
      await api.post('/topics', form)
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function toggle(row) {
  await api.patch(`/topics/${row.id}`, { enabled: row.enabled })
}

async function remove(row) {
  await ElMessageBox.confirm(`删除该主题？`, '提示', { type: 'warning' })
  await api.delete(`/topics/${row.id}`)
  load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <div style="display:flex;gap:12px;margin-bottom:14px">
      <el-select v-model="driveFilter" placeholder="全部驱动类型" clearable style="width:160px" @change="load">
        <el-option v-for="d in DRIVE_TYPES" :key="d" :label="d" :value="d" />
      </el-select>
      <div style="flex:1"></div>
      <el-button type="primary" @click="openCreate">新增主题</el-button>
    </div>

    <el-table :data="items" border>
      <el-table-column prop="drive_type" label="驱动类型" width="100" />
      <el-table-column prop="category" label="分类" width="130" />
      <el-table-column prop="conflict" label="冲突素材" min-width="300" show-overflow-tooltip />
      <el-table-column prop="use_count" label="使用次数" width="90" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" @change="toggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button link size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑主题' : '新增主题'" width="520px">
      <el-form label-width="90px">
        <el-form-item label="驱动类型">
          <el-select v-model="form.drive_type">
            <el-option v-for="d in DRIVE_TYPES" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="冲突素材">
          <el-input v-model="form.conflict" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
