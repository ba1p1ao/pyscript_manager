import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 进程管理 API
export const processApi = {
  list: () => api.get('/processes'),
  get: (pid) => api.get(`/processes/${pid}`),
  kill: (pids, force = false) => api.post('/processes/kill', { pids, force }),
  killOne: (pid, force = false) => api.delete(`/processes/${pid}?force=${force}`)
}

// 脚本配置 API
export const scriptApi = {
  list: () => api.get('/scripts'),
  create: (data) => api.post('/scripts', data),
  update: (name, data) => api.put(`/scripts/${name}`, data),
  delete: (name) => api.delete(`/scripts/${name}`),
  reload: () => api.post('/scripts/reload'),
  start: (name) => api.post(`/scripts/${name}/start`),
  stop: (name) => api.post(`/scripts/${name}/stop`),
  getLog: (name, lines = 200) => api.get(`/scripts/${name}/log?lines=${lines}`),
  getHistory: (name, limit = 20) => api.get(`/scripts/${name}/history?limit=${limit}`)
}

// 历史记录 API
export const historyApi = {
  list: (params) => api.get('/history', { params })
}

// 系统日志 API
export const systemLogApi = {
  list: (params) => api.get('/system-logs', { params })
}

// 统计 API
export const statsApi = {
  get: () => api.get('/stats')
}

// 定时任务 API
export const scheduledApi = {
  list: () => api.get('/scheduled')
}

// 日志管理 API
export const logManagementApi = {
  // 获取日志统计
  getStats: () => api.get('/logs/stats'),
  // 获取日志配置
  getConfig: () => api.get('/logs/config'),
  // 更新日志配置
  updateConfig: (data) => api.put('/logs/config', data),
  // 手动清理日志
  clean: (params) => api.post('/logs/clean', null, { params })
}

export default api
