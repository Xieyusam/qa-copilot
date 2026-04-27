<template>
  <div class="logs-view">
    <div class="header">
      <h1>日志查看</h1>
      <div class="filters">
        <select v-model="levelFilter" class="filter-select">
          <option value="">全部级别</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <input
          v-model="traceIdFilter"
          type="text"
          placeholder="输入 trace_id 搜索"
          class="filter-input"
        />
        <button @click="fetchLogs" class="btn-primary">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <table v-else class="logs-table">
      <thead>
        <tr>
          <th>时间</th>
          <th>级别</th>
          <th>Trace ID</th>
          <th>模块</th>
          <th>函数</th>
          <th>消息</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(log, index) in logs" :key="index" :class="'level-' + log.level">
          <td class="time">{{ formatTime(log.time) }}</td>
          <td>
            <span :class="'badge badge-' + log.level.toLowerCase()">
              {{ log.level }}
            </span>
          </td>
          <td class="trace-id">
            <a @click.prevent="searchByTraceId(log.trace_id)" href="#">
              {{ log.trace_id }}
            </a>
          </td>
          <td class="module">{{ log.name }}</td>
          <td class="function">{{ log.function }}</td>
          <td class="message">{{ log.message }}</td>
        </tr>
        <tr v-if="logs.length === 0">
          <td colspan="6" class="no-data">暂无日志数据</td>
        </tr>
      </tbody>
    </table>

    <div class="pagination">
      <span class="total">共 {{ logs.length }} 条日志</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { request } from '../api/request'

interface LogEntry {
  time: string
  level: string
  name: string
  function: string
  line: number
  trace_id: string
  message: string
}

const logs = ref<LogEntry[]>([])
const levelFilter = ref('')
const traceIdFilter = ref('')
const loading = ref(false)
const error = ref('')
const limit = 100

const API_BASE = '/api/admin/logs'

const fetchLogs = async () => {
  loading.value = true
  error.value = ''

  try {
    const params: Record<string, string | number> = { limit }
    if (levelFilter.value) {
      params.level = levelFilter.value
    }
    if (traceIdFilter.value) {
      params.trace_id = traceIdFilter.value
    }

    const response = await request(API_BASE + '?' + new URLSearchParams(params as Record<string, string>))
    const data = await response.json()
    logs.value = data
  } catch (err: any) {
    error.value = '获取日志失败'
    console.error('Failed to fetch logs:', err)
  } finally {
    loading.value = false
  }
}

const searchByTraceId = (traceId: string) => {
  traceIdFilter.value = traceId
  fetchLogs()
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return timeStr
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.logs-view {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.filters {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-select,
.filter-input {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.filter-input {
  width: 240px;
}

.btn-primary {
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-secondary {
  padding: 8px 16px;
  background-color: #6b7280;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #4b5563;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #6b7280;
}

.error {
  padding: 12px;
  background-color: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  color: #dc2626;
  margin-bottom: 16px;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.logs-table th,
.logs-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.logs-table th {
  background-color: #f9fafb;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  color: #6b7280;
}

.logs-table td {
  font-size: 13px;
  color: #374151;
}

.logs-table tr:hover {
  background-color: #f9fafb;
}

.logs-table tr.level-ERROR,
.logs-table tr.level-CRITICAL {
  background-color: #fef2f2;
}

.logs-table tr.level-WARNING {
  background-color: #fffbeb;
}

.time {
  white-space: nowrap;
  color: #6b7280;
  font-family: monospace;
  font-size: 12px;
}

.trace-id {
  font-family: monospace;
  font-size: 11px;
}

.trace-id a {
  color: #3b82f6;
  text-decoration: none;
  cursor: pointer;
}

.trace-id a:hover {
  text-decoration: underline;
}

.module {
  font-family: monospace;
  font-size: 12px;
  color: #8b5cf6;
}

.function {
  font-family: monospace;
  font-size: 12px;
  color: #059669;
}

.message {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-debug {
  background-color: #f3f4f6;
  color: #6b7280;
}

.badge-info {
  background-color: #dbeafe;
  color: #1d4ed8;
}

.badge-warning {
  background-color: #fef3c7;
  color: #b45309;
}

.badge-error {
  background-color: #fee2e2;
  color: #dc2626;
}

.badge-critical {
  background-color: #fee2e2;
  color: #991b1b;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #6b7280;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.total {
  color: #6b7280;
  font-size: 14px;
}
</style>
