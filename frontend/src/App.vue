<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => {
  if (route.path.startsWith('/downloads')) return '/downloads'
  if (route.path.startsWith('/analysis')) return '/analysis'
  if (route.path.startsWith('/preview')) return '/preview'
  if (route.path.startsWith('/rename')) return '/rename'
  if (route.path.startsWith('/imports')) return '/imports'
  if (route.path.startsWith('/logs')) return '/logs'
  if (route.path.startsWith('/resources')) return '/resources'
  if (route.path.startsWith('/sources')) return '/sources'
  if (route.path.startsWith('/settings')) return '/settings'
  if (route.path.startsWith('/setup')) return '/setup'
  if (route.path.startsWith('/backup')) return '/backup'
  if (route.path.startsWith('/diagnostics')) return '/diagnostics'
  return '/'
})
</script>

<template>
  <el-container class="layout">
    <el-aside width="240px" class="sidebar">
      <h1>番剧自动整理管家</h1>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/">任务看板</el-menu-item>
        <el-menu-item index="/sources">来源管理</el-menu-item>
        <el-menu-item index="/resources">资源库</el-menu-item>
        <el-menu-item index="/matching">匹配中心</el-menu-item>
        <el-menu-item index="/downloads">下载队列</el-menu-item>
        <el-menu-item index="/analysis">文件分析</el-menu-item>
        <el-menu-item index="/preview">命名预览</el-menu-item>
        <el-menu-item index="/rename">自动重命名</el-menu-item>
        <el-menu-item index="/imports">入库记录</el-menu-item>
        <el-menu-item index="/settings">系统设置</el-menu-item>
        <el-menu-item index="/setup">安装向导</el-menu-item>
        <el-menu-item index="/backup">备份恢复</el-menu-item>
        <el-menu-item index="/diagnostics">系统诊断</el-menu-item>
        <el-menu-item index="/logs">运行日志</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="main-content">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  background: #f8fafc;
}

.sidebar {
  border-right: 1px solid #e5e7eb;
  padding: 16px;
  background: #ffffff;
}

h1 {
  margin: 0 0 16px;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
}

.main-content {
  min-width: 0;
  padding: 24px;
}

@media (max-width: 720px) {
  .layout {
    display: block;
  }

  .sidebar {
    width: 100% !important;
    border-right: 0;
    border-bottom: 1px solid #e5e7eb;
  }

  .main-content {
    padding: 16px;
  }
}
</style>
