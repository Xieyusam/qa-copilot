<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'
import { uploadAttachment, type Attachment } from '../api/attachments'

const store = useChatStore()
const question = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const thinking = ref(false)
const attachments = ref<Attachment[]>([])  // 已上传的附件
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadError = ref('')

// 锚点模式：以用户消息的滚动位置为锚点，上下切换
const anchorActive = ref(false)
const anchorUserIndex = ref(-1) // -1=最新，0=倒数第1个用户消息，1=倒数第2个...

const displayMessages = computed(() => {
  return store.messages
})

function getUserMsgElements(): HTMLElement[] {
  if (!messagesEl.value) return []
  return Array.from(messagesEl.value.querySelectorAll<HTMLElement>('.bubble-row.user'))
}

function getUserMsgCount(): number {
  return getUserMsgElements().length
}

const currentAnchorLabel = computed(() => {
  if (!anchorActive.value) return ''
  const count = getUserMsgCount()
  if (count === 0) return ''
  // anchorUserIndex: -1=最新，0=倒数第1个(Qn)，1=倒数第2个(Qn-1)...
  const total = count
  if (anchorUserIndex.value === -1) return `Q${total}`
  const qNum = total - anchorUserIndex.value
  return `Q${qNum}`
})

function scrollToUserMsg(index: number) {
  const rows = getUserMsgElements()
  // index: 0=倒数第1个用户消息，1=倒数第2个...
  const actualIndex = rows.length - 1 - index
  if (actualIndex >= 0 && actualIndex < rows.length) {
    rows[actualIndex].scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function goAnchorUp() {
  const count = getUserMsgCount()
  if (count === 0) return

  if (!anchorActive.value) {
    anchorActive.value = true
    anchorUserIndex.value = -1 // 默认最新
    nextTick(() => {
      messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })
    })
    return
  }

  // 往上：-1->0(倒数第1), 0->1(倒数第2), ...
  if (anchorUserIndex.value === -1) {
    anchorUserIndex.value = 0
  } else {
    anchorUserIndex.value = Math.min(anchorUserIndex.value + 1, count - 1)
  }
  nextTick(() => scrollToUserMsg(anchorUserIndex.value))
}

function goAnchorDown() {
  const count = getUserMsgCount()
  if (count === 0) return

  if (!anchorActive.value) return

  // 往下：0(倒数第1)->-1(最新), -1->回到最新
  if (anchorUserIndex.value === -1 || anchorUserIndex.value === 0) {
    anchorActive.value = false
    anchorUserIndex.value = -1
    nextTick(() => {
      messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })
    })
    return
  }

  anchorUserIndex.value = Math.max(anchorUserIndex.value - 1, 0)
  nextTick(() => scrollToUserMsg(anchorUserIndex.value))
}

// 监听消息数量变化：切换会话加载新消息后，以及新消息发送后都自动滚动
watch(
  () => store.messages.length,
  (newLen, oldLen) => {
    if (newLen > (oldLen ?? 0)) {
      nextTick(() => scrollToBottom())
    }
  }
)

// 监听会话切换：切换后也自动滚动到底部
watch(
  () => store.currentSessionId,
  () => {
    // 使用 setTimeout + nextTick 确保 DOM 已渲染
    setTimeout(() => {
      nextTick(() => scrollToBottom())
    }, 50)
  }
)

// 默认话题引导
const suggestedTopics = [
  { icon: '📊', text: '查询 Jira 项目列表', query: '帮我查询当前 Jira 有哪些项目', fillOnly: false },
  { icon: '📝', text: '查询未解决问题数量', query: '帮我查询某个项目还有多少未解决的问题', fillOnly: false },
  { icon: '📅', text: '查询今日新增问题', query: '今天 Jira 所有项目新增了哪些问题？', fillOnly: false },
  { icon: '🔧', text: '日志错误分析', query: '请帮我分析以下日志错误并给出解决方案建议：\n', fillOnly: true },
]

