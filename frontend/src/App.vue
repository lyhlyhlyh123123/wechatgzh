<script setup>
import { ref } from 'vue'

import CreateView from './views/createView.vue'
import HistoryView from './views/HistoryView.vue'
import DetailView from './views/DetailView.vue'
import SettingsView from './views/SettingsView.vue'

const activeMenu = ref('create')
const selectedArticleId = ref(null)

function openDetail(id) {
  selectedArticleId.value = id
  activeMenu.value = 'detail'
}
</script>

<template>
  <el-container style="height:100vh">
    <el-aside width="180px" style="border-right:1px solid #e4e7ed;display:flex;flex-direction:column">
      <div style="padding:16px;font-weight:600;font-size:14px;border-bottom:1px solid #e4e7ed">情感内容工作台</div>
      <el-menu :default-active="activeMenu" @select="activeMenu=$event" style="flex:1;border-right:none">
        <el-menu-item index="create"><span>创造中心</span></el-menu-item>
        <el-menu-item index="detail"><span>查看详情</span></el-menu-item>
        <el-menu-item index="history"><span>历史记录</span></el-menu-item>
        <el-menu-item index="settings"><span>提示词</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-main style="padding:0;overflow:hidden;background:#fafafa">
      <CreateView v-show="activeMenu==='create'" @created="openDetail" />
      <HistoryView v-show="activeMenu==='history'" @select="openDetail" />
      <DetailView v-show="activeMenu==='detail'" :article-id="selectedArticleId" />
      <SettingsView v-show="activeMenu==='settings'" />
    </el-main>
  </el-container>
</template>
