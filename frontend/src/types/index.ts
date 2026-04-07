export interface Document {
  id: string
  filename: string
  fileType: string
  fileSize: number
  status: 'pending' | 'processing' | 'ready' | 'failed'
  uploadedAt: string
  kbCategory: string
}

export interface SessionMeta {
  sessionId: string
  title: string
  createdAt: string
  lastActive: string
}

export interface SourceRef {
  docId: string
  filename: string
  chunkPosition: number
  similarityScore?: number
  content?: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: SourceRef[]
}

export interface Session {
  sessionId: string
}

// SSE 事件类型
export interface TokenEvent {
  type: 'token'
  content: string
}

export interface SourcesEvent {
  type: 'sources'
  data: SourceRef[]
}