function onTopicClick(topic: typeof suggestedTopics[0]) {
  if (store.streaming) return
  if (topic.fillOnly) {
    // 只填入输入框，等待用户补充内容
    question.value = topic.query
  } else {
    // 直接发送
    sendSuggested(topic.query)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

// 流式过程中，监听最后一条消息内容变化，实时滚动
watch(
  () => {
    const msgs = store.messages
    return msgs.length > 0 ? msgs[msgs.length - 1].content : ''
  },
  () => {
    if (store.streaming) scrollToBottom()
  },
)

// 消息数量变化时也滚动（新消息出现）
watch(() => store.messages.length, scrollToBottom)

// 监听 streaming 状态控制 thinking 显示
watch(() => store.streaming, (isStreaming) => {
  if (isStreaming) {
    const lastMsg = store.messages[store.messages.length - 1]
    thinking.value = lastMsg?.role === 'assistant' && lastMsg.content === ''
  } else {
    thinking.value = false
  }
})

// 流式消息断点重试
async function retryStream() {
  store.clearStreamError()
  await store.retryLastQuestion()
}

async function send() {
  const q = question.value.trim()
  if (!q || store.streaming) return
  if (uploading.value) return

  question.value = ''
  // 发送后重置锚点
  anchorActive.value = false
  anchorUserIndex.value = -1

  // 发送附件
  const atts = attachments.value
  attachments.value = []
  await store.sendQuestion(q, atts)
}

function onAttachClick() {
  fileInputRef.value?.click()
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  // 检查数量限制
  const currentCount = attachments.value.length
  const newCount = input.files.length
  if (currentCount + newCount > 5) {
    uploadError.value = '最多只能上传5个附件'
    input.value = ''
    return
  }

  // 检查大小限制
  for (const file of input.files) {
    if (file.size > 10 * 1024 * 1024) {
      uploadError.value = '单个文件不能超过10MB'
      input.value = ''
      return
    }
  }

  uploadError.value = ''
  uploading.value = true

  // 上传每个文件
  const newAttachments: Attachment[] = []
  for (let i = 0; i < input.files.length; i++) {
    const file = input.files[i]
    try {
      const att = await uploadAttachment(file)
      newAttachments.push(att)
    } catch (err) {
      console.error('Upload failed:', err)
      uploadError.value = `上传失败: ${file.name}`
    }
  }

  attachments.value = [...attachments.value, ...newAttachments]
  uploading.value = false
  input.value = ''
}

function removeAttachment(id: string) {
  attachments.value = attachments.value.filter(a => a.id !== id)
}

async function sendSuggested(query: string) {
  if (store.streaming) return
  await store.sendQuestion(query)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="chat-container">
    <div class="chat-header">
      <span class="chat-title">QA Copilot 对话</span>
      <div class="header-actions">
        <button class="btn-nav" :class="{ active: anchorActive }" title="上一句" @click="goAnchorUp">
          <span v-if="anchorActive && currentAnchorLabel">{{ currentAnchorLabel }}</span>
          <span v-else>↑ 上一句</span>
        </button>
        <button class="btn-nav" title="下一句" @click="goAnchorDown">下一句 ↓</button>
        <button class="btn-clear" @click="store.clearChat()">清除对话</button>
      </div>
    </div>

    <div ref="messagesEl" class="messages">
      <!-- 欢迎界面：消息为空时显示 -->
      <div v-if="store.messages.length === 0" class="welcome">
        <div class="welcome-icon">🤖</div>
        <h2 class="welcome-title">你好，我是 QA Copilot</h2>
        <p class="welcome-desc">
          我可以帮助你查询 Jira 任务、搜索知识库文档、解答技术问题。<br>
          选择下方话题快速开始，或直接输入你的问题。
        </p>
        <div class="suggested-topics">
          <button
            v-for="topic in suggestedTopics"
            :key="topic.query"
            class="topic-btn"
            :disabled="store.streaming"
            @click="onTopicClick(topic)"
          >
            <span class="topic-icon">{{ topic.icon }}</span>
            <span class="topic-text">{{ topic.text }}</span>
          </button>
        </div>
      </div>

      <!-- 消息列表 -->
      <MessageBubble
        v-for="(msg, i) in displayMessages"
        :key="i"
        :message="msg"
        :index="i"
        :session-id="store.currentSessionId || undefined"
        :onRegenerate="store.regenerate"
      />

      <div v-if="thinking" class="thinking">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="thinking-text">{{ store.currentStatus || '正在思考...' }}</span>
      </div>
    </div>

    <div class="input-area">
      <button
        v-if="store.streaming"
        class="btn-stop"
        @click="store.stopStream()"
      >
        <span class="stop-icon">■</span> 停止生成
      </button>
      <!-- 流式中断错误提示 + 重试按钮 -->
      <div v-if="store.streamError && !store.streaming" class="stream-error">
        <span class="stream-error-msg">{{ store.streamError }}</span>
        <button
          v-if="store.streamPartial"
          class="btn-retry"
          @click="retryStream"
        >
          继续生成
        </button>
        <button
          class="btn-dismiss"
          @click="store.clearStreamError()"
        >
          ×
        </button>
      </div>
      <!-- 上传错误提示 -->
      <div v-if="uploadError" class="upload-error" @click="uploadError = ''">
        {{ uploadError }}
      </div>
      <!-- 附件预览标签 -->
      <div v-if="attachments.length > 0" class="attached-files">
        <span v-for="att in attachments" :key="att.id" class="file-tag">
          📎 {{ att.filename }} ({{ (att.size / 1024).toFixed(1) }}KB)
          <button class="file-remove" @click="removeAttachment(att.id)">×</button>
        </span>
      </div>
      <!-- 上传中指示器 -->
      <div v-if="uploading" class="upload-indicator">
        上传中...
      </div>
      <div class="input-row">
        <button class="btn-attach" title="添加附件" @click="onAttachClick">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
          </svg>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          class="hidden-file-input"
          accept=".pdf,.docx,.txt,.md,.xlsx,.xls"
          multiple
          @change="onFileChange"
        >
        <textarea
          v-model="question"
          class="input-box"
          placeholder="输入问题，按 Enter 发送（Shift+Enter 换行）"
          rows="2"
          :disabled="store.streaming"
          @keydown="onKeydown"
        ></textarea>
        <button
          class="btn-send"
          :disabled="store.streaming || !question.trim()"
          @click="send"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
  flex-shrink: 0;
}

.chat-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.btn-nav {
  padding: var(--spacing-1) var(--spacing-3);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
  min-width: 70px;
  text-align: center;
}

.btn-nav:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-dark);
}

