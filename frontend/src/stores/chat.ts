import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, SessionMeta, SourceRef, Attachment } from '../types'
import {
  listSessions,
  createSession,
  deleteSession,
  sendMessage,
  clearHistory,
  getMessages,
} from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<SessionMeta[]>([])
  const currentSessionId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const streaming = ref(false)
  const currentSources = ref<SourceRef[]>([])
  const abortController = ref<AbortController | null>(null)

  // 流式消息断点重试支持
  const streamingContent = ref('')  // 当前正在接收的流式内容缓存
  const lastQuestion = ref('')      // 最后一次发送的问题
  const lastAttachments = ref<Attachment[] | undefined>(undefined)  // 最后一次发送的附件
  const streamError = ref<string | null>(null)  // 流式错误信息
  const streamPartial = ref(false)  // 是否是部分内容（中断过）
  const currentStatus = ref<string>('')  // 当前状态信息

  async function init() {
    sessions.value = await listSessions()
    if (sessions.value.length > 0) {
      await switchSession(sessions.value[0].sessionId)
    } else {
      await newSession()
    }
  }

  async function loadSessions() {
    sessions.value = await listSessions()
  }

  async function newSession() {
    const { sessionId } = await createSession()
    await loadSessions()
    await switchSession(sessionId)
  }

  async function switchSession(sessionId: string) {
    currentSessionId.value = sessionId
    messages.value = await getMessages(sessionId)
    currentSources.value = []
  }

  async function sendQuestion(question: string, attachments?: Attachment[]) {
    if (!currentSessionId.value) await newSession()

    // 保存问题上下文用于可能的断点重试
    lastQuestion.value = question
    lastAttachments.value = attachments
    streamError.value = null
    streamPartial.value = false

    messages.value.push({
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
      attachments: attachments,
    })
    messages.value.push({
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      sources: [],
    })

    streaming.value = true
    streamingContent.value = ''
    abortController.value = new AbortController()
    currentStatus.value = ''

    try {
      await sendMessage(
        currentSessionId.value!,
        question,
        (token) => {
          streamingContent.value += token
          const last = messages.value[messages.value.length - 1]
          if (last?.role === 'assistant') last.content += token
        },
        (sources) => {
          currentSources.value = sources
          const last = messages.value[messages.value.length - 1]
          if (last?.role === 'assistant') last.sources = sources
        },
        abortController.value.signal,
        attachments,
        (status) => {
          currentStatus.value = status
        },
      )
      // 成功完成，清除缓存
      streamingContent.value = ''
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted')
        return
      }
      // 记录错误信息
      streamError.value = err.message || '连接中断'
      streamPartial.value = streamingContent.value.length > 0
      // 发送失败时移除末尾空 assistant 消息，避免界面残留空气泡
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant' && last.content === '') {
        messages.value.pop()
      }
      throw err
    } finally {
      streaming.value = false
      abortController.value = null
      // 刷新会话列表（标题和 last_active 已在后端更新）
      await loadSessions()
    }
  }

  function stopStream() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
      streaming.value = false
    }
  }

  async function retryLastQuestion() {
    if (!lastQuestion.value || streaming.value) return

    // 移除最后一条用户消息（准备重新发送）
    if (messages.value.length > 0 && messages.value[messages.value.length - 1].role === 'user') {
      messages.value.pop()
    }
    // 移除最后一条 assistant 消息（如果有的话）
    if (messages.value.length > 0 && messages.value[messages.value.length - 1].role === 'assistant') {
      messages.value.pop()
    }

    // 重新发送
    await sendQuestion(lastQuestion.value, lastAttachments.value)
  }

  function clearStreamError() {
    streamError.value = null
    streamPartial.value = false
  }

  async function regenerate(messageIndex: number) {
    if (streaming.value) return

    // Find the closest previous user message if the target is an assistant message
    let targetUserIndex = messageIndex
    if (messages.value[messageIndex].role === 'assistant') {
      targetUserIndex = messageIndex - 1
    }

    if (targetUserIndex < 0 || messages.value[targetUserIndex].role !== 'user') return

    const questionToResend = messages.value[targetUserIndex].content
    const attachmentsToResend = messages.value[targetUserIndex].attachments

    // Remove messages from the target user message onwards
    messages.value.splice(targetUserIndex)

    // Resend the question (with original attachments)
    await sendQuestion(questionToResend, attachmentsToResend)
  }

  async function clearChat() {
    if (currentSessionId.value) {
      await clearHistory(currentSessionId.value)
    }
    messages.value = []
    currentSources.value = []
  }

  async function removeSession(sessionId: string) {
    await deleteSession(sessionId)
    await loadSessions()
    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0) {
        await switchSession(sessions.value[0].sessionId)
      } else {
        await newSession()
      }
    }
  }

  return {
    sessions,
    currentSessionId,
    messages,
    streaming,
    currentSources,
    streamingContent,
    lastQuestion,
    lastAttachments,
    streamError,
    streamPartial,
    currentStatus,
    init,
    loadSessions,
    newSession,
    switchSession,
    sendQuestion,
    stopStream,
    retryLastQuestion,
    clearStreamError,
    regenerate,
    clearChat,
    removeSession,
  }
})
