<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="app-aside">
      <!-- Logo -->
      <div class="logo" @click="$router.push('/')">
        <el-icon :size="28" color="#409eff"><Promotion /></el-icon>
        <span v-show="!isCollapse" class="logo-text">脚本管理器</span>
      </div>
      
      <!-- 快捷操作按钮 -->
      <div class="quick-actions-top" :class="{ 'is-collapse': isCollapse }">
        <el-tooltip content="刷新数据" placement="right" :disabled="!isCollapse">
          <el-button type="primary" @click="refreshAll" class="action-btn">
            <el-icon><Refresh /></el-icon>
            <span class="btn-text">刷新数据</span>
          </el-button>
        </el-tooltip>
        <el-tooltip content="重载配置" placement="right" :disabled="!isCollapse">
          <el-button type="success" @click="reloadConfig" class="action-btn">
            <el-icon><Upload /></el-icon>
            <span class="btn-text">重载配置</span>
          </el-button>
        </el-tooltip>
      </div>
      
      <!-- 系统状态 -->
      <div v-show="!isCollapse" class="system-status">
        <div class="status-item">
          <el-icon class="status-icon running"><Loading /></el-icon>
          <span class="status-text">运行中: {{ stats.running_scripts }}</span>
        </div>
        <div class="status-item">
          <el-icon class="status-icon scheduled"><Clock /></el-icon>
          <span class="status-text">定时任务: {{ stats.scheduled_active }}/{{ stats.scheduled_total }}</span>
        </div>
        <div class="status-item">
          <el-icon class="status-icon process"><Cpu /></el-icon>
          <span class="status-text">进程: {{ stats.python_processes }}</span>
        </div>
      </div>
      
      <!-- 菜单 -->
      <el-scrollbar class="menu-scrollbar">
        <el-menu
          :default-active="currentRoute"
          :collapse="isCollapse"
          :collapse-transition="false"
          :unique-opened="false"
          router
          class="app-menu"
        >
          <!-- 监控中心 -->
          <el-sub-menu index="monitor">
            <template #title>
              <el-icon><Monitor /></el-icon>
              <span>监控中心</span>
            </template>
            <el-menu-item index="/">
              <el-icon><Odometer /></el-icon>
              <span>仪表盘</span>
            </el-menu-item>
            <el-menu-item index="/processes">
              <el-icon><Cpu /></el-icon>
              <span>进程管理</span>
              <el-badge v-if="processCount > 0" :value="processCount" :max="99" class="item-badge" />
            </el-menu-item>
          </el-sub-menu>
          
          <!-- 脚本管理 -->
          <el-sub-menu index="scripts-menu">
            <template #title>
              <el-icon><Document /></el-icon>
              <span>脚本管理</span>
            </template>
            <el-menu-item index="/scripts">
              <el-icon><Files /></el-icon>
              <span>脚本列表</span>
              <el-badge v-if="runningScripts > 0" :value="runningScripts" :max="99" class="item-badge success" />
            </el-menu-item>
            <el-menu-item index="/history">
              <el-icon><Clock /></el-icon>
              <span>运行历史</span>
            </el-menu-item>
          </el-sub-menu>
          
          <!-- 系统管理 -->
          <el-sub-menu index="system">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/logs">
              <el-icon><Delete /></el-icon>
              <span>日志管理</span>
            </el-menu-item>
            <el-menu-item index="/system-logs">
              <el-icon><Tickets /></el-icon>
              <span>操作日志</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
      
      <!-- 底部操作区 -->
      <div class="aside-footer">
        <!-- 折叠按钮 -->
        <div class="collapse-btn" @click="toggleCollapse">
          <el-icon>
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
          <span v-show="!isCollapse" class="collapse-text">收起菜单</span>
        </div>
      </div>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航 -->
      <el-header class="app-header" height="50px">
        <div class="header-left">
          <!-- 面包屑 -->
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 搜索 -->
          <el-input
            v-model="searchKeyword"
            placeholder="搜索脚本..."
            prefix-icon="Search"
            clearable
            class="search-input"
            @keyup.enter="handleSearch"
          />
          
          <!-- 时间 -->
          <div class="current-time">
            <el-icon><Clock /></el-icon>
            <span>{{ currentTime }}</span>
          </div>
          
          <!-- 服务状态 -->
          <el-tooltip content="服务运行正常" placement="bottom">
            <el-tag type="success" effect="light" class="status-tag">
              <el-icon class="pulse"><CircleCheck /></el-icon>
              在线
            </el-tag>
          </el-tooltip>
          
          <!-- 更多操作 -->
          <el-dropdown trigger="click" @command="handleCommand">
            <el-button circle>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="api-docs">
                  <el-icon><Document /></el-icon>API 文档
                </el-dropdown-item>
                <el-dropdown-item command="github">
                  <el-icon><Link /></el-icon>GitHub
                </el-dropdown-item>
                <el-dropdown-item divided command="about">
                  <el-icon><InfoFilled /></el-icon>关于
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 标签页导航 -->
      <div class="tabs-nav" v-if="visitedViews.length > 0">
        <el-tabs v-model="activeTab" type="card" closable @tab-remove="removeTab" @tab-click="clickTab">
          <el-tab-pane
            v-for="view in visitedViews"
            :key="view.path"
            :label="view.title"
            :name="view.path"
          />
        </el-tabs>
      </div>
      
      <!-- 内容区域 -->
      <el-main class="app-main">
        <router-view v-slot="{ Component, route }">
          <transition name="fade-slide" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="route.path" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
      
      <!-- 底部 -->
      <el-footer height="30px" class="app-footer">
        <span>Python 脚本管理器 v1.0.0</span>
        <span class="divider">|</span>
        <span>Powered by FastAPI + Vue3</span>
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { statsApi, scriptApi } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()

