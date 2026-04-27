<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getTraces, getTraceDetail, exportTrace, getFeedbacks, type Trace, type TraceDetail, type FeedbackStatistics, type Feedback } from '../api/admin'
import { getMessages } from '../api/chat'

// Traces state
const traces = ref<Trace[]>([])
const tracesLoading = ref(false)
const tracesPage = ref(1)
const tracesTotal = ref(0)
const tracesPageSize = 20

// Trace detail state
const selectedTrace = ref<TraceDetail | null>(null)
const traceDetailLoading = ref(false)

// Feedbacks state (used for matching with traces)
const feedbacks = ref<Feedback[]>([])
const feedbacksStats = ref<FeedbackStatistics>({ positive_count: 0, negative_count: 0, total_count: 0 })

// Context modal
const showContextModal = ref(false)
const contextMessages = ref<any[]>([])
const contextLoading = ref(false)

async function loadTraces() {
  tracesLoading.value = true
  try {
    const res = await getTraces(tracesPage.value, tracesPageSize)
    traces.value = res.items
    tracesTotal.value = res.total
  } catch (err) {
    console.error('Failed to load traces:', err)
  } finally {
    tracesLoading.value = false
  }
}

async function loadTraceDetail(traceId: string) {
  traceDetailLoading.value = true
  try {
    selectedTrace.value = await getTraceDetail(traceId)
  } catch (err) {
    console.error('Failed to load trace detail:', err)
  } finally {
    traceDetailLoading.value = false
  }
}

async function loadFeedbacks() {
  try {
    const res = await getFeedbacks(1, 1000)
    feedbacksStats.value = res.statistics
    feedbacks.value = res.items
  } catch (err) {
    console.error('Failed to load feedbacks:', err)
  }
}

async function handleExportTrace(traceId: string) {
  try {
    await exportTrace(traceId)
  } catch (err) {
    console.error('Failed to export trace:', err)
  }
}

async function openContextModal() {
  if (!selectedTrace.value) return
  showContextModal.value = true
  contextLoading.value = true
  contextMessages.value = []
  try {
    const msgs = await getMessages(selectedTrace.value.session_id)
    const answerIndex = msgs.findIndex(
      m => m.role === 'assistant' && selectedTrace.value!.final_answer &&
           m.content && m.content.includes(selectedTrace.value!.final_answer)
    )
    if (answerIndex > 0) {
      contextMessages.value = msgs.slice(0, answerIndex)
    } else {
      contextMessages.value = msgs
    }
  } catch (err) {
    console.error('Failed to load context:', err)
  } finally {
    contextLoading.value = false
  }
}

function closeContextModal() {
  showContextModal.value = false
  contextMessages.value = []
}

function formatDate(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN')
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  return `${(ms / 60000).toFixed(2)}min`
}

function getTraceFeedback(sessionId: string, messageIndex?: number): 'positive' | 'negative' | null {
  if (messageIndex !== undefined) {
    const fb = feedbacks.value.find(f => f.session_id === sessionId && f.message_index === messageIndex)
    return fb ? (fb.feedback_type as 'positive' | 'negative') : null
  }
  const fb = feedbacks.value.find(f => f.session_id === sessionId)
  return fb ? (fb.feedback_type as 'positive' | 'negative') : null
}

