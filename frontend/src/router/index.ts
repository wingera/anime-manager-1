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
    }
  ]
})

export default router
