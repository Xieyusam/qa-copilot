import type { Document } from '../types'
import { request } from './request'

const API_BASE = '/api'

function toDocument(raw: Record<string, unknown>): Document {
  return {
    id: raw.id as string,
    filename: raw.filename as string,
    fileType: (raw.file_type ?? raw.fileType) as string,
    fileSize: (raw.file_size ?? raw.fileSize) as number,
    status: (raw.status as Document['status']),
    uploadedAt: (raw.uploaded_at ?? raw.uploadedAt) as string,
    kbCategory: (raw.kb_category ?? raw.kbCategory ?? 'default') as string,
    kbCategoryId: (raw.kb_category_id ?? raw.kbCategoryId ?? '') as string,
    feishuDocId: (raw.feishu_doc_id ?? raw.feishuDocId) as string | undefined,
  }
}

export function uploadDocument(
  file: File,
  kbCategory: string = 'default',
  onProgress?: (pct: number) => void,
  chunkingStrategy?: string,
): Promise<{ id: string; filename: string; status: string; kbCategory: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)
    if (chunkingStrategy) {
      formData.append('chunking_strategy', chunkingStrategy)
    }

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      })
    }

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const raw = JSON.parse(xhr.responseText)
          resolve({
            id: raw.id as string,
            filename: raw.filename as string,
            status: raw.status as string,
            kbCategory: raw.kb_category as string,
          })
        } catch {
          reject(new Error('Invalid response format'))
        }
      } else if (xhr.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
        reject(new Error('Unauthorized'))
      } else {
        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
    xhr.addEventListener('abort', () => reject(new Error('Upload aborted')))

    xhr.open('POST', `${API_BASE}/documents/upload?kb_category=${encodeURIComponent(kbCategory)}`)
    const token = localStorage.getItem('token')
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.send(formData)
  })
}

export async function listDocuments(): Promise<Document[]> {
  const res = await request(`${API_BASE}/documents`)
  if (!res.ok) {
    if (res.status === 401) throw new Error('Unauthorized')
    throw new Error(`Failed to list documents: ${res.status}`)
  }
  const data = await res.json()
  return (data as Record<string, unknown>[]).map(toDocument)
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await request(`${API_BASE}/documents/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete document: ${res.status}`)
}

export async function getDocumentStatus(
  id: string,
): Promise<{ id: string; status: string; errorMsg: string | null }> {
  const res = await request(`${API_BASE}/documents/${id}/status`)
  if (!res.ok) throw new Error(`Failed to get document status: ${res.status}`)
  const raw = await res.json()
  return {
    id: raw.id as string,
    status: raw.status as string,
    errorMsg: (raw.error_msg ?? raw.errorMsg ?? null) as string | null,
  }
}

export async function getDocumentsStatus(
  ids: string[],
): Promise<{ id: string; status: string; errorMsg: string | null }[]> {
  if (!ids.length) return []
  const res = await request(`${API_BASE}/documents/status?ids=${ids.join(',')}`)
  if (!res.ok) throw new Error(`Failed to get documents status: ${res.status}`)
  const data = await res.json()
  return (data as Record<string, unknown>[]).map(raw => ({
    id: raw.id as string,
    status: raw.status as string,
    errorMsg: (raw.error_msg ?? raw.errorMsg ?? null) as string | null,
  }))
}

export interface DocumentChunk {
  chunk_id: string
  position: number
  content: string
  kb_category: string
}

export interface DocumentChunksResponse {
  doc_id: string
  filename: string
  total_chunks: number
  chunks: DocumentChunk[]
}

export async function getDocumentChunks(docId: string): Promise<DocumentChunksResponse> {
  const res = await request(`${API_BASE}/documents/${docId}/chunks`)
  if (!res.ok) throw new Error(`Failed to get document chunks: ${res.status}`)
  return res.json()
}

export function getDocumentDownloadUrl(docId: string): string {
  return `${API_BASE}/documents/${docId}/download`
}
