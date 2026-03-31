<template>
  <div class="history">
    <!-- 筛选工具栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="脚本名称">
          <el-select v-model="filters.script_name" placeholder="全部" clearable @change="loadHistory">
            <el-option 
              v-for="name in scriptNames" 
              :key="name" 
              :label="name" 
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable @change="loadHistory">
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已停止" value="stopped" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadHistory">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 历史列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="historyList" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="script_name" label="脚本名称" min-width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/scripts/${row.script_name}`)">
              {{ row.script_name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="pid" label="PID" width="100">
          <template #default="{ row }">
            <span class="mono">{{ row.pid || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.end_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="运行时长" width="100">
          <template #default="{ row }">
            {{ row.duration ? row.duration + ' 秒' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="exit_code" label="退出码" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.exit_code !== null" :type="row.exit_code === 0 ? 'success' : 'danger'" size="small">
              {{ row.exit_code }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="retry_count" label="重试" width="70" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button 
              v-if="row.error_message"
              type="warning" 
              size="small"
              @click="showError(row)"
            >
              <el-icon><Warning /></el-icon> 错误
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <span class="total">共 {{ total }} 条记录</span>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <!-- 错误详情对话框 -->
    <el-dialog v-model="errorDialogVisible" title="错误详情" width="700px">
      <pre class="log-output">{{ currentError }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { historyApi, scriptApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const historyList = ref([])
const scriptNames = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const errorDialogVisible = ref(false)
const currentError = ref('')

const filters = ref({
  script_name: '',
  status: ''
})

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getStatusType = (status) => {
  const types = { running: 'success', completed: 'primary', failed: 'danger', stopped: 'info' }
  return types[status] || 'info'
}

const loadScriptNames = async () => {
  try {
    const res = await scriptApi.list()
    if (res.success) {
      scriptNames.value = res.data.map(s => s.name)
    }
  } catch (e) {
    console.error('加载脚本名称失败:', e)
  }
}

const loadHistory = async () => {
  loading.value = true
  try {
    const params = {
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize
    }
    if (filters.value.script_name) {
      params.script_name = filters.value.script_name
    }
    if (filters.value.status) {
      params.status = filters.value.status
    }
    
    const res = await historyApi.list(params)
    if (res.success) {
      historyList.value = res.data
      total.value = res.total
    }
  } catch (e) {
    console.error('加载历史失败:', e)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadHistory()
}

const showError = (row) => {
  currentError.value = row.error_message
  errorDialogVisible.value = true
}

onMounted(() => {
  loadScriptNames()
  loadHistory()
})
</script>

<style scoped>
.history {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  padding: 16px 16px 0;
}

.table-card {
  flex: 1;
}

.mono {
  font-family: 'Consolas', 'Monaco', monospace;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0 0;
}

.total {
  color: #909399;
  font-size: 14px;
}
</style>
