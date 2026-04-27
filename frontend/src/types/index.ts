export interface Document {
  id: string
  filename: string
  fileType: string
  fileSize: number
  status: 'pending' | 'processing' | 'ready' | 'failed'
  uploadedAt: string
  kbCategory: string       // 分类名称 (from kb_category_rel.name)
  kbCategoryId: string     // 分类 ID (from kb_category_id)
  feishuDocId?: string     // 飞书文档 ID（如果有）
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

export interface Attachment {
  id: string
  filename: string
  size: number
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: SourceRef[]
  attachments?: Attachment[]
  feedback_type?: 'positive' | 'negative' | null
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

export interface StatusEvent {
  type: 'status'
  content: string
}

export interface DoneEvent {
  type: 'done'
  content: string
}

export interface ErrorEvent {
  type: 'error'
  content: string
}

export type SSEEvent = TokenEvent | SourcesEvent | StatusEvent | DoneEvent | ErrorEvent
