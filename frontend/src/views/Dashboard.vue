<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon primary">
              <el-icon :size="32"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_scripts }}</div>
              <div class="stat-label">总脚本数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon success">
              <el-icon :size="32"><VideoPlay /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.running_scripts }}</div>
              <div class="stat-label">运行中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon scheduled">
              <el-icon :size="32"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.scheduled_active }}/{{ stats.scheduled_total }}</div>
              <div class="stat-label">定时任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon warning">
              <el-icon :size="32"><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.python_processes }}</div>
              <div class="stat-label">Python 进程</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 今日统计 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="12">
        <el-card shadow="hover" class="stat-card today-card">
          <div class="stat-content">
            <div class="stat-icon info">
              <el-icon :size="32"><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.today_runs }}</div>
              <div class="stat-label">今日运行</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover" class="stat-card today-card">
          <div class="stat-content">
            <div class="stat-icon danger">
              <el-icon :size="32"><CircleClose /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.today_failed }}</div>
              <div class="stat-label">今日失败</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最近运行记录 -->
    <el-card shadow="never" class="history-card">
      <template #header>
        <div class="card-header">
          <span>最近运行记录</span>
          <el-button type="primary" link @click="$router.push('/history')">
            查看全部 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </template>
      
      <el-table :data="historyList" v-loading="loading" stripe>
        <el-table-column prop="script_name" label="脚本名称" min-width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/scripts/${row.script_name}`)">
              {{ row.script_name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="pid" label="PID" width="100" />
        <el-table-column prop="start_time" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="运行时长" width="120">
          <template #default="{ row }">
            {{ row.duration ? row.duration + ' 秒' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="$router.push(`/scripts/${row.script_name}`)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, onActivated } from 'vue'
import { statsApi, historyApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const stats = ref({
  total_scripts: 0,
  running_scripts: 0,
  python_processes: 0,
  scheduled_total: 0,
  scheduled_active: 0,
  today_runs: 0,
  today_failed: 0
})
const historyList = ref([])
let refreshTimer = null

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getStatusType = (status) => {
  const types = {
    running: 'success',
    completed: 'primary',
    failed: 'danger',
    stopped: 'info'
  }
  return types[status] || 'info'
}

const loadData = async () => {
  loading.value = true
  try {
    const [statsRes, historyRes] = await Promise.all([
      statsApi.get(),
      historyApi.list({ limit: 10 })
    ])
    
    if (statsRes.success) {
      stats.value = statsRes.data
    }
    if (historyRes.success) {
      historyList.value = historyRes.data
    }
  } catch (e) {
    console.error('加载数据失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  // 定时刷新
  refreshTimer = setInterval(loadData, 70000)
})

// 当组件被 keep-alive 缓存后重新激活时，刷新数据
onActivated(() => {
  loadData()
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stat-cards {
  margin-bottom: 0;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-icon.primary { background: linear-gradient(135deg, #409eff, #66b1ff); }
.stat-icon.success { background: linear-gradient(135deg, #67c23a, #85ce61); }
.stat-icon.warning { background: linear-gradient(135deg, #e6a23c, #f0c78a); }
.stat-icon.danger { background: linear-gradient(135deg, #f56c6c, #fab6b6); }
.stat-icon.scheduled { background: linear-gradient(135deg, #9b59b6, #c39bd3); }
.stat-icon.info { background: linear-gradient(135deg, #3498db, #85c1e9); }

.today-card {
  margin-top: 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.history-card {
  flex: 1;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
