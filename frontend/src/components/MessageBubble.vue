<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { Message } from '../types'
import { submitFeedback } from '../api/chat'

const props = defineProps<{
  message: Message,
  index?: number,
  sessionId?: string,
  onRegenerate?: (index: number) => void
}>()

const rawContent = ref('')
const showSources = ref(false)
const showToast = ref(false)
const toastMessage = ref('')
// 初始化反馈状态：从消息中读取已提交的反馈（只有 assistant 消息才有反馈）
const feedbackType = ref<'positive' | 'negative' | null>(
  props.message.role === 'assistant' ? (props.message.feedback_type ?? null) : null
)
const feedbackLoading = ref(false)

// 流式渲染性能优化：使用 requestAnimationFrame 调度渲染
let rafId: number | null = null
let lastRenderedLength = 0
let isStreaming = true

// 检测流式是否结束（内容不再变化超过 500ms）
let streamEndTimer: ReturnType<typeof setTimeout> | null = null
function detectStreamEnd() {
  if (streamEndTimer) clearTimeout(streamEndTimer)
  streamEndTimer = setTimeout(() => {
    isStreaming = false
    // 流式结束后强制完整渲染一次
    rawContent.value = props.message.content
    lastRenderedLength = props.message.content.length
  }, 500)
}

// 调度渲染：使用 RAF 与浏览器刷新率同步
function scheduleRender(content: string) {
  if (rafId) return // 已有待处理的渲染任务

  rafId = requestAnimationFrame(() => {
    rafId = null
    // 流式过程中只更新长度变化超过阈值时才重新渲染
    const newLength = content.length
    const delta = newLength - lastRenderedLength

    if (isStreaming) {
      // 流式中：增量超过 50 字符才更新，减少渲染次数
      if (delta >= 50 || delta < 0) {
        rawContent.value = content
        lastRenderedLength = newLength
      }
      detectStreamEnd()
    } else {
      // 流式结束：直接更新
      rawContent.value = content
      lastRenderedLength = newLength
    }
  })
}

// 监听内容变化
watch(() => props.message.content, (newContent) => {
  // 重置流式状态（新消息开始）
  if (newContent.length < lastRenderedLength) {
    isStreaming = true
    lastRenderedLength = 0
  }
  scheduleRender(newContent)
}, { immediate: true })

// 组件销毁时清理
onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (streamEndTimer) clearTimeout(streamEndTimer)
})

function displayToast(msg: string) {
  toastMessage.value = msg
  showToast.value = true
  setTimeout(() => {
    showToast.value = false
  }, 2000)
}

async function copyContent(content: string) {
  if (!content) {
    displayToast('暂无可复制的片段内容')
    return
  }
  try {
    await navigator.clipboard.writeText(content)
    displayToast('片段内容已复制！')
  } catch (err) {
    console.error('Failed to copy text: ', err)
    displayToast('复制失败')
  }
}

async function copyMarkdown() {
  const content = props.message.content
  if (!content) {
    displayToast('暂无可复制的内容')
    return
  }
  try {
    await navigator.clipboard.writeText(content)
    displayToast('已复制！')
  } catch (err) {
    console.error('Failed to copy: ', err)
    displayToast('复制失败')
  }
}

async function downloadOriginal(docId: string, filename: string) {
  try {
    const response = await fetch(
      `/api/documents/${encodeURIComponent(docId)}/download?filename=${encodeURIComponent(filename)}`
    )
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.style.display = 'none'
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Download failed:', error)
    displayToast('下载原文失败，请重试')
  }
}

const renderedContent = computed(() => {
  if (props.message.role !== 'assistant') return ''
  const raw = rawContent.value
  if (!raw) return ''

  // 使用 marked 的异步解析选项（同步更快）
  const parsed = marked.parse(raw, {
    breaks: true,      // 支持 GFM 换行
    gfm: true,         // GitHub Flavored Markdown
  }) as string

  return DOMPurify.sanitize(parsed, {
    // 仅允许安全的 HTML 标签
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr'],
    ALLOWED_ATTR: ['href', 'title', 'class'],
  })
})

function handleRegenerate() {
  if (props.onRegenerate && props.index !== undefined) {
    props.onRegenerate(props.index)
  }
}

function getScoreClass(score: number): string {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.5) return 'score-med'
  return 'score-low'
}

async function handleFeedback(type: 'positive' | 'negative') {
  if (!props.sessionId || props.index === undefined) return
  feedbackLoading.value = true
  try {
    await submitFeedback(props.sessionId, props.index, type)
    feedbackType.value = type
    displayToast(type === 'positive' ? '感谢您的反馈！' : '感谢反馈，我们会改进！')
  } catch (err) {
    console.error('Failed to submit feedback:', err)
    displayToast('反馈提交失败')
  } finally {
    feedbackLoading.value = false
  }
}
</script>

