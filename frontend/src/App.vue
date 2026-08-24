<script setup>
import { FolderOpened, Menu, Setting } from '@element-plus/icons-vue'
</script>

<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="border-right: 1px solid #eee">
      <div style="padding: 18px 16px; font-weight: 600">情感内容工作台</div>
      <el-menu router :default-active="$route.path">
        <el-menu-item index="/"><el-icon><Menu /></el-icon>内容包</el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon>提示词</el-menu-item>
      </el-menu>
      <div style="position:absolute;bottom:16px;left:16px;color:#999;font-size:12px">
        <el-icon><FolderOpened /></el-icon> 本地工作台 v0.1
      </div>
    </el-aside>
    <el-main style="background:#f7f8fa;padding:0;overflow:hidden">
      <router-view />
    </el-main>
  </el-container>
</template>