.btn-nav.active {
  background: var(--color-primary-bg);
  border-color: var(--color-primary-light);
  color: var(--color-primary);
}

.btn-clear {
  padding: var(--spacing-1) var(--spacing-4);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.btn-clear:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border-dark);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
  display: flex;
  flex-direction: column;
}

/* Welcome section */
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--spacing-10) var(--spacing-6);
}

.welcome-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-4);
}

.welcome-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
  margin: 0 0 var(--spacing-3);
}

.welcome-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-6);
  line-height: var(--line-height-relaxed);
}

.suggested-topics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-3);
  justify-content: center;
  max-width: 500px;
}

.topic-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--color-text);
  transition: all var(--transition-fast);
}

.topic-btn:hover:not(:disabled) {
  background: var(--color-primary-bg);
  border-color: var(--color-primary-light);
  color: var(--color-primary);
}

.topic-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.topic-icon {
  font-size: 16px;
}

.topic-text {
  font-weight: var(--font-weight-medium);
}

.thinking {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-2) 0;
}

.dot {
  width: 8px;
  height: 8px;
  background: var(--color-text-muted);
  border-radius: var(--radius-full);
  animation: bounce 1.2s infinite ease-in-out;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
  40%            { transform: scale(1);   opacity: 1;   }
}

.thinking-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-left: var(--spacing-1);
}

.input-area {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
  flex-shrink: 0;
  position: relative;
}

.input-row {
  display: flex;
  gap: var(--spacing-2);
  align-items: flex-end;
  position: relative;
}

.attached-files {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  padding: var(--spacing-2) 0;
}

.file-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-light);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

.file-remove {
  background: transparent;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0;
  margin-left: var(--spacing-1);
}

.file-remove:hover {
  color: var(--color-error);
}

.btn-attach {
  position: absolute;
  left: 6px;
  bottom: 6px;
  padding: var(--spacing-1);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);
  z-index: 1;
}

.btn-attach:hover {
  color: var(--color-primary);
}

.hidden-file-input {
  display: none;
}

.btn-stop {
  position: absolute;
  top: -40px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  z-index: 10;
  transition: all var(--transition-fast);
}

.btn-stop:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

.stop-icon {
  font-size: 10px;
  color: var(--color-error);
}

.stream-error {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-error-bg, #fef2f2);
  border: 1px solid var(--color-error, #ef4444);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-error, #ef4444);
  margin-bottom: var(--spacing-2);
}

.stream-error-msg {
  flex: 1;
}

.btn-retry {
  padding: var(--spacing-1) var(--spacing-3);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-retry:hover {
  background: var(--color-primary-dark);
}

.btn-dismiss {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 16px;
  padding: 0 var(--spacing-1);
}

.btn-dismiss:hover {
  color: var(--color-text);
}

.input-box {
  flex: 1;
  resize: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-2) 70px var(--spacing-2) 36px; /* 左侧给上传按钮留空间，右侧给发送按钮留空间 */
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  line-height: var(--line-height-normal);
  outline: none;
  transition: all var(--transition-fast);
  background: var(--color-bg-card);
  color: var(--color-text);
}

.input-box::placeholder {
  color: var(--color-text-muted);
}

.input-box:hover {
  border-color: var(--color-border-dark);
}

.input-box:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.input-box:disabled {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
}

.btn-send {
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: var(--spacing-1) var(--spacing-3);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  height: 28px;
  transition: all var(--transition-fast);
  z-index: 1;
}

.btn-send:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-send:disabled {
  background: var(--color-secondary-light);
  cursor: not-allowed;
}
</style>