<template>
  <div class="bubble-row" :class="message.role">
    <div class="bubble-wrapper">
      <div class="bubble" :class="message.role">
        <!-- user: plain text; assistant: rendered markdown -->
        <p v-if="message.role === 'user'" class="content">{{ message.content }}</p>
        <!-- 用户消息的附件标签 -->
        <div v-if="message.role === 'user' && message.attachments?.length" class="attachments">
          <span v-for="att in message.attachments" :key="att.id" class="file-tag">
            📎 {{ att.filename }} ({{ (att.size / 1024).toFixed(1) }}KB)
          </span>
        </div>
        <div
          v-else
          class="markdown-body"
          v-html="renderedContent"
        ></div>

        <!-- 查看溯源按钮 (只在回答结束并且有来源时显示) -->
        <div v-if="message.role === 'assistant' && message.sources?.length" class="source-toggle">
          <button class="btn-source" @click="showSources = true">
            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            查看溯源
          </button>
        </div>
      </div>
      <div v-if="message.role === 'assistant' && onRegenerate && !message.content.includes('未在知识库中找到')" class="actions">
        <!-- 复制内容按钮 -->
        <button class="action-btn" @click="copyMarkdown" title="复制内容">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <!-- 重新生成按钮 -->
        <button class="action-btn" @click="handleRegenerate" title="重新生成">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
        <!-- 反馈按钮 -->
        <button
          class="action-btn feedback-btn"
          :class="{ active: feedbackType === 'positive' }"
          @click="handleFeedback('positive')"
          :disabled="feedbackLoading"
          title="点赞"
        >
          👍
        </button>
        <button
          class="action-btn feedback-btn"
          :class="{ active: feedbackType === 'negative' }"
          @click="handleFeedback('negative')"
          :disabled="feedbackLoading"
          title="点踩"
        >
          👎
        </button>
      </div>
    </div>

    <!-- 溯源右侧抽屉 -->
    <Teleport to="body">
      <div v-if="showSources" class="drawer-overlay" @click="showSources = false">
        <div class="drawer" @click.stop>
          <div class="drawer-header">
            <h3>溯源片段 (Top {{ message.sources?.length }})</h3>
            <button class="btn-close" @click="showSources = false">&times;</button>
          </div>
          <div class="drawer-body">
            <div v-for="(src, i) in message.sources" :key="i" class="source-card">
              <div class="source-card-header">
                <span class="source-doc-name" :title="src.filename">{{ src.filename }}</span>
                <span v-if="src.similarityScore !== undefined" class="source-badge" :class="getScoreClass(src.similarityScore)">
                  {{ (src.similarityScore * 100).toFixed(1) }}%
                </span>
              </div>
              <div v-if="src.similarityScore !== undefined && src.similarityScore < 0.6" class="source-warning">
                <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                该片段相关性较低，回答可能不准确
              </div>
              <div class="source-card-content">
                {{ src.content || '（暂无片段内容，可能是历史记录未保存内容）' }}
              </div>
              <div class="source-card-actions">
                <button class="btn-action" @click="copyContent(src.content || '')">复制内容</button>
                <button class="btn-action" @click="downloadOriginal(src.docId, src.filename)">下载原文</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 自定义 Toast 提示 -->
    <Teleport to="body">
      <div v-if="showToast" class="toast-message">
        {{ toastMessage }}
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.bubble-row {
  display: flex;
  margin-bottom: var(--spacing-3);
}

.bubble-row.user { justify-content: flex-end; }
.bubble-row.assistant { justify-content: flex-start; }

.bubble {
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  /* 内联级别让宽度由内容自然撑开 */
  display: inline;
}

.bubble-wrapper {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  /* max-width 限制气泡最大宽度，长文本在此限制下自动换行 */
  max-width: 85%;
  /* width: fit-content 让 wrapper 宽度由 bubble 自然宽度决定 */
  width: fit-content;
}

.bubble.user {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-bottom-right-radius: 2px;
}

.bubble.assistant {
  background: var(--color-bg-hover);
  color: var(--color-text);
  border-bottom-left-radius: 2px;
}

.content {
  margin: 0;
  white-space: pre-wrap;
  word-break: normal;
  overflow-wrap: normal;
}

/* 用户消息附件标签 */
.attachments {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-top: var(--spacing-2);
}

