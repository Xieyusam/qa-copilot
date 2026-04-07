<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'

const store = useChatStore()
const question = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const thinking = ref(false)

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

async function send() {
  const q = question.value.trim()
  if (!q || store.streaming) return
  question.value = ''
  // 发送后重置锚点
  anchorActive.value = false
  anchorUserIndex.value = -1
  await store.sendQuestion(q)
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
        <span class="thinking-text">正在思考...</span>
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
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
  flex-shrink: 0;
  position: relative;
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

.input-box {
  flex: 1;
  resize: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-2) var(--spacing-3);
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
  padding: 0 var(--spacing-5);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  align-self: flex-end;
  height: 38px;
  transition: all var(--transition-fast);
}

.btn-send:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-send:disabled {
  background: var(--color-secondary-light);
  cursor: not-allowed;
}
</style>
