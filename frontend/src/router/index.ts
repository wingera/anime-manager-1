import { createRouter, createWebHistory } from 'vue-router'
import DashboardHome from '../pages/DashboardHome.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardHome
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../pages/SettingsCenter.vue')
    },
    {
      path: '/setup',
      name: 'setup',
      component: () => import('../pages/SetupWizard.vue')
    },
    {
      path: '/backup',
      name: 'backup',
      component: () => import('../pages/BackupRestore.vue')
    },
    {
      path: '/diagnostics',
      name: 'diagnostics',
      component: () => import('../pages/SystemDiagnostics.vue')
    },
    {
      path: '/sources',
      name: 'sources',
      component: () => import('../pages/SourceManagement.vue')
    },
    {
      path: '/resources',
      name: 'resources',
      component: () => import('../pages/ResourceLibrary.vue')
    },
    {
      path: '/downloads',
      name: 'downloads',
      component: () => import('../pages/DownloadQueue.vue')
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('../pages/FileAnalysis.vue')
    },
    {
      path: '/preview',
      name: 'preview',
      component: () => import('../pages/RenamePreview.vue')
    },
    {
      path: '/rename',
      name: 'rename',
      component: () => import('../pages/AutoRename.vue')
    },
    {
      path: '/imports',
      name: 'imports',
      component: () => import('../pages/ImportRecords.vue')
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('../pages/OperationLogs.vue')
    }
  ]
})

export default router