// 状态
const isCollapse = ref(false)
const currentTime = ref('')
const searchKeyword = ref('')
const stats = ref({
  total_scripts: 0,
  running_scripts: 0,
  python_processes: 0,
  scheduled_total: 0,
  scheduled_active: 0
})

// 标签页导航
const visitedViews = ref([
  { path: '/', title: '仪表盘', closable: false }
])
const cachedViews = ref(['Dashboard'])
const activeTab = ref('/')

// 计算属性
const currentRoute = computed(() => route.path)
const processCount = computed(() => stats.value.python_processes)
const runningScripts = computed(() => stats.value.running_scripts)

// 面包屑
const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title
  }))
})

// 菜单定义
const menuItems = [
  { path: '/', title: '仪表盘', icon: 'Odometer' },
  { path: '/processes', title: '进程管理', icon: 'Monitor' },
  { path: '/scripts', title: '脚本配置', icon: 'Document' },
  { path: '/history', title: '运行历史', icon: 'Clock' },
  { path: '/logs', title: '系统日志', icon: 'Tickets' }
]

// 更新时间
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 加载统计数据
const loadStats = async () => {
  try {
    const res = await statsApi.get()
    if (res.success) {
      stats.value = res.data
    }
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

// 刷新所有数据
const refreshAll = () => {
  loadStats()
  ElMessage.success('数据已刷新')
}

// 重载配置
const reloadConfig = async () => {
  try {
    const res = await scriptApi.reload()
    ElMessage.success(res.message)
    loadStats()
  } catch (e) {
    console.error('重载失败:', e)
  }
}

// 切换折叠
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 搜索
const handleSearch = () => {
  if (searchKeyword.value.trim()) {
    router.push({ path: '/scripts', query: { search: searchKeyword.value } })
  }
}

// 下拉菜单命令
const handleCommand = (command) => {
  switch (command) {
    case 'api-docs':
      window.open('/docs', '_blank')
      break
    case 'github':
      window.open('https://github.com', '_blank')
      break
    case 'about':
      ElMessageBox.alert(
        'Python 脚本管理器 v1.0.0\n\n一个基于 FastAPI + Vue3 的脚本后台管理系统',
        '关于',
        { confirmButtonText: '确定' }
      )
      break
  }
}

// 标签页操作
const addVisitedView = (view) => {
  if (view.path === '/') return
  
  const exists = visitedViews.value.find(v => v.path === view.path)
  if (!exists) {
    visitedViews.value.push({
      path: view.path,
      title: view.meta?.title || '未知页面',
      closable: true
    })
  }
  activeTab.value = view.path
}

const removeTab = (path) => {
  const index = visitedViews.value.findIndex(v => v.path === path)
  if (index > -1) {
    visitedViews.value.splice(index, 1)
    if (activeTab.value === path) {
      const next = visitedViews.value[index] || visitedViews.value[index - 1]
      router.push(next.path)
    }
  }
}

const clickTab = (tab) => {
  router.push(tab.paneName)
}

// 监听路由变化
watch(
  () => route.path,
  (path) => {
    addVisitedView(route)
  },
  { immediate: true }
)

// 定时器
let timer = null
let statsTimer = null

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  
  loadStats()
  statsTimer = setInterval(loadStats, 70000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (statsTimer) clearInterval(statsTimer)
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏样式 */
.app-aside {
  background: linear-gradient(180deg, #1e3a5f 0%, #0d2137 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  padding-left: 18px;
  gap: 30px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  transition: background-color 0.3s;
}

.logo:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
}

/* 系统状态 */
.system-status {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  white-space: nowrap;
}

.status-icon {
  font-size: 18px;
}

.status-icon.running {
  color: #67c23a;
  animation: pulse 2s infinite;
}

.status-icon.process {
  color: #409eff;
}

.status-text {
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
}

/* 菜单样式 */
.menu-scrollbar {
  flex: 1;
  overflow: hidden;
}

.app-menu {
  border-right: none;
  background-color: transparent !important;
}

/* 子菜单标题 */
.app-menu :deep(.el-sub-menu__title) {
  color: rgba(255, 255, 255, 0.7) !important;
  height: 48px;
  line-height: 48px;
  background-color: transparent !important;
}

.app-menu :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: #fff !important;
}

/* 菜单项 */
.app-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.7) !important;
  height: 48px;
  line-height: 48px;
  background-color: transparent !important;
}

