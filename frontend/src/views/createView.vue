<script setup>
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { api } from '../api'

const emit = defineEmits(['created'])
const creating = ref(false)

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

function applyPreset(p) { Object.assign(prefs.value, p.values) }

async function doCreate() {
  creating.value = true
  try {
    const resp = await api.post('/creation/one-shot', { image_preferences: { ...prefs.value } })
    ElMessage.success('已生成')
    emit('created', resp.data.id)
  } finally { creating.value = false }
}
</script>

<template>
  <div style="padding:24px;max-width:560px;margin:0 auto">
    <h2 style="font-size:18px;margin:0 0 16px">创造中心</h2>

    <div style="background:#fff;border-radius:8px;padding:16px;border:1px solid #ebeef5;margin-bottom:16px">
      <div style="font-size:13px;color:#909399;margin-bottom:8px">快速预设</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <el-button v-for="p in presets" :key="p.label" size="small" @click="applyPreset(p)">{{ p.label }}</el-button>
      </div>
    </div>

    <div style="background:#fff;border-radius:8px;padding:16px;border:1px solid #ebeef5;margin-bottom:16px">
      <div style="font-size:13px;color:#909399;margin-bottom:10px">人物设定</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div v-for="(options, key) in opts" :key="key">
          <div style="font-size:13px;color:#606266;margin-bottom:4px">{{ key }}</div>
          <el-select v-model="prefs[key]" style="width:100%">
            <el-option v-for="o in options" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
      </div>
    </div>

    <el-button type="primary" :loading="creating" @click="doCreate" style="width:100%;height:44px;font-size:15px">一键创作</el-button>
  </div>
</template>
