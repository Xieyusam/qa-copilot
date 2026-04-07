import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Document } from '../types'
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  getDocumentsStatus,
} from '../api/documents'

export type ToastType = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
}

let toastSeq = 0

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<Document[]>([])
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const deletingIds = ref(new Set<string>())
  const pollingTimer = ref<number | null>(null)
  const toasts = ref<Toast[]>([])

  function addToast(type: ToastType, message: string, duration = 3000) {
    const id = ++toastSeq
    toasts.value.push({ id, type, message })
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, duration)
  }

  async function fetchDocuments() {
    try {
      documents.value = await listDocuments()
      checkPolling()
    } catch (e: any) {
      console.error('Failed to fetch documents:', e)
      // 如果发生认证错误（比如在组件挂载时抛出），不要使用全局抛出让整个应用崩溃
      if (e.message !== 'Unauthorized') {
        addToast('error', e?.message || '获取文档列表失败')
      }
    }
  }

  async function upload(file: File, kbCategory: string = 'default') {
    uploading.value = true
    uploadProgress.value = 0
    try {
      await uploadDocument(file, kbCategory, (pct) => {
        uploadProgress.value = pct
      })
      await fetchDocuments()
      addToast('success', `「${file.name}」上传成功，正在处理中`)
    } catch (e: any) {
      addToast('error', e?.message || '上传失败，请重试')
      throw e
    } finally {
      uploading.value = false
      uploadProgress.value = 0
    }
  }

  async function remove(id: string) {
    if (deletingIds.value.has(id)) return
    deletingIds.value.add(id)
    const doc = documents.value.find(d => d.id === id)
    try {
      await deleteDocument(id)
      documents.value = documents.value.filter(d => d.id !== id)
      checkPolling()
      addToast('success', `「${doc?.filename ?? '文档'}」已删除`)
    } catch (e: any) {
      addToast('error', e?.message || '删除失败，请重试')
    } finally {
      deletingIds.value.delete(id)
    }
  }

  function checkPolling() {
    const pendingIds = documents.value
      .filter(d => d.status === 'pending' || d.status === 'processing')
      .map(d => d.id)

    if (pendingIds.length > 0 && !pollingTimer.value) {
      pollingTimer.value = window.setInterval(async () => {
        try {
          const currentPendingIds = documents.value
            .filter(d => d.status === 'pending' || d.status === 'processing')
            .map(d => d.id)
            
          if (currentPendingIds.length === 0) {
            stopPolling()
            return
          }

          const results = await getDocumentsStatus(currentPendingIds)
          let changed = false
          
          for (const result of results) {
            const idx = documents.value.findIndex(d => d.id === result.id)
            if (idx !== -1) {
              const prev = documents.value[idx]
              if (prev.status !== result.status) {
                documents.value[idx] = { ...prev, status: result.status as Document['status'] }
                changed = true
                if (result.status === 'ready') {
                  addToast('success', `「${prev.filename}」处理完成，已可用于问答`)
                } else if (result.status === 'failed') {
                  addToast('error', `「${prev.filename}」处理失败`)
                }
              }
            }
          }
          
          if (changed) {
            checkPolling()
          }
        } catch (e) {
          console.error('Failed to poll document status', e)
        }
      }, 3000)
    } else if (pendingIds.length === 0 && pollingTimer.value) {
      stopPolling()
    }
  }

  function stopPolling() {
    if (pollingTimer.value) {
      window.clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  return {
    documents,
    uploading,
    uploadProgress,
    deletingIds,
    toasts,
    fetchDocuments,
    upload,
    remove,
    addToast,
    checkPolling,
    stopPolling,
  }
})