.app-menu :deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: #fff !important;
}

.app-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #409eff 0%, rgba(64, 158, 255, 0.5) 100%) !important;
  color: #fff !important;
}

/* 子菜单内部 - 嵌套菜单 */
.app-menu :deep(.el-sub-menu .el-menu),
.app-menu :deep(.el-sub-menu .el-menu.el-menu--inline),
.app-menu :deep(.el-sub-menu .el-menu.el-menu--popup) {
  background-color: transparent !important;
}

.app-menu :deep(.el-sub-menu .el-menu .el-menu-item) {
  padding-left: 50px !important;
  background-color: transparent !important;
  min-width: auto !important;
}

/* 内联子菜单项 */
.app-menu :deep(.el-menu--inline .el-menu-item) {
  background-color: transparent !important;
}

/* 弹出子菜单项 */
.app-menu :deep(.el-menu--popup .el-menu-item) {
  background-color: transparent !important;
}

/* 子菜单弹出层 - 折叠状态或溢出时 */
.app-menu :deep(.el-menu--popup) {
  background: linear-gradient(180deg, #1e3a5f 0%, #0d2137 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  min-width: 180px !important;
}

.app-menu :deep(.el-menu--popup .el-menu-item) {
  color: rgba(255, 255, 255, 0.7) !important;
  background-color: transparent !important;
}

.app-menu :deep(.el-menu--popup .el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: #fff !important;
}

.app-menu :deep(.el-menu--popup .el-menu-item.is-active) {
  background: rgba(64, 158, 255, 0.3) !important;
  color: #fff !important;
}

/* 激活状态的子菜单标题 */
.app-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #409eff !important;
}

/* 子菜单箭头颜色 */
.app-menu :deep(.el-sub-menu__icon-arrow) {
  color: rgba(255, 255, 255, 0.5) !important;
}

/* 子菜单标题内的图标 */
.app-menu :deep(.el-sub-menu__title .el-icon) {
  color: rgba(255, 255, 255, 0.7) !important;
}

.app-menu :deep(.el-sub-menu__title:hover .el-icon) {
  color: #fff !important;
}

/* 已展开的子菜单 */
.app-menu :deep(.el-sub-menu.is-opened > .el-sub-menu__title .el-sub-menu__icon-arrow) {
  color: rgba(255, 255, 255, 0.7) !important;
}

/* 菜单项内容布局 */
.app-menu :deep(.el-menu-item) {
  display: flex;
  align-items: center;
  position: relative;
}

.app-menu :deep(.el-menu-item .el-icon) {
  margin-right: 8px;
}

.app-menu :deep(.el-menu-item > span) {
  flex: 1;
}

/* 菜单徽章 */
.item-badge {
  position: absolute;
  right: 16px;
  top: 0;
  height: 100%;
  display: flex;
  align-items: center;
}

.item-badge :deep(.el-badge__content) {
  position: relative;
  top: 0;
  transform: none;
  background-color: #f56c6c;
  border: none;
  font-size: 10px;
  height: 16px;
  line-height: 16px;
  padding: 0 5px;
}

.item-badge.success :deep(.el-badge__content) {
  background-color: #67c23a;
}

/* 折叠状态下隐藏角标 */
.app-menu :deep(.el-menu--collapse .el-menu-item .item-badge) {
  display: none;
}

/* 底部操作区 */
.aside-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* 顶部快捷操作按钮 */
.quick-actions-top {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.quick-actions-top .action-btn {
  width: 100%;
  height: 40px;
  font-size: 14px;
  font-weight: 500;
  margin-left: 0 !important;
  overflow: hidden;
  transition: width 0.3s ease, padding 0.3s ease, border-radius 0.3s ease;
}

.quick-actions-top.is-collapse .action-btn {
  width: 32px;
  height: 32px;
  padding: 0;
}

.quick-actions-top .btn-text {
  white-space: nowrap;
  margin-left: 6px;
}

.quick-actions-top .action-btn :deep(.el-icon) {
  flex-shrink: 0;
}

.quick-actions-top.is-collapse .btn-text {
  display: none;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s;
}

.collapse-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.collapse-text {
  font-size: 12px;
}

/* 主容器 */
.main-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部导航 */
.app-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-input {
  width: 200px;
}

.current-time {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-size: 13px;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 标签页导航 */
.tabs-nav {
  background: #fff;
  padding: 0 10px;
  border-bottom: 1px solid #e4e7ed;
}

.tabs-nav :deep(.el-tabs__header) {
  margin: 0;
  height: 36px;
}

.tabs-nav :deep(.el-tabs__item) {
  height: 32px;
  line-height: 32px;
}

/* 主内容区 */
.app-main {
  flex: 1;
  background: #f5f7fa;
  padding: 20px;
  overflow: auto;
}

/* 底部 */
.app-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}

.divider {
  color: #dcdfe6;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>