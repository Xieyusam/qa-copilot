import { request } from './request'

export interface Trace {
  id: string
  session_id: string
  message_index: number
  question: string
  final_answer: string | null
  total_time_ms: number
  created_at: string
  steps_count: number
}

export interface TraceStep {
  id: string
  step_index: number
  step_type: string
  tool_name: string | null
  input_prompt: string | null
  output_result: string | null
  start_time_ms: number
  time_ms: number
  duration_ms: number
  created_at: string
}

export interface TraceDetail extends Trace {
  steps: TraceStep[]
  attachments_json: string | null
}

export interface TraceListResponse {
  total: number
  page: number
  page_size: number
  items: Trace[]
}

export interface FeedbackStatistics {
  positive_count: number
  negative_count: number
  total_count: number
}

export interface Feedback {
  id: string
  session_id: string
  message_index: number
  feedback_type: string
  user_id: string
  created_at: string
}

export interface FeedbackListResponse {
  total: number
  page: number
  page_size: number
  statistics: FeedbackStatistics
  items: Feedback[]
}

export async function getTraces(page: number = 1, pageSize: number = 20, sessionId?: string): Promise<TraceListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (sessionId) params.append('session_id', sessionId)
  const response = await request(`/api/admin/traces?${params}`)
  if (!response.ok) throw new Error(`Failed to fetch traces: ${response.status}`)
  return response.json()
}

export async function getTraceDetail(traceId: string): Promise<TraceDetail> {
  const response = await request(`/api/admin/traces/${traceId}`)
  if (!response.ok) throw new Error(`Failed to fetch trace detail: ${response.status}`)
  return response.json()
}

export async function exportTrace(traceId: string): Promise<void> {
  const response = await request(`/api/admin/traces/${traceId}/export`)
  if (!response.ok) throw new Error(`Failed to export trace: ${response.status}`)
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `trace_${traceId}.json`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function getFeedbacks(page: number = 1, pageSize: number = 20, sessionId?: string, feedbackType?: string): Promise<FeedbackListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (sessionId) params.append('session_id', sessionId)
  if (feedbackType) params.append('feedback_type', feedbackType)
  const response = await request(`/api/admin/feedbacks?${params}`)
  if (!response.ok) throw new Error(`Failed to fetch feedbacks: ${response.status}`)
  return response.json()
}