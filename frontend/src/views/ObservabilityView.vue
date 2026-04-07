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
    // Find the assistant message that contains the final_answer and show only messages before it
    const answerIndex = msgs.findIndex(
      m => m.role === 'assistant' && selectedTrace.value!.final_answer &&
           m.content && m.content.includes(selectedTrace.value!.final_answer)
    )
    // Show messages up to (and including) the user message before the answer
    if (answerIndex > 0) {
      // answerIndex is the assistant msg, so we show msgs[0] to msgs[answerIndex - 1]
      // which is the user question and all prior messages
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

function getTraceFeedback(sessionId: string): 'positive' | 'negative' | null {
  // Match first feedback for this session (most relevant is the assistant answer)
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

function refreshData() {
  loadTraces()
  loadFeedbacks()
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
              <div v-if="getTraceFeedback(trace.session_id)" class="trace-feedback" :class="getTraceFeedback(trace.session_id)">
                {{ getTraceFeedback(trace.session_id) === 'positive' ? '👍' : '👎' }}
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
                📥 导出 JSON
              </button>
            </div>
          </div>

          <div class="detail-section">
            <h4>📝 用户问题</h4>
            <p class="question-text">{{ selectedTrace.question }}</p>
          </div>

          <div class="detail-section">
            <h4>💬 AI 回答</h4>
            <p class="answer-text">{{ selectedTrace.final_answer || '（回答生成中或出错）' }}</p>
          </div>

          <div class="detail-stats">
            <div class="stat-item">
              <span class="stat-label">总耗时</span>
              <span class="stat-value">{{ formatDuration(selectedTrace.total_time_ms) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">执行步骤</span>
              <span class="stat-value">{{ selectedTrace.steps.length }} 步</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">创建时间</span>
              <span class="stat-value">{{ formatDate(selectedTrace.created_at) }}</span>
            </div>
          </div>

          <div class="detail-section">
            <h4>🔄 执行步骤</h4>
            <div class="steps-timeline">
              <div v-for="step in selectedTrace.steps" :key="step.id" class="step-node">
                <div class="step-marker">
                  <span class="step-num">{{ step.step_index + 1 }}</span>
                </div>
                <div class="step-card">
                  <div class="step-header">
                    <span class="step-type" :class="step.step_type">
                      {{ step.step_type }}
                    </span>
                    <span v-if="step.tool_name" class="step-tool">🔧 {{ step.tool_name }}</span>
                    <span class="step-duration">{{ formatDuration(step.time_ms) }}</span>
                  </div>
                  <div v-if="step.input_prompt" class="step-io">
                    <span class="io-label">输入:</span>
                    <pre>{{ step.input_prompt }}</pre>
                  </div>
                  <div v-if="step.output_result" class="step-io">
                    <span class="io-label">输出:</span>
                    <pre>{{ step.output_result }}</pre>
                  </div>
                </div>
              </div>
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
              <button class="btn-export-small" @click="exportContextJson">📥 导出 JSON</button>
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

.trace-feedback {
  font-size: 16px;
  flex-shrink: 0;
}

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

.detail-actions {
  display: flex;
  gap: var(--spacing-2);
}

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

.detail-section {
  margin-bottom: var(--spacing-5);
}

.detail-section h4 {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.question-text {
  font-size: var(--font-size-sm);
  color: var(--color-text);
  margin: 0;
  line-height: var(--line-height-relaxed);
  background: var(--color-primary-bg);
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.answer-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: var(--line-height-relaxed);
  white-space: pre-wrap;
  max-height: 160px;
  overflow-y: auto;
  background: var(--color-bg-hover);
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-5);
}

.stat-item {
  background: var(--color-bg-hover);
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-item .stat-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-bottom: 2px;
}

.stat-item .stat-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

/* Steps Timeline */
.steps-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.step-node {
  display: flex;
  gap: var(--spacing-3);
}

.step-marker {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-num {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-inverse);
}

.step-card {
  flex: 1;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-3) var(--spacing-4);
  box-shadow: var(--shadow-sm);
}

.step-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.step-type {
  font-size: var(--font-size-xs);
  padding: 2px var(--spacing-2);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.step-type.tool_call { background: var(--color-warning-bg); color: var(--color-warning); }

.step-tool { font-size: var(--font-size-xs); color: var(--color-text-secondary); font-weight: var(--font-weight-medium); }

.step-duration { margin-left: auto; font-size: var(--font-size-xs); color: var(--color-text-muted); }

.step-io { margin-top: var(--spacing-2); }

.io-label { font-size: var(--font-size-xs); color: var(--color-text-secondary); font-weight: var(--font-weight-semibold); }

.step-io pre {
  margin: var(--spacing-1) 0 0;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-bg-hover);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 80px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  line-height: var(--line-height-normal);
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
