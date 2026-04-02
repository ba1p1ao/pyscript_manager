<template>
  <div class="script-detail">
    <!-- 返回按钮 -->
    <div class="back-link">
      <el-link type="primary" @click="$router.push('/scripts')">
        <el-icon><ArrowLeft /></el-icon> 返回脚本列表
      </el-link>
    </div>
    
    <el-row :gutter="20">
      <!-- 脚本信息 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>脚本信息</span>
              <div>
                <!-- manual 类型：根据运行状态显示 -->
                <el-button 
                  v-if="script.schedule_type === 'manual' && script.status !== 'running'"
                  type="success" 
                  @click="startScript"
                >
                  <el-icon><VideoPlay /></el-icon> 启动
                </el-button>
                <el-button 
                  v-else-if="script.schedule_type === 'manual' && script.status === 'running'"
                  type="warning" 
                  @click="stopScript"
                >
                  <el-icon><VideoPause /></el-icon> 停止
                </el-button>
                <!-- cron/interval 类型：根据 enabled 状态显示 -->
                <el-button 
                  v-else-if="script.schedule_type !== 'manual' && !script.enabled"
                  type="success" 
                  @click="startScript"
                >
                  <el-icon><VideoPlay /></el-icon> 启动
                </el-button>
                <el-button 
                  v-else-if="script.schedule_type !== 'manual' && script.enabled"
                  type="warning" 
                  @click="stopScript"
                >
                  <el-icon><VideoPause /></el-icon> 停止
                </el-button>
              </div>
            </div>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="脚本路径">
              <span class="mono">{{ script.script_path }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="当前状态">
              <el-tag :type="getDisplayStatusType(script)">
                {{ getDisplayStatus(script) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="调度类型">
              <el-tag :type="getScheduleTypeColor(script.schedule_type)" size="small">
                {{ script.schedule_type }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="调度配置">
              <span v-if="script.schedule_type === 'cron'">{{ script.schedule }}</span>
              <span v-else-if="script.schedule_type === 'interval'">每 {{ script.interval_seconds }} 秒</span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="下次执行" v-if="script.schedule_type !== 'manual'">
              <span>{{ formatTime(script.next_run_time) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="最大重试">{{ script.max_retries }}</el-descriptions-item>
            <el-descriptions-item label="超时时间">{{ script.timeout }} 秒</el-descriptions-item>
            <el-descriptions-item label="当前 PID">
              <span class="mono">{{ script.current_pid || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="最后运行">{{ formatTime(script.last_run_time) }}</el-descriptions-item>
          </el-descriptions>
          
          <div v-if="script.description" style="margin-top: 16px">
            <span class="label">描述：</span>
            <span>{{ script.description }}</span>
          </div>
        </el-card>
        
        <!-- 日志输出 -->
        <el-card shadow="never" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>日志输出</span>
              <div>
                <el-button size="small" @click="loadLog">
                  <el-icon><Refresh /></el-icon> 刷新
                </el-button>
                <el-button 
                  size="small" 
                  :type="autoRefresh ? 'primary' : 'default'"
                  @click="autoRefresh = !autoRefresh"
                >
                  <el-icon><Clock /></el-icon>
                  {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
                </el-button>
              </div>
            </div>
          </template>
          
          <pre class="log-output">{{ logContent || '暂无日志' }}</pre>
        </el-card>
      </el-col>
      
      <!-- 运行统计 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <span>运行统计</span>
          </template>
          
          <div class="stat-item">
            <span class="stat-label">总运行次数</span>
            <span class="stat-value">{{ stats.total }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">成功次数</span>
            <span class="stat-value success">{{ stats.success }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">失败次数</span>
            <span class="stat-value danger">{{ stats.failed }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">成功率</span>
            <span class="stat-value primary">{{ stats.successRate }}</span>
          </div>
        </el-card>
        
        <!-- 运行历史 -->
        <el-card shadow="never" style="margin-top: 20px">
          <template #header>
            <span>运行历史</span>
          </template>
          
          <el-table :data="history" size="small" max-height="400">
            <el-table-column prop="pid" label="PID" width="70" />
            <el-table-column prop="start_time" label="开始时间" width="140">
              <template #default="{ row }">
                {{ formatTimeShort(row.start_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="时长" width="70">
              <template #default="{ row }">
                {{ row.duration ? row.duration + 's' : '-' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { scriptApi } from '@/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const scriptName = computed(() => route.params.name)

const script = ref({})
const logContent = ref('')
const history = ref([])
const stats = ref({ total: 0, success: 0, failed: 0, successRate: '0%' })
const autoRefresh = ref(false)

let refreshTimer = null

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const formatTimeShort = (time) => {
  return time ? dayjs(time).format('MM-DD HH:mm') : '-'
}

const getStatusType = (status) => {
  const types = { running: 'success', completed: 'primary', failed: 'danger', stopped: 'info' }
  return types[status] || 'info'
}

const getScheduleTypeColor = (type) => {
  const colors = { cron: 'primary', interval: 'warning', manual: 'info' }
  return colors[type] || 'info'
}

// 获取显示状态：cron/interval 类型根据 enabled 显示 scheduled/stopped
const getDisplayStatus = (row) => {
  if (row.schedule_type === 'manual') {
    return row.status
  }
  // cron/interval 类型
  return row.enabled ? 'scheduled' : 'stopped'
}

// 获取显示状态颜色
const getDisplayStatusType = (row) => {
  if (row.schedule_type === 'manual') {
    return getStatusType(row.status)
  }
  // cron/interval 类型
  return row.enabled ? 'success' : 'info'
}

const loadScript = async () => {
  try {
    const res = await scriptApi.list()
    if (res.success) {
      script.value = res.data.find(s => s.name === scriptName.value) || {}
    }
  } catch (e) {
    console.error('加载脚本信息失败:', e)
  }
}

const loadLog = async () => {
  try {
    const res = await scriptApi.getLog(scriptName.value, 500)
    if (res.success) {
      logContent.value = res.log_content
    }
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

const loadHistory = async () => {
  try {
    const res = await scriptApi.getHistory(scriptName.value, 20)
    if (res.success) {
      history.value = res.data
      calculateStats()
    }
  } catch (e) {
    console.error('加载历史失败:', e)
  }
}

const calculateStats = () => {
  const h = history.value
  stats.value.total = h.length
  stats.value.success = h.filter(item => item.status === 'completed').length
  stats.value.failed = h.filter(item => item.status === 'failed').length
  stats.value.successRate = stats.value.total > 0 
    ? Math.round(stats.value.success / stats.value.total * 100) + '%' 
    : '0%'
}

const startScript = async () => {
  try {
    const res = await scriptApi.start(scriptName.value)
    ElMessage.success(res.message)
    await Promise.all([loadScript(), loadHistory()])
  } catch (e) {
    console.error('启动失败:', e)
  }
}

const stopScript = async () => {
  try {
    const res = await scriptApi.stop(scriptName.value)
    ElMessage.success(res.message)
    await Promise.all([loadScript(), loadHistory()])
  } catch (e) {
    console.error('停止失败:', e)
  }
}

onMounted(async () => {
  await Promise.all([loadScript(), loadLog(), loadHistory()])
  
  refreshTimer = setInterval(() => {
    if (autoRefresh.value) loadLog()
    loadScript()
    loadHistory()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.script-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-link {
  margin-bottom: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mono {
  font-family: 'Consolas', 'Monaco', monospace;
}

.label {
  color: #909399;
  margin-right: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #909399;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
}

.stat-value.success { color: #67c23a; }
.stat-value.danger { color: #f56c6c; }
.stat-value.primary { color: #409eff; }

.text-muted {
  color: #909399;
}
</style>