function exportContextJson() {
  if (!selectedTrace.value || contextMessages.value.length === 0) return
  const data = JSON.stringify({
    session_id: selectedTrace.value.session_id,
    trace_id: selectedTrace.value.id,
    messages: contextMessages.value,
  }, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `context-${selectedTrace.value.id.slice(0, 8)}.json`
  link.click()
  URL.revokeObjectURL(url)
}

const tracesTotalPages = computed(() => Math.ceil(tracesTotal.value / tracesPageSize))

// Statistics
const avgTraceTime = computed(() => {
  if (traces.value.length === 0) return 0
  const total = traces.value.reduce((sum, t) => sum + t.total_time_ms, 0)
  return total / traces.value.length
})

const positiveRate = computed(() => {
  if (feedbacksStats.value.total_count === 0) return 0
  return (feedbacksStats.value.positive_count / feedbacksStats.value.total_count) * 100
})

const traceAttachments = computed(() => {
  if (!selectedTrace.value?.attachments_json) return null
  try {
    return JSON.parse(selectedTrace.value.attachments_json)
  } catch {
    return null
  }
})

function refreshData() {
  loadTraces()
  loadFeedbacks()
}

// Merge steps by node type for cleaner timeline display
interface MergedStep {
  id: string
  step_type: string
  label: string
  start_time_ms: number
  end_time_ms: number
  duration_ms: number
  isParallel: boolean
  children: any[]
}

const mergedTimeline = computed(() => {
  if (!selectedTrace.value?.steps || selectedTrace.value.steps.length === 0) return []

  const steps = selectedTrace.value.steps
  const totalTime = Math.max(...steps.map(s => s.time_ms))

  // Group steps by their main node type
  const nodeMap = new Map<string, MergedStep>()

  steps.forEach((step, idx) => {
    // Determine the main node type from step_type or tool_name
    let nodeType = step.step_type
    let label = step.step_type

    // Map tool_call to their parent node
    if (step.step_type === 'tool_call' && step.tool_name) {
      // Try to determine parent from context (previous steps)
      const prevStep = idx > 0 ? steps[idx - 1] : null
      if (prevStep && prevStep.step_type !== 'tool_call') {
        nodeType = prevStep.step_type
        label = step.tool_name
      } else {
        label = step.tool_name
      }
    } else if (step.step_type === 'intent_detection') {
      label = '意图分析'
    } else if (step.step_type.includes('supervisor')) {
      label = '协调决策'
    } else if (step.step_type === 'decide') {
      label = '路由决策'
    } else if (step.step_type === 'aggregate') {
      label = '结果汇总'
    } else if (step.step_type.includes('search')) {
      label = '知识检索'
    } else if (step.step_type.includes('jira')) {
      label = 'Jira查询'
    } else if (step.step_type.includes('translate')) {
      label = '翻译'
    } else if (step.step_type.includes('log')) {
      label = '日志分析'
    } else if (step.step_type.includes('summarize')) {
      label = '摘要'
    }

    // Calculate actual start and end times
    const startMs = step.start_time_ms
    const endMs = step.time_ms
    const durationMs = step.duration_ms || (endMs - startMs)

    // Check if parallel to previous (overlapping time)
    const prevStep = idx > 0 ? steps[idx - 1] : null
    const isParallel = prevStep ? startMs < prevStep.time_ms : false

    // Use step_index as part of key to avoid overwriting
    const key = `${nodeType}_${step.step_index}`

    if (!nodeMap.has(key)) {
      nodeMap.set(key, {
        id: key,
        step_type: nodeType,
        label: label,
        start_time_ms: startMs,
        end_time_ms: endMs,
        duration_ms: durationMs,
        isParallel: isParallel,
        children: [step]
      })
    } else {
      // Merge: extend time range if needed
      const existing = nodeMap.get(key)!
      existing.start_time_ms = Math.min(existing.start_time_ms, startMs)
      existing.end_time_ms = Math.max(existing.end_time_ms, endMs)
      existing.duration_ms = existing.end_time_ms - existing.start_time_ms
      existing.children.push(step)
    }
  })

  // Sort by start time
  const merged = Array.from(nodeMap.values()).sort((a, b) => a.start_time_ms - b.start_time_ms)

  // Recalculate parallelism after merging
  return merged.map((step, idx) => ({
    ...step,
    isParallel: idx > 0 && step.start_time_ms < merged[idx - 1].end_time_ms
  }))
})

const totalTime = computed(() => {
  if (!selectedTrace.value?.steps.length) return 0
  return Math.max(...selectedTrace.value.steps.map(s => s.time_ms))
})

const timelineMarkers = computed(() => {
  if (!totalTime.value) return []
  const markers = []
  const step = totalTime.value / 4
  for (let i = 0; i <= 4; i++) {
    const ms = step * i
    markers.push({
      pct: (ms / totalTime.value) * 100,
      label: formatDuration(ms)
    })
  }
  return markers
})

function getStepColor(stepType: string): string {
  if (stepType.includes('intent')) return '#ec4899'      // pink - intent detection
  if (stepType.includes('supervisor') || stepType.includes('decide')) return '#6366f1'  // indigo - supervisor
  if (stepType.includes('search')) return '#10b981'       // emerald - search
  if (stepType.includes('jira')) return '#f59e0b'        // amber - jira
  if (stepType.includes('translate')) return '#8b5cf6'   // violet - translate
  if (stepType.includes('log')) return '#06b6d4'         // cyan - log
  if (stepType.includes('summarize')) return '#14b8a6'   // teal - summarize
  if (stepType.includes('aggregate')) return '#f43f5e'   // rose - aggregate
  return '#64748b'                                          // slate - default
}

onMounted(() => {
  loadTraces()
  loadFeedbacks()
})
</script>

<template>
  <div class="observability-page">
    <!-- Compact header: stat strip + refresh -->
    <div class="page-header">
      <div class="stat-strip">
        <div class="strip-item">
          <span class="strip-num">{{ tracesTotal }}</span>
          <span class="strip-label">追踪记录</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-num">{{ avgTraceTime > 0 ? formatDuration(avgTraceTime) : '—' }}</span>
          <span class="strip-label">平均耗时</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-num good">{{ feedbacksStats.positive_count }}</span>
          <span class="strip-label">👍 点赞</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-num bad">{{ feedbacksStats.negative_count }}</span>
          <span class="strip-label">👎 点踩</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-num">{{ positiveRate > 0 ? positiveRate.toFixed(1) + '%' : '—' }}</span>
          <span class="strip-label">好评率</span>
        </div>
      </div>
      <button class="btn-refresh" @click="refreshData">
        🔄 刷新
      </button>
    </div>

    <!-- Main content: traces list + detail -->
    <div class="main-layout">
      <!-- Left: Traces List -->
      <div class="list-panel">
        <div class="panel-header">
          <h3>追踪记录</h3>
          <span class="count-badge">{{ tracesTotal }} 条</span>
        </div>

        <div v-if="tracesLoading" class="loading-state">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>
        <div v-else-if="traces.length === 0" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无追踪数据</p>
          <p class="empty-hint">开始对话后，执行轨迹将显示在这里</p>
        </div>
        <div v-else class="traces-list">
          <div
            v-for="trace in traces"
            :key="trace.id"
            :class="['trace-card', { selected: selectedTrace?.id === trace.id }]"
            @click="loadTraceDetail(trace.id)"
          >
            <div class="trace-top">
              <div class="trace-question">{{ trace.question }}</div>
              <div v-if="getTraceFeedback(trace.session_id, trace.message_index)" class="trace-feedback" :class="getTraceFeedback(trace.session_id, trace.message_index)">
                {{ getTraceFeedback(trace.session_id, trace.message_index) === 'positive' ? '👍' : '👎' }}
              </div>
            </div>
            <div class="trace-info">
              <span class="info-item">
                <span class="info-icon">🔧</span>
                {{ trace.steps_count }} 步骤
              </span>
              <span class="info-item">
                <span class="info-icon">⏱️</span>
                {{ formatDuration(trace.total_time_ms) }}
              </span>
              <span class="trace-time">{{ formatDate(trace.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="tracesTotalPages > 1" class="pagination">
          <button :disabled="tracesPage === 1" @click="tracesPage--; loadTraces()">‹ 上一页</button>
          <span class="page-info">{{ tracesPage }} / {{ tracesTotalPages }}</span>
          <button :disabled="tracesPage >= tracesTotalPages" @click="tracesPage++; loadTraces()">下一页 ›</button>
        </div>
      </div>

      <!-- Right: Trace Detail -->
      <div class="detail-panel">
        <div v-if="!selectedTrace" class="no-selection">
          <div class="no-selection-icon">👈</div>
          <p>选择左侧追踪记录查看详情</p>
        </div>
        <div v-else-if="traceDetailLoading" class="loading-state">
          <div class="spinner"></div>
          <span>加载详情...</span>
        </div>
        <div v-else class="detail-content">
          <div class="detail-header">
            <h3>追踪详情</h3>
            <div class="detail-actions">
              <button class="btn-action" @click="openContextModal">
                💬 上下文
              </button>
              <button class="btn-export" @click="handleExportTrace(selectedTrace.id)">
                📥 导出
              </button>
            </div>
          </div>

          <!-- Question & Answer -->
          <div class="qa-section">
            <div class="qa-item">
              <div class="qa-label">🙋 用户问题</div>
              <div class="qa-content question">{{ selectedTrace.question }}</div>
            </div>
            <div class="qa-item">
              <div class="qa-label">🤖 AI 回答</div>
              <div class="qa-content answer">{{ selectedTrace.final_answer || '（无）' }}</div>
            </div>
          </div>

          <!-- Attachments -->
          <div v-if="traceAttachments" class="attachments-section">
            <div class="section-label">📎 附件</div>
            <div class="attachments-list">
              <span v-for="att in traceAttachments" :key="att.id" class="file-tag">
                {{ att.filename }} ({{ (att.size / 1024).toFixed(1) }}KB)
              </span>
            </div>
          </div>

          <!-- Stats -->
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">⏱️</div>
              <div class="stat-info">
                <div class="stat-value">{{ formatDuration(selectedTrace.total_time_ms) }}</div>
                <div class="stat-label">总耗时</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">🔧</div>
              <div class="stat-info">
                <div class="stat-value">{{ selectedTrace.steps.length }}</div>
                <div class="stat-label">执行步骤</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">📅</div>
              <div class="stat-info">
                <div class="stat-value">{{ formatDate(selectedTrace.created_at) }}</div>
                <div class="stat-label">创建时间</div>
              </div>
            </div>
          </div>

          <!-- Timeline -->
          <div class="timeline-section">
            <div class="section-label">📊 执行时间轴</div>

            <div v-if="mergedTimeline.length" class="timeline-container">
              <!-- Timeline header with markers -->
              <div class="timeline-header">
                <div
                  v-for="marker in timelineMarkers"
                  :key="marker.label"
                  class="timeline-marker"
                  :style="{ left: marker.pct + '%' }"
                >
                  <div class="marker-line"></div>
                  <div class="marker-label">{{ marker.label }}</div>
                </div>
              </div>

              <!-- Timeline rows -->
              <div class="timeline-rows">
                <div
                  v-for="(step, idx) in mergedTimeline"
                  :key="step.id"
                  class="timeline-row"
                >
                  <div class="row-label">
                    <span class="step-index">{{ idx + 1 }}</span>
                    <span class="step-name" :style="{ color: getStepColor(step.step_type) }">
                      {{ step.label }}
                    </span>
                    <span v-if="step.isParallel" class="parallel-tag">并行</span>
                  </div>
                  <div class="row-bar-container">
                    <div
                      class="timeline-bar"
                      :style="{
                        left: (step.start_time_ms / totalTime * 100) + '%',
                        width: Math.max((step.duration_ms / totalTime * 100), 2) + '%',
                        backgroundColor: getStepColor(step.step_type)
                      }"
                      :title="`${step.label}: ${formatDuration(step.duration_ms)}`"
                    >
                      <span class="bar-duration">{{ formatDuration(step.duration_ms) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step details accordion -->
            <div class="steps-accordion">
              <details
                v-for="(step, idx) in selectedTrace.steps"
                :key="step.id"
                class="step-detail"
              >
                <summary class="step-summary">
                  <span class="step-num">{{ idx + 1 }}</span>
                  <span class="step-type" :style="{ backgroundColor: getStepColor(step.step_type) + '20', color: getStepColor(step.step_type) }">
                    {{ step.step_type }}
                  </span>
                  <span v-if="step.tool_name" class="step-tool">{{ step.tool_name }}</span>
                  <span class="step-dur">{{ formatDuration(step.duration_ms || (step.time_ms - step.start_time_ms)) }}</span>
                  <span class="expand-icon">▶</span>
                </summary>
                <div class="step-body">
                  <div v-if="step.input_prompt" class="step-io">
                    <div class="io-label">📥 输入</div>
                    <pre class="io-content">{{ step.input_prompt }}</pre>
                  </div>
                  <div v-if="step.output_result" class="step-io">
                    <div class="io-label">📤 输出</div>
                    <pre class="io-content">{{ step.output_result }}</pre>
                  </div>
                  <div class="step-meta">
                    <span>开始: {{ formatDuration(step.start_time_ms) }}</span>
                    <span>结束: {{ formatDuration(step.time_ms) }}</span>
                  </div>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Modal -->
    <Teleport to="body">
      <div v-if="showContextModal" class="modal-overlay" @click="closeContextModal">
        <div class="modal context-modal" @click.stop>
          <div class="modal-header">
            <h3>💬 对话上下文</h3>
            <div class="modal-header-actions">
              <button class="btn-export-small" @click="exportContextJson">📥 导出</button>
              <button class="btn-close" @click="closeContextModal">&times;</button>
            </div>
          </div>
          <div class="modal-body">
            <div v-if="contextLoading" class="loading-state">
              <div class="spinner"></div>
              <span>加载中...</span>
            </div>
            <div v-else-if="contextMessages.length === 0" class="empty-state">
              <p>暂无上下文数据</p>
            </div>
            <div v-else class="context-list">
              <div
                v-for="(msg, i) in contextMessages"
                :key="i"
                :class="['context-msg', msg.role]"
              >
                <div class="context-role">{{ msg.role === 'user' ? '👤 用户' : '🤖 AI' }}</div>
                <div class="context-content">{{ msg.content || '（无内容）' }}</div>
                <div v-if="msg.role === 'user' && msg.attachments?.length" class="context-attachments">
                  <span v-for="att in msg.attachments" :key="att.id" class="file-tag">
                    {{ att.filename }} ({{ (att.size / 1024).toFixed(1) }}KB)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.observability-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-4) var(--spacing-5);
  background: var(--color-bg);
  overflow: hidden;
  gap: var(--spacing-4);
}

/* Compact Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-3) var(--spacing-5);
  gap: var(--spacing-4);
}

.stat-strip {
  display: flex;
  align-items: center;
  gap: var(--spacing-5);
  flex: 1;
}

.strip-item {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-2);
}

.strip-num {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.strip-num.good { color: var(--color-success); }
.strip-num.bad { color: var(--color-error); }

.strip-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.strip-divider {
  width: 1px;
  height: 24px;
  background: var(--color-border);
}

.btn-refresh {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.btn-refresh:hover {
  background: var(--color-bg);
  border-color: var(--color-border-dark);
}

/* Main Layout */
.main-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: var(--spacing-4);
  min-height: 0;
}

/* Panel Styles */
.list-panel, .detail-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
}

.panel-header {
  padding: var(--spacing-3) var(--spacing-5);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg);
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.count-badge {
  background: var(--color-bg-hover);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

/* Loading & Empty States */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-15) var(--spacing-5);
  color: var(--color-text-secondary);
  gap: var(--spacing-3);
  flex: 1;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: var(--spacing-15) var(--spacing-5);
  color: var(--color-text-secondary);
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.empty-icon { font-size: 40px; margin-bottom: var(--spacing-3); }
.empty-state p { margin: 0; font-size: var(--font-size-sm); }
.empty-hint { font-size: var(--font-size-xs); color: var(--color-text-muted) !important; margin-top: var(--spacing-2) !important; }

/* Traces List */
.traces-list {
  flex: 1;
  overflow-y: auto;
}

.trace-card {
  padding: var(--spacing-3) var(--spacing-5);
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.trace-card:hover { background: var(--color-bg-hover); }
.trace-card.selected { background: var(--color-primary-bg); border-left: 3px solid var(--color-primary); }

.trace-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.trace-question {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
  line-height: var(--line-height-normal);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-feedback { font-size: 16px; flex-shrink: 0; }

.trace-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.info-icon { font-size: var(--font-size-xs); }

.trace-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-left: auto;
}

/* Detail Panel */
.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-20) var(--spacing-5);
  color: var(--color-text-muted);
  flex: 1;
}

