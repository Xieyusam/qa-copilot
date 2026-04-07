import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, SessionMeta, SourceRef } from '../types'
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

  // 加载会话列表，并自动切换到最近一次会话（或新建）
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

  async function sendQuestion(question: string) {
    if (!currentSessionId.value) await newSession()

    messages.value.push({
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    })
    messages.value.push({
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      sources: [],
    })

    streaming.value = true
    abortController.value = new AbortController()

    try {
      await sendMessage(
        currentSessionId.value!,
        question,
        (token) => {
          const last = messages.value[messages.value.length - 1]
          if (last?.role === 'assistant') last.content += token
        },
        (sources) => {
          currentSources.value = sources
          const last = messages.value[messages.value.length - 1]
          if (last?.role === 'assistant') last.sources = sources
        },
        abortController.value.signal
      )
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted')
        return
      }
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

  async function regenerate(messageIndex: number) {
    if (streaming.value) return
    
    // Find the closest previous user message if the target is an assistant message
    let targetUserIndex = messageIndex
    if (messages.value[messageIndex].role === 'assistant') {
      targetUserIndex = messageIndex - 1
    }
    
    if (targetUserIndex < 0 || messages.value[targetUserIndex].role !== 'user') return
    
    const questionToResend = messages.value[targetUserIndex].content
    
    // Remove messages from the target user message onwards
    messages.value.splice(targetUserIndex)
    
    // Resend the question
    await sendQuestion(questionToResend)
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
    init,
    loadSessions,
    newSession,
    switchSession,
    sendQuestion,
    stopStream,
    regenerate,
    clearChat,
    removeSession,
  }
})
