import { request } from './request'

export interface FeishuDocument {
  id: string
  feishu_doc_url: string
  feishu_doc_type: string
  title: string
  kb_category_id: string
  is_active: boolean
  sync_interval_hours: number
  last_sync_status: string
  last_sync_error: string | null
  last_fetched_at: string | null
  created_at: string
  updated_at: string | null
}

export interface FeishuDocumentCreate {
  feishu_doc_url: string
  feishu_doc_type: string
  title: string
  kb_category_id: string
  is_active?: boolean
  sync_interval_hours?: number
}

export interface FeishuDocumentUpdate {
  feishu_doc_url?: string
  feishu_doc_type?: string
  title?: string
  kb_category_id?: string
  is_active?: boolean
  sync_interval_hours?: number
}

const API_BASE = '/api/admin/feishu'

export async function listFeishuDocuments(): Promise<FeishuDocument[]> {
  const res = await request(`${API_BASE}/documents`)
  if (!res.ok) throw new Error('获取飞书文档列表失败')
  return res.json()
}

export async function createFeishuDocument(data: FeishuDocumentCreate): Promise<FeishuDocument> {
  const res = await request(`${API_BASE}/documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '注册飞书文档失败')
  }
  return res.json()
}

export async function updateFeishuDocument(id: string, data: FeishuDocumentUpdate): Promise<FeishuDocument> {
  const res = await request(`${API_BASE}/documents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '更新飞书文档失败')
  }
  return res.json()
}

export async function deleteFeishuDocument(id: string): Promise<void> {
  const res = await request(`${API_BASE}/documents/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除飞书文档失败')
}

export async function syncFeishuDocument(id: string): Promise<void> {
  const res = await request(`${API_BASE}/documents/${id}/sync`, { method: 'POST' })
  if (!res.ok) throw new Error('触发同步失败')
}

export async function syncAllFeishuDocuments(): Promise<void> {
  const res = await request(`${API_BASE}/sync-all`, { method: 'POST' })
  if (!res.ok) throw new Error('触发全量同步失败')
}
