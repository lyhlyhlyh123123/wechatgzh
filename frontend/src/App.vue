<script setup>
import { ref } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import HomeView from './views/HomeView.vue'
import SettingsView from './views/SettingsView.vue'

const activeMenu = ref('home')
</script>

<template>
  <el-container style="height:100vh">
    <el-aside width="200px" style="border-right:1px solid #e4e7ed;display:flex;flex-direction:column">
      <div style="padding:18px 16px;font-weight:600;font-size:15px;border-bottom:1px solid #e4e7ed">情感内容工作台</div>
      <el-menu :default-active="activeMenu" @select="activeMenu=$event" style="flex:1;border-right:none">
        <el-menu-item index="home">
          <span>创造中心</span>
        </el-menu-item>
        <el-menu-item index="settings">
          <el-icon><Setting /></el-icon>
          <span>提示词</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main style="padding:0;overflow:hidden;background:#fafafa">
      <HomeView v-if="activeMenu==='home'" />
      <SettingsView v-else-if="activeMenu==='settings'" />
    </el-main>
  </el-container>
</template>
