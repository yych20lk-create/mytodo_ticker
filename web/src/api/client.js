import axios from 'axios'

/** 从 hash query 或 location 解析 API 基址（WebEngine 宿主会注入） */
export function resolveApiBase() {
  try {
    const hash = window.location.hash || ''
    const qi = hash.indexOf('?')
    if (qi >= 0) {
      const qs = new URLSearchParams(hash.slice(qi + 1))
      const api = qs.get('api')
      if (api) return api.replace(/\/$/, '')
    }
  } catch (_) {}
  // 开发代理
  return ''
}

const http = axios.create({
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const base = resolveApiBase()
  if (base && !config.url?.startsWith('http')) {
    config.baseURL = base
  }
  return config
})

export async function getHealth() {
  const { data } = await http.get('/api/health')
  return data
}

export async function getMeta() {
  const { data } = await http.get('/api/meta')
  return data
}

export async function listTasks() {
  const { data } = await http.get('/api/tasks')
  return data.items || []
}

export async function getTask(id) {
  const { data } = await http.get(`/api/tasks/${id}`)
  return data.item
}

export async function createTask(payload) {
  const { data } = await http.post('/api/tasks', payload)
  return data.item
}

export async function updateTask(id, payload) {
  const { data } = await http.put(`/api/tasks/${id}`, payload)
  return data.item
}

export async function updateProgress(id, percent, note = '') {
  const { data } = await http.post(`/api/tasks/${id}/progress`, { percent, note })
  return data.item
}

export async function markDone(id) {
  await http.post(`/api/tasks/${id}/done`)
}

export async function abandonTask(id) {
  await http.post(`/api/tasks/${id}/abandon`)
}

export async function selectTask(id) {
  await http.post(`/api/tasks/${id}/select`)
}

/** 已加载的脚本/服务插件列表（设置未启用时 items 为空） */
export async function listPlugins() {
  const { data } = await http.get('/api/plugins')
  return data
}

/** 运行插件：script 传 {}；service 传 { action: 'start'|'stop'|'status' } */
export async function runPlugin(id, body = {}) {
  const { data } = await http.post(`/api/plugins/${id}/run`, body)
  return data
}

/**
 * 检查弹窗提醒时间冲突（任务/周期模板/每日计划/复盘）
 * body: { reminder, exclude_task_id?, exclude_template_id? }
 */
export async function checkReminderConflicts(body) {
  const { data } = await http.post('/api/reminders/check-conflicts', body)
  return data
}

export async function listTemplates() {
  const { data } = await http.get('/api/templates')
  return data.items || []
}

export async function getTemplate(id) {
  const { data } = await http.get(`/api/templates/${id}`)
  return data.item
}

export async function createTemplate(payload) {
  const { data } = await http.post('/api/templates', payload)
  return data.item
}

export async function updateTemplate(id, payload) {
  const { data } = await http.put(`/api/templates/${id}`, payload)
  return data.item
}

export async function deleteTemplate(id) {
  await http.delete(`/api/templates/${id}`)
}

export async function getSettings() {
  const { data } = await http.get('/api/settings')
  return data.settings
}

export async function saveSettings(settings) {
  const { data } = await http.put('/api/settings', { settings })
  return data.settings
}

export async function getCurrentTask() {
  const { data } = await http.get('/api/current-task')
  return data.item
}

/** 首次配置向导完成 */
export async function completeSetup(form = {}) {
  const { data } = await http.post('/api/setup/complete', form)
  return data
}

/** 任务表单：在已有一级下添加二级分类 */
export async function addSecondaryCategory(primaryId, name) {
  const { data } = await http.post('/api/categories/secondary', {
    primary_id: primaryId,
    name,
  })
  return data
}

/** 历史记录：操作日志 + AI 报告列表 */
export async function fetchHistory({ days = 30, category = 'all' } = {}) {
  const { data } = await http.get('/api/history', {
    params: { days, category },
  })
  return data
}

export async function fetchAiReport(name) {
  const { data } = await http.get(`/api/history/ai/${encodeURIComponent(name)}`)
  return data
}

/** 关闭宿主窗口并回传结果（Qt WebEngine） */
export function closeHost(payload = {}) {
  const json = encodeURIComponent(JSON.stringify(payload || {}))
  window.location.href = `zentray://close?payload=${json}`
}

export function cancelHost() {
  closeHost({ cancelled: true })
}
