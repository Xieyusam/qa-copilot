import { request } from './request'

export interface Attachment {
  id: string
  filename: string
  size: number
}

export async function uploadAttachment(file: File): Promise<Attachment> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await request('/api/attachments', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function getAttachment(id: string): Promise<Attachment> {
  const res = await request(`/api/attachments/${id}`)
  if (!res.ok) throw new Error(`Get attachment failed: ${res.status}`)
  return res.json()
}
