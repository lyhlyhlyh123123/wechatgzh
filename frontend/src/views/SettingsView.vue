<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { api } from '../api'

const PROMPTS = [
  { name: 'creator_system', label: '创意总监提示词' },
  { name: 'question_bank', label: '问题库（100问）' },
]

const promptName = ref('creator_system')
const promptContent = ref('')
const savingPrompt = ref(false)

async function loadPrompt() {
  const { data } = await api.get(`/prompts/${promptName.value}`)
  promptContent.value = data.content
}

async function savePrompt() {
  savingPrompt.value = true
  try {
    await api.put(`/prompts/${promptName.value}`, { content: promptContent.value })
    ElMessage.success('提示词已保存，立即生效')
  } finally {
    savingPrompt.value = false
  }
}

onMounted(loadPrompt)
</script>

<template>
  <el-card header="模型与 Key 请直接编辑运行目录下的 .env 文件（修改后重启生效）；下方提示词保存后立即生效">
    <el-tabs v-model="promptName" @tab-change="loadPrompt">
      <el-tab-pane v-for="p in PROMPTS" :key="p.name" :label="p.label" :name="p.name" />
    </el-tabs>
    <el-input v-model="promptContent" type="textarea" :rows="24" style="margin-top:8px" />
    <el-button type="primary" :loading="savingPrompt" style="margin-top:10px" @click="savePrompt">
      保存提示词
    </el-button>
  </el-card>
</template>
