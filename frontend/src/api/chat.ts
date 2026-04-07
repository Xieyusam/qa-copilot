import type { Message, SessionMeta, SourceRef, TokenEvent, SourcesEvent } from '../types'
import { request } from './request'

const API_BASE = '/api'

function toSourceRef(raw: Record<string, unknown>): SourceRef {
  return {
    docId: (raw.doc_id ?? raw.docId) as string,
    filename: raw.filename as string,
    chunkPosition: (raw.chunk_position ?? raw.chunkPosition) as number,
    similarityScore: (raw.similarity_score ?? raw.similarityScore) as number | undefined,
    content: raw.content as string | undefined,
  }
}

function toMessage(raw: Record<string, unknown>): Message {
  return {
    role: raw.role as 'user' | 'assistant',
    content: raw.content as string,
    timestamp: raw.timestamp as string,
    sources: raw.sources
      ? (raw.sources as Record<string, unknown>[]).map(toSourceRef)
      : undefined,
  }
}

function toSessionMeta(raw: Record<string, unknown>): SessionMeta {
  return {
    sessionId: (raw.session_id ?? raw.sessionId) as string,
    title: raw.title as string,
    createdAt: (raw.created_at ?? raw.createdAt) as string,
    lastActive: (raw.last_active ?? raw.lastActive) as string,
  }
}

export async function listSessions(): Promise<SessionMeta[]> {
  const res = await request(`${API_BASE}/chat/sessions`)
  if (!res.ok) throw new Error(`Failed to list sessions: ${res.status}`)
  const data = await res.json()
  return (data as Record<string, unknown>[]).map(toSessionMeta)
}

export async function createSession(): Promise<{ sessionId: string }> {
  const res = await request(`${API_BASE}/chat/sessions`, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`)
  const raw = await res.json()
  return { sessionId: (raw.session_id ?? raw.sessionId) as string }
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await request(`${API_BASE}/chat/sessions/${sessionId}`, { method: 'DELETE' })
  if (!res.ok && res.status !== 404) throw new Error(`Failed to delete session: ${res.status}`)
}

export async function sendMessage(
  sessionId: string,
  question: string,
  onToken: (token: string) => void,
  onSources: (sources: SourceRef[]) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await request(`${API_BASE}/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal,
  })

  if (!res.ok) throw new Error(`Failed to send message: ${res.status}`)
  if (!res.body) throw new Error('Response body is empty')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      // 处理末尾残留 buffer
      if (buffer.trim()) {
        const lines = buffer.split('\n')
        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const payload = line.slice(5).trim()
          if (payload === '[DONE]') break

          try {
            const event = JSON.parse(payload) as TokenEvent | SourcesEvent
            if (event.type === 'token') {
              onToken(event.content)
            } else if (event.type === 'sources') {
              const mappedSources = (event.data as unknown as Record<string, unknown>[]).map(toSourceRef)
              onSources(mappedSources)
            }
          } catch {
            // Ignore malformed SSE lines
          }
        }
      }
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (payload === '[DONE]') return

      try {
        const event = JSON.parse(payload) as TokenEvent | SourcesEvent
        if (event.type === 'token') {
          onToken(event.content)
        } else if (event.type === 'sources') {
          const mappedSources = (event.data as unknown as Record<string, unknown>[]).map(toSourceRef)
          onSources(mappedSources)
        }
      } catch {
        // Ignore malformed SSE lines
      }
    }
  }
}

export async function clearHistory(sessionId: string): Promise<void> {
  const res = await request(`${API_BASE}/chat/sessions/${sessionId}/history`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to clear history: ${res.status}`)
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const res = await request(`${API_BASE}/chat/sessions/${sessionId}/messages`)
  if (!res.ok) throw new Error(`Failed to get messages: ${res.status}`)
  const data = await res.json()
  return (data as Record<string, unknown>[]).map(toMessage)
}

export async function submitFeedback(
  sessionId: string,
  messageIndex: number,
  feedbackType: 'positive' | 'negative'
): Promise<{ status: string; feedback_type: string }> {
  const res = await request(`${API_BASE}/chat/sessions/${sessionId}/messages/${messageIndex}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback_type: feedbackType }),
  })
  if (!res.ok) throw new Error(`Failed to submit feedback: ${res.status}`)
  return res.json()
}
