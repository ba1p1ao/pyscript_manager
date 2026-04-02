<template>
  <div class="scripts">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="loadScripts">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-button @click="reloadConfig">
            <el-icon><Upload /></el-icon> 重载配置
          </el-button>
        </div>
        <div class="toolbar-center">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索脚本名称或路径..."
            prefix-icon="Search"
            clearable
            style="width: 300px"
            @input="handleSearch"
          />
        </div>
        <div class="toolbar-right">
          <el-button type="success" @click="openAddDialog">
            <el-icon><Plus /></el-icon> 添加脚本
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 统计信息 -->
    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-value">{{ filteredScripts.length }}</div>
        <div class="stat-label">显示脚本</div>
      </div>
      <div class="stat-card running">
        <div class="stat-value">{{ runningCount }}</div>
        <div class="stat-label">运行中</div>
      </div>
      <div class="stat-card stopped">
        <div class="stat-value">{{ stoppedCount }}</div>
        <div class="stat-label">已停止</div>
      </div>
      <div class="stat-card scheduled">
        <div class="stat-value">{{ scheduledTotal }}</div>
        <div class="stat-label">定时任务</div>
      </div>
      <div class="stat-card enabled">
        <div class="stat-value">{{ enabledCount }}</div>
        <div class="stat-label">已启用</div>
      </div>
    </div>
    
    <!-- 脚本列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="filteredScripts" v-loading="loading" stripe row-key="name">
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/scripts/${row.name}`)">
              {{ row.name }}
            </el-link>
            <div class="script-desc" v-if="row.description">{{ row.description }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="script_path" label="脚本路径" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="script-path">{{ row.script_path }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="schedule_type" label="调度类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getScheduleTypeColor(row.schedule_type)" size="small">
              {{ row.schedule_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="schedule" label="调度配置" min-width="140">
          <template #default="{ row }">
            <span v-if="row.schedule_type === 'cron'">{{ row.schedule }}</span>
            <span v-else-if="row.schedule_type === 'interval'">每 {{ row.interval_seconds }} 秒</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_time" label="下次执行" width="160">
          <template #default="{ row }">
            <span v-if="row.schedule_type !== 'manual' && row.enabled">
              {{ formatTime(row.next_run_time) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="max_retries" label="重试次数" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getDisplayStatusType(row)" size="small">
              {{ getDisplayStatus(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="最后运行" width="160">
          <template #default="{ row }">
            {{ formatTime(row.last_run_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <!-- manual 类型：根据运行状态显示 -->
            <el-button 
              v-if="row.schedule_type === 'manual' && row.status !== 'running'"
              type="success" 
              size="small"
              @click="startScript(row.name)"
            >
              <el-icon><VideoPlay /></el-icon> 启动
            </el-button>
            <el-button 
              v-else-if="row.schedule_type === 'manual' && row.status === 'running'"
              type="warning" 
              size="small"
              @click="stopScript(row.name)"
            >
              <el-icon><VideoPause /></el-icon> 停止
            </el-button>
            <!-- cron/interval 类型：根据 auto_start 状态显示 -->
            <el-button 
              v-else-if="row.schedule_type !== 'manual'  && (!row.enabled || !row.auto_start)"
              type="success" 
              size="small"
              @click="startScript(row.name)"
            >
              <el-icon><VideoPlay /></el-icon> 启动
            </el-button>
            <el-button 
              v-else-if="row.schedule_type !== 'manual' && (row.enabled || row.auto_start)"
              type="warning" 
              size="small"
              @click="stopScript(row.name)"
            >
              <el-icon><VideoPause /></el-icon> 停止
            </el-button>
            <el-button type="primary" size="small" @click="openEditDialog(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-popconfirm
              title="确定要删除该脚本配置吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="deleteScript(row.name)"
            >
              <template #reference>
                <el-button type="danger" size="small">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEditing ? '编辑脚本' : '添加脚本'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="脚本名称" prop="name">
          <el-input v-model="form.name" :disabled="isEditing" placeholder="请输入脚本名称" />
        </el-form-item>
        
        <el-form-item label="脚本路径" prop="script_path">
          <el-input v-model="form.script_path" placeholder="请输入脚本绝对路径" />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="请输入脚本描述" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="调度类型">
              <el-select v-model="form.schedule_type" style="width: 100%" @change="onScheduleTypeChange">
                <el-option label="手动运行" value="manual" />
                <el-option label="Cron 定时" value="cron" />
                <el-option label="间隔运行" value="interval" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- Cron 表达式输入 -->
            <el-form-item v-if="form.schedule_type === 'cron'" label="Cron 表达式">
              <el-input 
                v-model="form.schedule" 
                placeholder="* * * * * (分 时 日 月 周)"
              />
              <div class="form-hint">例: 0 8 * * * 表示每天 8:00 执行</div>
            </el-form-item>
            <!-- 间隔秒数输入 -->
            <el-form-item v-else-if="form.schedule_type === 'interval'" label="间隔秒数">
              <el-input-number 
                v-model="form.interval_seconds" 
                :min="1" 
                :max="86400"
                style="width: 100%"
              />
              <div class="form-hint">每隔多少秒执行一次</div>
            </el-form-item>
            <!-- 手动运行提示 -->
            <el-form-item v-else label="调度配置">
              <span class="text-muted">手动运行需要通过界面或 API 触发</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大重试">
              <el-input-number v-model="form.max_retries" :min="0" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重试间隔">
              <el-input-number v-model="form.retry_delay" :min="1" style="width: 100%" />
              <template #append>秒</template>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="超时时间">
              <el-input-number v-model="form.timeout" :min="1" style="width: 100%" />
              <template #append>秒</template>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工作目录">
              <el-input v-model="form.working_dir" placeholder="可选" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="Python路径">
          <el-input v-model="form.python_path" placeholder="默认使用系统 Python" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-checkbox v-model="form.enabled">启用</el-checkbox>
          <el-checkbox v-model="form.auto_start" style="margin-left: 20px">自动启动</el-checkbox>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveScript">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { scriptApi } from '@/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const loading = ref(false)
const scripts = ref([])
const scheduledTotal = ref(0)
const searchKeyword = ref('')
const dialogVisible = ref(false)
const isEditing = ref(false)
const formRef = ref(null)

// 计算属性
const filteredScripts = computed(() => {
  if (!searchKeyword.value) return scripts.value
  
  const keyword = searchKeyword.value.toLowerCase()
  return scripts.value.filter(s => 
    s.name.toLowerCase().includes(keyword) ||
    s.script_path.toLowerCase().includes(keyword) ||
    (s.description && s.description.toLowerCase().includes(keyword))
  )
})

const runningCount = computed(() => scripts.value.filter(s => s.status === 'running').length)
// 已停止：只统计 manual 类型且 status 为 stopped 的脚本，排除定时任务
const stoppedCount = computed(() => scripts.value.filter(s => 
  s.schedule_type === 'manual' && s.status === 'stopped'
).length)
const enabledCount = computed(() => scripts.value.filter(s => s.enabled).length)

const form = ref({
  name: '',
  script_path: '',
  description: '',
  schedule_type: 'manual',
  schedule: '',
  interval_seconds: 300,
  max_retries: 3,
  retry_delay: 60,
  timeout: 3600,
  working_dir: '',
  python_path: '',
  enabled: true,
  auto_start: false
})

const rules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
  script_path: [{ required: true, message: '请输入脚本路径', trigger: 'blur' }]
}

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const getScheduleTypeColor = (type) => {
  const colors = { cron: 'primary', interval: 'warning', manual: 'info' }
  return colors[type] || 'info'
}

const getStatusType = (status) => {
  const types = { running: 'success', completed: 'primary', failed: 'danger', stopped: 'info' }
  return types[status] || 'info'
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

const loadScripts = async () => {
  loading.value = true
  try {
    const res = await scriptApi.list()
    if (res.success) {
      scripts.value = res.data
      scheduledTotal.value = res.scheduled_total || 0
    }
  } catch (e) {
    console.error('加载脚本失败:', e)
  } finally {
    loading.value = false
  }
}

const reloadConfig = async () => {
  try {
    const res = await scriptApi.reload()
    ElMessage.success(res.message)
    await loadScripts()
  } catch (e) {
    console.error('重载配置失败:', e)
  }
}

const handleSearch = () => {
  // 搜索逻辑已通过 computed 属性处理
}

const onScheduleTypeChange = () => {
  // 切换调度类型时重置相关字段
  if (form.value.schedule_type === 'cron') {
    form.value.schedule = ''
    form.value.interval_seconds = null
  } else if (form.value.schedule_type === 'interval') {
    form.value.schedule = null
    form.value.interval_seconds = form.value.interval_seconds || 300
  } else {
    form.value.schedule = null
    form.value.interval_seconds = null
  }
}

const openAddDialog = () => {
  isEditing.value = false
  form.value = {
    name: '',
    script_path: '',
    description: '',
    schedule_type: 'manual',
    schedule: '',
    interval_seconds: 300,
    max_retries: 3,
    retry_delay: 60,
    timeout: 3600,
    working_dir: '',
    python_path: '',
    enabled: true,
    auto_start: false
  }
  dialogVisible.value = true
}

const openEditDialog = (script) => {
  isEditing.value = true
  form.value = { 
    ...script,
    interval_seconds: script.interval_seconds || 300
  }
  dialogVisible.value = true
}

const saveScript = async () => {
  try {
    await formRef.value.validate()
    
    // 准备提交数据，根据调度类型过滤字段
    const submitData = { ...form.value }
    if (submitData.schedule_type === 'manual') {
      submitData.schedule = null
      submitData.interval_seconds = null
    } else if (submitData.schedule_type === 'cron') {
      submitData.interval_seconds = null
    } else if (submitData.schedule_type === 'interval') {
      submitData.schedule = null
    }
    
    if (isEditing.value) {
      await scriptApi.update(form.value.name, submitData)
      ElMessage.success('脚本更新成功')
    } else {
      await scriptApi.create(submitData)
      ElMessage.success('脚本添加成功')
    }
    
    dialogVisible.value = false
    await loadScripts()
  } catch (e) {
    console.error('保存失败:', e)
  }
}

const deleteScript = async (name) => {
  try {
    await scriptApi.delete(name)
    ElMessage.success('脚本删除成功')
    await loadScripts()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

const startScript = async (name) => {
  try {
    const res = await scriptApi.start(name)
    ElMessage.success(res.message)
    await loadScripts()
  } catch (e) {
    console.error('启动失败:', e)
  }
}

const stopScript = async (name) => {
  try {
    const res = await scriptApi.stop(name)
    ElMessage.success(res.message)
    await loadScripts()
  } catch (e) {
    console.error('停止失败:', e)
  }
}

// 监听路由参数变化
watch(
  () => route.query.search,
  (search) => {
    if (search) {
      searchKeyword.value = search
    }
  },
  { immediate: true }
)

onMounted(() => {
  loadScripts()
})
</script>

<style scoped>
.scripts {
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

.toolbar-left, .toolbar-right {
  display: flex;
  gap: 12px;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

/* 统计卡片 */
.stat-row {
  display: flex;
  gap: 16px;
}

.stat-card {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  border-left: 4px solid #409eff;
}

.stat-card.running {
  border-left-color: #67c23a;
}

.stat-card.stopped {
  border-left-color: #909399;
}

.stat-card.scheduled {
  border-left-color: #9b59b6;
}

.stat-card.enabled {
  border-left-color: #e6a23c;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-card.running .stat-value {
  color: #67c23a;
}

.stat-card.stopped .stat-value {
  color: #909399;
}

.stat-card.scheduled .stat-value {
  color: #9b59b6;
}

.stat-card.enabled .stat-value {
  color: #e6a23c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.table-card {
  flex: 1;
}

.script-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.script-path {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: #606266;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.text-muted {
  color: #909399;
}
</style>
