<template>
  <div class="processes">
    <!-- 定时任务 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <el-icon><Clock /></el-icon>
            <span>定时任务</span>
            <el-tag type="info" size="small">{{ scheduledTasks.length }} 个</el-tag>
          </div>
          <el-button type="primary" size="small" @click="loadScheduledTasks">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      
      <el-table :data="scheduledTasks" v-loading="scheduledLoading" stripe size="small">
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/scripts/${row.name}`)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="schedule_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.schedule_type === 'cron' ? 'primary' : 'warning'" size="small">
              {{ row.schedule_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="schedule" label="调度配置" min-width="140">
          <template #default="{ row }">
            <span v-if="row.schedule_type === 'cron'">{{ row.schedule }}</span>
            <span v-else>每 {{ row.interval_seconds }} 秒</span>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_time" label="下次执行" width="160">
          <template #default="{ row }">
            <span v-if="row.enabled && row.next_run_time">{{ formatTime(row.next_run_time) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '运行中' : '已停止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="!row.enabled"
              type="success" 
              size="small"
              @click="startScheduled(row.name)"
            >
              启动
            </el-button>
            <el-button 
              v-else
              type="warning" 
              size="small"
              @click="stopScheduled(row.name)"
            >
              停止
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- Python 进程 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="section-header">
          <div class="section-title">
            <el-icon><Monitor /></el-icon>
            <span>Python 进程</span>
            <el-tag type="info" size="small">{{ processes.length }} 个</el-tag>
          </div>
          <div class="section-actions">
            <el-button type="primary" size="small" @click="loadProcesses">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
            <el-button 
              type="danger" 
              size="small"
              :disabled="selectedPids.length === 0"
              @click="showKillConfirm"
            >
              终止选中 ({{ selectedPids.length }})
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="processes" 
        v-loading="processLoading"
        @selection-change="handleSelectionChange"
        stripe
        size="small"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="pid" label="PID" width="100">
          <template #default="{ row }">
            <el-tag effect="plain" size="small">{{ row.pid }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cmdline" label="命令行" min-width="300" show-overflow-tooltip />
        <el-table-column prop="cpu_percent" label="CPU" width="120">
          <template #default="{ row }">
            <div class="cpu-cell">
              <span>{{ row.cpu_percent?.toFixed(1) }}%</span>
              <el-progress 
                :percentage="Math.min(row.cpu_percent || 0, 100)" 
                :stroke-width="4"
                :show-text="false"
                :color="getCpuColor(row.cpu_percent)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="memory_mb" label="内存 (MB)" width="100">
          <template #default="{ row }">
            {{ row.memory_mb?.toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="启动时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-popconfirm
              title="确定要终止该进程吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="killProcess(row.pid)"
            >
              <template #reference>
                <el-button type="danger" size="small">终止</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 批量终止确认对话框 -->
    <el-dialog v-model="killDialogVisible" title="确认终止进程" width="400px">
      <p>确定要终止选中的 {{ selectedPids.length }} 个进程吗？此操作不可撤销。</p>
      <template #footer>
        <el-button @click="killDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmKillSelected">确认终止</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { processApi, scheduledApi, scriptApi } from '@/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const processLoading = ref(false)
const scheduledLoading = ref(false)
const processes = ref([])
const scheduledTasks = ref([])
const selectedPids = ref([])
const killDialogVisible = ref(false)
let refreshTimer = null

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getCpuColor = (cpu) => {
  if (cpu > 80) return '#f56c6c'
  if (cpu > 50) return '#e6a23c'
  return '#67c23a'
}

const loadProcesses = async () => {
  processLoading.value = true
  try {
    const res = await processApi.list()
    if (res.success) {
      processes.value = res.data
    }
  } catch (e) {
    console.error('加载进程失败:', e)
  } finally {
    processLoading.value = false
  }
}

const loadScheduledTasks = async () => {
  scheduledLoading.value = true
  try {
    const res = await scheduledApi.list()
    if (res.success) {
      scheduledTasks.value = res.data
    }
  } catch (e) {
    console.error('加载定时任务失败:', e)
  } finally {
    scheduledLoading.value = false
  }
}

const startScheduled = async (name) => {
  try {
    const res = await scriptApi.start(name)
    ElMessage.success(res.message)
    await loadScheduledTasks()
  } catch (e) {
    console.error('启动失败:', e)
  }
}

const stopScheduled = async (name) => {
  try {
    const res = await scriptApi.stop(name)
    ElMessage.success(res.message)
    await loadScheduledTasks()
  } catch (e) {
    console.error('停止失败:', e)
  }
}

const handleSelectionChange = (selection) => {
  selectedPids.value = selection.map(p => p.pid)
}

const showKillConfirm = () => {
  killDialogVisible.value = true
}

const killProcess = async (pid) => {
  try {
    await processApi.killOne(pid)
    ElMessage.success(`进程 ${pid} 已终止`)
    await loadProcesses()
  } catch (e) {
    console.error('终止进程失败:', e)
  }
}

const confirmKillSelected = async () => {
  killDialogVisible.value = false
  try {
    const res = await processApi.kill(selectedPids.value)
    ElMessage.success(res.message)
    selectedPids.value = []
    await loadProcesses()
  } catch (e) {
    console.error('批量终止失败:', e)
  }
}

const loadAll = () => {
  loadProcesses()
  loadScheduledTasks()
}

// 智能刷新：页面可见时刷新
const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    loadAll()
    refreshTimer = setInterval(loadAll, 60000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

onMounted(() => {
  loadAll()
  refreshTimer = setInterval(loadAll, 60000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.processes {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-card {
  flex: 1;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.cpu-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.text-muted {
  color: #909399;
}
</style>
