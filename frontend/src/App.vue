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

const navSections = [
  {
    title: '工作流',
    items: [
      { label: '任务看板', path: '/' },
      { label: '来源管理', path: '/sources' },
      { label: '资源库', path: '/resources' },
      { label: '匹配中心', path: '/matching' },
      { label: '下载队列', path: '/downloads' },
      { label: '文件分析', path: '/analysis' },
      { label: '命名预览', path: '/preview' },
      { label: '自动重命名', path: '/rename' },
      { label: '入库记录', path: '/imports' }
    ]
  },
  {
    title: '系统',
    items: [
      { label: '系统设置', path: '/settings' },
      { label: '安装向导', path: '/setup' },
      { label: '备份恢复', path: '/backup' },
      { label: '系统诊断', path: '/diagnostics' },
      { label: '运行日志', path: '/logs' }
    ]
  }
]
</script>

<template>
  <el-container class="layout">
    <el-aside width="248px" class="sidebar">
      <div class="brand">
        <span class="brand-mark">番</span>
        <div>
          <h1>番剧自动整理管家</h1>
          <p>媒体库整理控制台</p>
        </div>
      </div>
      <el-menu :default-active="activeMenu" router class="nav-menu">
        <template v-for="section in navSections" :key="section.title">
          <li class="nav-section-title">{{ section.title }}</li>
          <el-menu-item v-for="item in section.items" :key="item.path" :index="item.path">
            {{ item.label }}
          </el-menu-item>
        </template>
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
  background: transparent;
}

.sidebar {
  position: sticky;
  top: 0;
  overflow-y: auto;
  height: 100vh;
  border-right: 1px solid rgba(143, 158, 181, 0.22);
  padding: 18px 16px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 8px 0 28px rgba(15, 23, 42, 0.035);
  backdrop-filter: blur(12px);
}

.brand {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
  padding: 8px 8px 16px;
  border-bottom: 1px solid rgba(143, 158, 181, 0.18);
}

.brand-mark {
  display: inline-grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid rgba(64, 158, 255, 0.26);
  border-radius: 10px;
  background: #eef6ff;
  color: #1677d2;
  font-weight: 800;
}

h1 {
  margin: 0;
  color: #0f172a;
  font-size: 17px;
  line-height: 1.3;
}

.brand p {
  margin: 4px 0 0;
  color: #718096;
  font-size: 12px;
  line-height: 1.4;
}

.nav-menu {
  border-right: 0;
  background: transparent;
}

.nav-section-title {
  margin: 14px 8px 6px;
  color: #8a97a9;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  list-style: none;
}

.nav-menu :deep(.el-menu-item) {
  height: 42px;
  margin: 2px 0;
  border-radius: 8px;
  color: #344256;
  font-weight: 600;
}

.nav-menu :deep(.el-menu-item.is-active) {
  background: #eaf4ff;
  color: #1677d2;
}

.nav-menu :deep(.el-menu-item:hover) {
  background: #f3f7fb;
}

.main-content {
  min-width: 0;
  padding: 28px 32px;
}

@media (max-width: 720px) {
  .layout {
    display: block;
  }

  .sidebar {
    position: static;
    width: 100% !important;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid rgba(143, 158, 181, 0.22);
  }

  .nav-menu {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px;
  }

  .nav-section-title {
    grid-column: 1 / -1;
  }

  .nav-menu :deep(.el-menu-item) {
    justify-content: center;
  }

  .main-content {
    padding: 16px;
  }
}
</style>
