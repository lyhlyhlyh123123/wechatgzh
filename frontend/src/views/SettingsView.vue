<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const PROMPTS = [
  { name: 'creator_system', label: '创意总监提示词' },
  { name: 'question_bank', label: '问题库（100问）' },
]

const s = reactive({
  deepseek_api_key_masked: '',
  deepseek_model: '',
  volcengine_ark_api_key_masked: '',
  volcengine_ark_image_model: '',
  image_size_default: '',
  presets: [],
  image_count_default: 1,
  image_count_max: 3,
  api_ready: false,
})
const keys = reactive({ deepseek_api_key: '', volcengine_ark_api_key: '' })
const promptName = ref('creator_system')
const promptContent = ref('')
const savingCfg = ref(false)
const savingPrompt = ref(false)

async function load() {
  const { data } = await api.get('/settings')
  Object.assign(s, data)
}

async function loadPrompt() {
  const { data } = await api.get(`/prompts/${promptName.value}`)
  promptContent.value = data.content
}

async function saveConfig() {
  savingCfg.value = true
  try {
    await api.put('/settings', {
      deepseek_api_key: keys.deepseek_api_key || undefined,
      deepseek_model: s.deepseek_model,
      volcengine_ark_api_key: keys.volcengine_ark_api_key || undefined,
      volcengine_ark_image_model: s.volcengine_ark_image_model,
      image_size_default: s.image_size_default,
      image_count_default: s.image_count_default,
    })
    keys.deepseek_api_key = ''
    keys.volcengine_ark_api_key = ''
    await load()
    ElMessage.success('配置已保存并生效')
  } finally {
    savingCfg.value = false
  }
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

onMounted(() => {
  load()
  loadPrompt()
})
</script>

<template>
  <el-row :gutter="16">
    <el-col :span="10">
      <el-card header="API 与默认配置">
        <el-alert
          v-if="!s.api_ready"
          title="尚未配置完整的 API Key，生成功能不可用"
          type="warning"
          :closable="false"
          style="margin-bottom:14px"
        />
        <el-form label-width="150px">
          <el-form-item label="DeepSeek Key">
            <el-input v-model="keys.deepseek_api_key" type="password" :placeholder="s.deepseek_api_key_masked || '未配置'" show-password />
          </el-form-item>
          <el-form-item label="DeepSeek 模型">
            <el-input v-model="s.deepseek_model" />
          </el-form-item>
          <el-form-item label="ARK Key">
            <el-input v-model="keys.volcengine_ark_api_key" type="password" :placeholder="s.volcengine_ark_api_key_masked || '未配置'" show-password />
          </el-form-item>
          <el-form-item label="ARK 图片模型">
            <el-input v-model="s.volcengine_ark_image_model" />
          </el-form-item>
          <el-form-item label="默认图片尺寸">
            <el-select v-model="s.image_size_default" style="width:100%">
              <el-option v-for="p in s.presets" :key="p.size" :label="`${p.label}（${p.size}）`" :value="p.size" />
            </el-select>
          </el-form-item>
          <el-form-item label="默认图片数量">
            <el-input-number v-model="s.image_count_default" :min="1" :max="s.image_count_max" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingCfg" @click="saveConfig">保存配置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-col>

    <el-col :span="14">
      <el-card header="提示词模板（修改立即生效）">
        <el-tabs v-model="promptName" @tab-change="loadPrompt">
          <el-tab-pane v-for="p in PROMPTS" :key="p.name" :label="p.label" :name="p.name" />
        </el-tabs>
        <el-input v-model="promptContent" type="textarea" :rows="20" style="margin-top:8px" />
        <el-button type="primary" :loading="savingPrompt" style="margin-top:10px" @click="savePrompt">
          保存提示词
        </el-button>
      </el-card>
    </el-col>
  </el-row>
</template>