.file-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  background: rgba(255, 255, 255, 0.15);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: inherit;
}

/* Markdown styles */
.markdown-body :deep(p) { margin: 0 0 var(--spacing-2); }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) { margin: var(--spacing-3) 0 var(--spacing-2); font-weight: var(--font-weight-semibold); }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { padding-left: var(--spacing-5); margin: var(--spacing-2) 0; }
.markdown-body :deep(li) { margin: var(--spacing-1) 0; }
.markdown-body :deep(code) {
  background: var(--color-bg-hover);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  font-family: 'Fira Code', monospace;
  font-size: var(--font-size-xs);
}
.markdown-body :deep(pre) {
  background: var(--color-bg-hover);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin: var(--spacing-2) 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--color-border);
  padding-left: var(--spacing-2);
  color: var(--color-text-secondary);
  margin: var(--spacing-2) 0;
}
.markdown-body :deep(a) { color: var(--color-primary); }
.markdown-body :deep(strong) { font-weight: var(--font-weight-semibold); }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: var(--spacing-2) 0; }
.markdown-body :deep(th),
.markdown-body :deep(td) { border: 1px solid var(--color-border); padding: var(--spacing-1) var(--spacing-2); }
.markdown-body :deep(th) { background: var(--color-bg-hover); }

.source-toggle {
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border);
}

.btn-source {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-source:hover {
  background: var(--color-bg-card);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* 抽屉样式 */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  animation: fadeIn var(--transition-normal);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.drawer {
  width: 640px;
  max-width: 95vw;
  background: var(--color-bg);
  height: 100vh;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.drawer-header {
  padding: var(--spacing-5) var(--spacing-6);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-header h3 {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--color-text);
}

.btn-close {
  background: transparent;
  border: none;
  font-size: var(--font-size-xl);
  line-height: 1;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color var(--transition-fast);
}
.btn-close:hover { color: var(--color-text); }

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.source-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  transition: box-shadow var(--transition-fast);
  flex-shrink: 0;
}

.source-card:hover {
  box-shadow: var(--shadow-md);
}

.source-card-header {
  padding: var(--spacing-4) var(--spacing-6);
  background: linear-gradient(to bottom, var(--color-bg), var(--color-bg-hover));
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.source-doc-name {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 320px;
}

.source-badge {
  font-size: var(--font-size-xs);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-medium);
}
.score-high { background: var(--color-success-bg); color: var(--color-success); }
.score-med { background: var(--color-warning-bg); color: var(--color-warning); }
.score-low { background: var(--color-error-bg); color: var(--color-error); }

.source-warning {
  padding: var(--spacing-3) var(--spacing-6);
  background: var(--color-warning-bg);
  color: var(--color-warning-dark);
  font-size: var(--font-size-xs);
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  border-bottom: 1px solid var(--color-warning);
  flex-shrink: 0;
}

.source-card-content {
  padding: var(--spacing-6);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  background: var(--color-bg-card);
  min-height: 80px;
  max-height: 300px;
  overflow-y: auto;
}

.source-card-actions {
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  display: flex;
  gap: var(--spacing-3);
  justify-content: flex-end;
  flex-shrink: 0;
}

.btn-action {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-weight: var(--font-weight-medium);
}

.btn-action:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-dark);
  color: var(--color-text);
}

/* 修复由于嵌套或父级样式导致的滚动条不出现问题 */
.drawer-body::-webkit-scrollbar,
.source-card-content::-webkit-scrollbar {
  width: 6px;
}
.drawer-body::-webkit-scrollbar-track,
.source-card-content::-webkit-scrollbar-track {
  background: transparent;
}
.drawer-body::-webkit-scrollbar-thumb,
.source-card-content::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}
.drawer-body::-webkit-scrollbar-thumb:hover,
.source-card-content::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-muted);
}

.toast-message {
  position: fixed;
  bottom: var(--spacing-6);
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: var(--color-text-inverse);
  padding: var(--spacing-2) var(--spacing-5);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  z-index: 9999;
  box-shadow: var(--shadow-md);
  animation: fadeUp var(--transition-normal) ease-out;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translate(-50%, 10px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}

.bubble-row.user .bubble-wrapper {
  flex-direction: row-reverse;
}

.actions {
  display: flex;
  opacity: 0;
  transition: opacity var(--transition-fast);
  padding-top: var(--spacing-1);
}

.bubble-wrapper:hover .actions {
  opacity: 1;
}

.action-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.feedback-btn.active {
  background: var(--color-primary-bg);
}

.feedback-btn.active:hover {
  background: var(--color-primary-bg);
}
</style>
