<script setup>
import { Document, FolderOpened, Menu, Setting, Star } from '@element-plus/icons-vue'
</script>

<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="border-right: 1px solid #eee">
      <div style="padding: 18px 16px; font-weight: 600">情感内容工作台</div>
      <el-menu router :default-active="$route.path">
        <el-menu-item index="/"><el-icon><Menu /></el-icon>内容包</el-menu-item>
        <el-menu-item index="/wizard"><el-icon><Document /></el-icon>新建内容</el-menu-item>
        <el-menu-item index="/topics"><el-icon><Star /></el-icon>主题库</el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon>设置</el-menu-item>
      </el-menu>
      <div style="position:absolute;bottom:16px;left:16px;color:#999;font-size:12px">
        <el-icon><FolderOpened /></el-icon> 本地工作台 v0.1
      </div>
    </el-aside>
    <el-main style="background:#f7f8fa">
      <router-view />
    </el-main>
  </el-container>
</template>
