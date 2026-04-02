import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘', icon: 'Odometer' }
  },
  {
    path: '/processes',
    name: 'Processes',
    component: () => import('@/views/Processes.vue'),
    meta: { title: '进程管理', icon: 'Monitor' }
  },
  {
    path: '/scripts',
    name: 'Scripts',
    component: () => import('@/views/Scripts.vue'),
    meta: { title: '脚本配置', icon: 'Document' }
  },
  {
    path: '/scripts/:name',
    name: 'ScriptDetail',
    component: () => import('@/views/ScriptDetail.vue'),
    meta: { title: '脚本详情', icon: 'Document', hidden: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History.vue'),
    meta: { title: '运行历史', icon: 'Clock' }
  },
  {
    path: '/logs',
    name: 'LogManagement',
    component: () => import('@/views/LogManagement.vue'),
    meta: { title: '日志管理', icon: 'Delete' }
  },
  {
    path: '/system-logs',
    name: 'SystemLogs',
    component: () => import('@/views/SystemLogs.vue'),
    meta: { title: '操作日志', icon: 'Tickets' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - Python 脚本管理器`
  next()
})

export default router
