<template>
  <div class="system-logs">
    <!-- 筛选工具栏 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="日志级别">
          <el-select v-model="filters.level" placeholder="全部" clearable @change="loadLogs">
            <el-option label="INFO" value="INFO" />
            <el-option label="WARNING" value="WARNING" />
            <el-option label="ERROR" value="ERROR" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" placeholder="全部" clearable @change="loadLogs">
            <el-option label="启动脚本" value="start_script" />
            <el-option label="停止脚本" value="stop_script" />
            <el-option label="终止进程" value="kill_process" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 日志列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="140">
          <template #default="{ row }">
            {{ row.module || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作" width="120" />
        <el-table-column prop="target" label="目标" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.target || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="详情" min-width="200" show-overflow-tooltip />
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { systemLogApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 50

const filters = ref({
  level: '',
  action: ''
})

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getLevelType = (level) => {
  const types = { INFO: 'primary', WARNING: 'warning', ERROR: 'danger' }
  return types[level] || 'info'
}

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize
    }
    if (filters.value.level) {
      params.level = filters.value.level
    }
    if (filters.value.action) {
      params.action = filters.value.action
    }
    
    const res = await systemLogApi.list(params)
    if (res.success) {
      logs.value = res.data
      total.value = res.total
    }
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadLogs()
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.system-logs {
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
