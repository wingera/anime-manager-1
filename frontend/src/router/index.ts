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
      path: '/sources',
      name: 'sources',
      component: () => import('../pages/SourceManagement.vue')
    },
    {
      path: '/resources',
      name: 'resources',
      component: () => import('../pages/ResourceLibrary.vue')
    }
  ]
})

export default router
