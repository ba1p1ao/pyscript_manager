<template>
  <div class="processes">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="loadProcesses">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <span class="process-count">共 {{ processes.length }} 个 Python 进程</span>
        </div>
        <div class="toolbar-right">
          <el-button 
            type="danger" 
            :disabled="selectedPids.length === 0"
            @click="showKillConfirm"
          >
            <el-icon><SwitchButton /></el-icon>
            终止选中 ({{ selectedPids.length }})
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 进程列表 -->
    <el-card shadow="never" class="table-card">
      <el-table 
        :data="processes" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
        stripe
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="pid" label="PID" width="100">
          <template #default="{ row }">
            <el-tag effect="plain">{{ row.pid }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cmdline" label="命令行" min-width="300" show-overflow-tooltip />
        <el-table-column prop="cpu_percent" label="CPU" width="150">
          <template #default="{ row }">
            <div class="cpu-cell">
              <span>{{ row.cpu_percent?.toFixed(1) }}%</span>
              <el-progress 
                :percentage="Math.min(row.cpu_percent || 0, 100)" 
                :stroke-width="6"
                :show-text="false"
                :color="getCpuColor(row.cpu_percent)"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="memory_mb" label="内存 (MB)" width="120">
          <template #default="{ row }">
            {{ row.memory_mb?.toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="启动时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
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
import { processApi } from '@/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const processes = ref([])
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
  loading.value = true
  try {
    const res = await processApi.list()
    if (res.success) {
      processes.value = res.data
    }
  } catch (e) {
    console.error('加载进程失败:', e)
  } finally {
    loading.value = false
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

onMounted(() => {
  loadProcesses()
  refreshTimer = setInterval(loadProcesses, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.processes {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.process-count {
  color: #909399;
  font-size: 14px;
}

.table-card {
  flex: 1;
}

.cpu-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
