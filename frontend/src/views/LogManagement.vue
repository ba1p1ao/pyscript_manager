<template>
  <div class="log-management">
    <!-- 日志统计 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon primary">
              <el-icon :size="32"><Folder /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_size_mb }} MB</div>
              <div class="stat-label">日志总大小</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon success">
              <el-icon :size="32"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.script_count }}</div>
              <div class="stat-label">脚本数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon warning">
              <el-icon :size="32"><Tickets /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.db_history_count }}</div>
              <div class="stat-label">历史记录数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon info">
              <el-icon :size="32"><Memo /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.db_system_log_count }}</div>
              <div class="stat-label">系统日志数</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 日志详情 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="card-header">
              <el-icon><FolderOpened /></el-icon>
              <span>应用日志</span>
            </div>
          </template>
          <div class="detail-item">
            <span class="label">文件数量:</span>
            <span class="value">{{ stats.app_logs?.file_count || 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="label">占用空间:</span>
            <span class="value">{{ stats.app_logs?.size_mb || 0 }} MB</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>脚本日志</span>
            </div>
          </template>
          <div class="detail-item">
            <span class="label">文件数量:</span>
            <span class="value">{{ stats.script_logs?.file_count || 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="label">占用空间:</span>
            <span class="value">{{ stats.script_logs?.size_mb || 0 }} MB</span>
          </div>
          <div class="detail-item" v-if="stats.oldest_log_date">
            <span class="label">最早日志:</span>
            <span class="value">{{ stats.oldest_log_date }}</span>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="never" class="detail-card">
          <template #header>
            <div class="card-header">
              <el-icon><Files /></el-icon>
              <span>归档日志</span>
            </div>
          </template>
          <div class="detail-item">
            <span class="label">文件数量:</span>
            <span class="value">{{ stats.archive_logs?.file_count || 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="label">占用空间:</span>
            <span class="value">{{ stats.archive_logs?.size_mb || 0 }} MB</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 清理配置 -->
    <el-card shadow="never" class="config-card">
      <template #header>
        <div class="card-header">
          <div class="title">
            <el-icon><Setting /></el-icon>
            <span>清理配置</span>
          </div>
          <el-button type="primary" size="small" @click="saveConfig" :loading="saving">
            保存配置
          </el-button>
        </div>
      </template>
      
      <el-form :model="config" label-width="160px" class="config-form">
        <el-row :gutter="40">
          <el-col :span="12">
            <el-form-item label="脚本日志保留天数">
              <el-input-number v-model="config.script_retention_days" :min="1" :max="365" />
              <span class="hint">超过此天数的日志将被删除</span>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="历史记录保留数量">
              <el-input-number v-model="config.history_retention_count" :min="10" :max="10000" :step="100" />
              <span class="hint">每个脚本保留的运行记录数</span>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="系统日志保留天数">
              <el-input-number v-model="config.system_log_retention_days" :min="1" :max="365" />
              <span class="hint">系统操作日志保留时间</span>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="归档触发天数">
              <el-input-number v-model="config.archive_after_days" :min="1" :max="30" />
              <span class="hint">超过此天数的日志将被压缩归档</span>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="归档保留天数">
              <el-input-number v-model="config.archive_retention_days" :min="1" :max="365" />
              <span class="hint">归档文件的保留时间</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      
      <div class="log-dirs">
        <div class="dir-item">
          <span class="label">应用日志目录:</span>
          <span class="path">{{ config.log_dirs?.app || '-' }}</span>
        </div>
        <div class="dir-item">
          <span class="label">脚本日志目录:</span>
          <span class="path">{{ config.log_dirs?.scripts || '-' }}</span>
        </div>
        <div class="dir-item">
          <span class="label">归档目录:</span>
          <span class="path">{{ config.log_dirs?.archive || '-' }}</span>
        </div>
      </div>
    </el-card>
    
    <!-- 手动清理 -->
    <el-card shadow="never" class="clean-card">
      <template #header>
        <div class="card-header">
          <div class="title">
            <el-icon><Delete /></el-icon>
            <span>手动清理</span>
          </div>
        </div>
      </template>
      
      <div class="clean-options">
        <el-checkbox v-model="cleanOptions.clean_scripts">清理脚本日志文件</el-checkbox>
        <el-checkbox v-model="cleanOptions.clean_history">清理历史记录</el-checkbox>
        <el-checkbox v-model="cleanOptions.clean_system_logs">清理系统日志</el-checkbox>
        <el-checkbox v-model="cleanOptions.archive">归档旧日志</el-checkbox>
      </div>
      
      <div class="clean-action">
        <el-button 
          type="danger" 
          @click="handleClean"
          :loading="cleaning"
          :disabled="!hasCleanOption"
        >
          <el-icon><Delete /></el-icon>
          执行清理
        </el-button>
        <span class="hint">注意：清理操作不可恢复，请谨慎操作</span>
      </div>
      
      <!-- 清理结果 -->
      <el-collapse v-if="cleanResult" class="clean-result">
        <el-collapse-item title="清理结果" name="result">
          <div class="result-grid">
            <div class="result-item">
              <span class="label">删除日志文件:</span>
              <span class="value">{{ cleanResult.script_logs_deleted }} 个</span>
            </div>
            <div class="result-item">
              <span class="label">释放空间:</span>
              <span class="value">{{ cleanResult.script_logs_freed_mb }} MB</span>
            </div>
            <div class="result-item">
              <span class="label">创建归档:</span>
              <span class="value">{{ cleanResult.archives_created }} 个</span>
            </div>
            <div class="result-item">
              <span class="label">删除归档:</span>
              <span class="value">{{ cleanResult.archives_deleted }} 个</span>
            </div>
            <div class="result-item">
              <span class="label">删除历史记录:</span>
              <span class="value">{{ cleanResult.history_deleted }} 条</span>
            </div>
            <div class="result-item">
              <span class="label">删除系统日志:</span>
              <span class="value">{{ cleanResult.system_logs_deleted }} 条</span>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { logManagementApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const cleaning = ref(false)

// 统计数据
const stats = ref({
  total_size_mb: 0,
  script_count: 0,
  db_history_count: 0,
  db_system_log_count: 0,
  app_logs: { file_count: 0, size_mb: 0 },
  script_logs: { file_count: 0, size_mb: 0 },
  archive_logs: { file_count: 0, size_mb: 0 },
  oldest_log_date: null
})

// 配置数据
const config = ref({
  script_retention_days: 30,
  history_retention_count: 500,
  system_log_retention_days: 30,
  archive_after_days: 7,
  archive_retention_days: 90,
  log_dirs: {}
})

// 清理选项
const cleanOptions = ref({
  clean_scripts: true,
  clean_history: true,
  clean_system_logs: true,
  archive: true
})

// 清理结果
const cleanResult = ref(null)

const hasCleanOption = computed(() => {
  return Object.values(cleanOptions.value).some(v => v)
})

// 加载统计数据
const loadStats = async () => {
  loading.value = true
  try {
    const res = await logManagementApi.getStats()
    if (res.success) {
      stats.value = res.data
    }
  } catch (e) {
    console.error('加载统计失败:', e)
  } finally {
    loading.value = false
  }
}

// 加载配置
const loadConfig = async () => {
  try {
    const res = await logManagementApi.getConfig()
    if (res.success) {
      config.value = res.data
    }
  } catch (e) {
    console.error('加载配置失败:', e)
  }
}

// 保存配置
const saveConfig = async () => {
  saving.value = true
  try {
    const res = await logManagementApi.updateConfig({
      script_retention_days: config.value.script_retention_days,
      history_retention_count: config.value.history_retention_count,
      system_log_retention_days: config.value.system_log_retention_days,
      archive_after_days: config.value.archive_after_days,
      archive_retention_days: config.value.archive_retention_days
    })
    if (res.success) {
      ElMessage.success('配置保存成功')
    }
  } catch (e) {
    console.error('保存配置失败:', e)
  } finally {
    saving.value = false
  }
}

// 执行清理
const handleClean = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要执行日志清理吗？此操作不可恢复！',
      '确认清理',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    cleaning.value = true
    cleanResult.value = null
    
    const res = await logManagementApi.clean(cleanOptions.value)
    if (res.success) {
      ElMessage.success('清理完成')
      cleanResult.value = res.results
      // 刷新统计
      await loadStats()
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('清理失败:', e)
    }
  } finally {
    cleaning.value = false
  }
}

onMounted(() => {
  loadStats()
  loadConfig()
})
</script>

<style scoped>
.log-management {
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
.stat-icon.info { background: linear-gradient(135deg, #3498db, #85c1e9); }

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.detail-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header .title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item .label {
  color: #909399;
}

.detail-item .value {
  font-weight: 500;
  color: #303133;
}

.config-card {
  margin-top: 0;
}

.config-form {
  margin-bottom: 20px;
}

.config-form .hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.log-dirs {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
}

.dir-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.dir-item .label {
  color: #606266;
  min-width: 100px;
}

.dir-item .path {
  font-family: monospace;
  color: #303133;
  background: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
}

.clean-card {
  margin-top: 0;
}

.clean-options {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.clean-action {
  display: flex;
  align-items: center;
  gap: 16px;
}

.clean-action .hint {
  color: #909399;
  font-size: 13px;
}

.clean-result {
  margin-top: 20px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.result-item .label {
  color: #606266;
}

.result-item .value {
  font-weight: 500;
  color: #303133;
}
</style>