.no-selection-icon { font-size: 48px; margin-bottom: var(--spacing-3); }

.detail-content {
  padding: var(--spacing-5);
  flex: 1;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-5);
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--color-border);
}

.detail-header h3 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.detail-actions { display: flex; gap: var(--spacing-2); }

.btn-action {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  cursor: pointer;
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
}

.btn-action:hover {
  background: var(--color-bg);
  border-color: var(--color-border-dark);
  color: var(--color-text);
}

.btn-export {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  cursor: pointer;
  font-weight: var(--font-weight-medium);
  transition: background var(--transition-fast);
}

.btn-export:hover { background: var(--color-primary-dark); }

/* QA Section */
.qa-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.qa-item {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--spacing-3) var(--spacing-4);
}

.qa-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.qa-content {
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

.qa-content.question {
  color: var(--color-text);
  background: var(--color-primary-bg);
  border-left: 3px solid var(--color-primary);
  padding-left: var(--spacing-3);
}

.qa-content.answer {
  color: var(--color-text-secondary);
}

/* Attachments */
.attachments-section {
  margin-bottom: var(--spacing-4);
}

.section-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.attachments-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.file-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-light);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-5);
}

.stat-card {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.stat-icon { font-size: 24px; }

.stat-info { flex: 1; }

.stat-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

/* Timeline Section */
.timeline-section {
  margin-bottom: var(--spacing-4);
}

.timeline-container {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
  margin-bottom: var(--spacing-3);
}

.timeline-header {
  position: relative;
  height: 24px;
  margin-bottom: var(--spacing-3);
  border-bottom: 1px solid var(--color-border);
}

.timeline-marker {
  position: absolute;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.marker-line {
  width: 1px;
  height: 6px;
  background: var(--color-border);
}

.marker-label {
  font-size: 10px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.timeline-rows {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.timeline-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.row-label {
  width: 100px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.step-index {
  width: 18px;
  height: 18px;
  background: var(--color-bg-hover);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.step-name {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.parallel-tag {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 3px;
  background: #f59e0b;
  color: white;
  flex-shrink: 0;
}

.row-bar-container {
  flex: 1;
  position: relative;
  height: 28px;
  background: var(--color-bg-hover);
  border-radius: var(--radius-sm);
}

.timeline-bar {
  position: absolute;
  top: 4px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  overflow: hidden;
  transition: width 0.3s ease;
}

.bar-duration {
  font-size: 10px;
  color: white;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  padding: 0 4px;
}

/* Steps Accordion */
.steps-accordion {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.step-detail {
  background: var(--color-bg-card);
}

.step-detail:not(:last-child) {
  border-bottom: 1px solid var(--color-border);
}

.step-summary {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  cursor: pointer;
  list-style: none;
  transition: background var(--transition-fast);
}

.step-summary::-webkit-details-marker { display: none; }
.step-summary:hover { background: var(--color-bg-hover); }

.step-summary .step-num {
  width: 20px;
  height: 20px;
  background: var(--color-bg-hover);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.step-type {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
  flex-shrink: 0;
}

.step-tool {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-dur {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.expand-icon {
  font-size: 10px;
  color: var(--color-text-muted);
  transition: transform var(--transition-fast);
  flex-shrink: 0;
}

.step-detail[open] .expand-icon {
  transform: rotate(90deg);
}

.step-body {
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
}

.step-io {
  margin-bottom: var(--spacing-2);
}

.step-io:last-of-type {
  margin-bottom: 0;
}

.io-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-1);
}

.io-content {
  margin: 0;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-bg-hover);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 100px;
  overflow-y: auto;
  line-height: var(--line-height-normal);
}

.step-meta {
  display: flex;
  gap: var(--spacing-4);
  margin-top: var(--spacing-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

/* Context Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.context-modal {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  width: 700px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.btn-export-small {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  cursor: pointer;
  font-weight: var(--font-weight-medium);
}

.btn-close {
  background: transparent;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.btn-close:hover { color: var(--color-text); }

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
}

.context-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.context-msg {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.context-msg.user { background: var(--color-primary-bg); border-color: var(--color-primary-light); }
.context-msg.assistant { background: var(--color-bg-hover); }

.context-role {
  padding: var(--spacing-2) var(--spacing-4);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.context-content {
  padding: var(--spacing-3) var(--spacing-4);
  font-size: var(--font-size-sm);
  color: var(--color-text);
  white-space: pre-wrap;
  line-height: var(--line-height-relaxed);
  max-height: 200px;
  overflow-y: auto;
}

.context-attachments {
  padding: var(--spacing-2) var(--spacing-4);
  background: rgba(255, 255, 255, 0.3);
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.context-attachments .file-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  background: rgba(255, 255, 255, 0.5);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-3);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.pagination button {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  padding: var(--spacing-1) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
}

.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination button:not(:disabled):hover { background: var(--color-bg-hover); border-color: var(--color-border-dark); }

.page-info {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}
</style>
