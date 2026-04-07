<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useDocumentStore } from '../stores/documents'
import { useCategoryStore } from '../stores/categories'
import ConfirmDialog from './ConfirmDialog.vue'
import { getDocumentChunks, getDocumentDownloadUrl, type DocumentChunk } from '../api/documents'

const props = defineProps<{
  filterCategoryId?: string
}>()

const store = useDocumentStore()
const categoryStore = useCategoryStore()

const confirmTarget = ref<{ id: string; filename: string } | null>(null)
const selectedDoc = ref<{ id: string; filename: string } | null>(null)
const chunks = ref<DocumentChunk[]>([])
const chunksLoading = ref(false)
const showChunksModal = ref(false)

const STATUS_LABEL: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  ready: '就绪',
  failed: '失败',
}

const FILE_ICONS: Record<string, string> = {
  pdf: '📕',
  docx: '📘',
  txt: '📄',
  md: '📝',
}

// 过滤后的文档列表
const filteredDocuments = computed(() => {
  if (!props.filterCategoryId) return store.documents
  return store.documents.filter(doc => doc.kbCategory === props.filterCategoryId)
})

function fileIcon(type: string) {
  return FILE_ICONS[type?.toLowerCase()] ?? '📄'
}

function formatSize(bytes: number) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function formatDate(iso: string) {
  if (!iso) return '—'
  const normalized = /[Z+\-]\d*$/.test(iso) ? iso : iso + 'Z'
  return new Date(normalized).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function getCategoryName(categoryId: string): string {
  return categoryStore.getCategoryName(categoryId)
}

function askDelete(id: string, filename: string) {
  confirmTarget.value = { id, filename }
}

async function confirmDelete() {
  if (!confirmTarget.value) return
  await store.remove(confirmTarget.value.id)
  confirmTarget.value = null
}

async function viewChunks(doc: { id: string; filename: string }) {
  selectedDoc.value = doc
  chunksLoading.value = true
  showChunksModal.value = true
  chunks.value = []

  try {
    const result = await getDocumentChunks(doc.id)
    chunks.value = result.chunks
  } catch (err) {
    console.error('Failed to load chunks:', err)
    chunks.value = []
  } finally {
    chunksLoading.value = false
  }
}

function downloadDocument(docId: string) {
  const url = getDocumentDownloadUrl(docId)
  const token = localStorage.getItem('token')
  const link = document.createElement('a')
  link.href = url
  if (token) {
    // Use fetch with auth header for protected downloads
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.blob())
      .then(blob => {
        const blobUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = blobUrl
        a.download = selectedDoc.value?.filename || 'document'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(blobUrl)
      })
      .catch(err => console.error('Download failed:', err))
  } else {
    link.target = '_blank'
    link.click()
  }
}

function closeChunksModal() {
  showChunksModal.value = false
  selectedDoc.value = null
  chunks.value = []
}

onMounted(async () => {
  await Promise.all([
    store.fetchDocuments(),
    categoryStore.fetchCategories(),
  ])
})
</script>

<template>
  <div class="doc-list">
    <!-- Empty state -->
    <div v-if="filteredDocuments.length === 0" class="empty-state">
      <div class="empty-icon">📭</div>
      <p class="empty-title">{{ filterCategoryId ? '该分类暂无文档' : '暂无文档' }}</p>
      <p class="empty-sub">上传文档后，即可在问答页面使用知识库</p>
    </div>

    <!-- Document cards -->
    <div v-else class="cards">
      <div
        v-for="doc in filteredDocuments"
        :key="doc.id"
        class="card"
        :class="{ 'card-deleting': store.deletingIds.has(doc.id) }"
      >
        <div class="card-icon">{{ fileIcon(doc.fileType) }}</div>

        <div class="card-body">
          <div class="card-top">
            <span class="card-name" :title="doc.filename">{{ doc.filename }}</span>
          </div>

          <div class="card-meta">
            <span class="meta-item">
              <span class="meta-label">知识库</span>
              <span class="meta-value">{{ getCategoryName(doc.kbCategory) }}</span>
            </span>
            <span class="meta-sep">·</span>
            <span class="meta-item">
              <span class="meta-label">类型</span>
              <span class="meta-value">{{ doc.fileType?.toUpperCase() }}</span>
            </span>
            <span class="meta-sep">·</span>
            <span class="meta-item">
              <span class="meta-label">大小</span>
              <span class="meta-value">{{ formatSize(doc.fileSize) }}</span>
            </span>
            <span class="meta-sep">·</span>
            <span class="meta-item">
              <span class="meta-label">上传时间</span>
              <span class="meta-value">{{ formatDate(doc.uploadedAt) }}</span>
            </span>
          </div>

          <p v-if="doc.status === 'failed'" class="error-hint">
            ⚠ 文档处理失败，请删除后重新上传
          </p>
        </div>

        <div class="card-right">
          <span class="status-badge" :class="'status-' + doc.status">
            <span v-if="doc.status === 'processing'" class="status-spinner"></span>
            {{ STATUS_LABEL[doc.status] ?? doc.status }}
          </span>
          <button
            v-if="doc.status === 'ready'"
            class="btn-action"
            @click="viewChunks({ id: doc.id, filename: doc.filename })"
            title="查看分片"
          >
            📖
          </button>
          <button
            v-if="doc.status === 'ready'"
            class="btn-action btn-download"
            @click="downloadDocument(doc.id)"
            title="下载原文"
          >
            ⬇️
          </button>
          <button
            class="btn-delete"
            :disabled="store.deletingIds.has(doc.id)"
            @click="askDelete(doc.id, doc.filename)"
            title="删除文档"
          >
            <span v-if="store.deletingIds.has(doc.id)" class="btn-spinner"></span>
            <span v-else>🗑</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 二次确认弹窗 -->
    <ConfirmDialog
      v-if="confirmTarget"
      title="确认删除文档"
      :message="`确定要删除「${confirmTarget.filename}」吗？删除后将同时移除其向量索引，无法恢复。`"
      :loading="store.deletingIds.has(confirmTarget.id)"
      @confirm="confirmDelete"
      @cancel="confirmTarget = null"
    />

    <!-- 分片查看弹窗 -->
    <Teleport to="body">
      <div v-if="showChunksModal" class="modal-overlay" @click="closeChunksModal">
        <div class="modal" @click.stop>
          <div class="modal-header">
            <h3>{{ selectedDoc?.filename }} - 分片列表</h3>
            <button class="btn-close" @click="closeChunksModal">&times;</button>
          </div>
          <div class="modal-body">
            <div v-if="chunksLoading" class="loading">加载中...</div>
            <div v-else-if="chunks.length === 0" class="empty">暂无分片数据</div>
            <div v-else class="chunks-list">
              <div v-for="chunk in chunks" :key="chunk.chunk_id" class="chunk-item">
                <div class="chunk-header">
                  <span class="chunk-position">分片 #{{ chunk.position + 1 }}</span>
                  <span class="chunk-category">{{ chunk.kb_category }}</span>
                </div>
                <div class="chunk-content">{{ chunk.content }}</div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="closeChunksModal">关闭</button>
            <button class="btn-primary" @click="downloadDocument(selectedDoc?.id || '')">
              ⬇️ 下载原文
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.doc-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-5);
  margin-bottom: var(--spacing-3);
  background: var(--color-bg);
}

.doc-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.filter-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.filter-select {
  width: 160px;
}

.btn-clear-filter {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-clear-filter:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-15) var(--spacing-5);
  gap: var(--spacing-2);
}

.empty-icon { font-size: 40px; }

.empty-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin: 0;
}

.empty-sub {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 0;
  text-align: center;
}

.cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  padding: var(--spacing-1);
}

.card {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-4) var(--spacing-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  transition: box-shadow var(--transition-fast), opacity var(--transition-fast), transform var(--transition-fast);
}

.card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.card-deleting {
  opacity: 0.5;
  pointer-events: none;
}

.card-icon {
  font-size: 32px;
  flex-shrink: 0;
  line-height: 1;
}

.card-right {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-2);
  flex-shrink: 0;
}

.card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.card-top {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.card-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  flex-shrink: 0;
}

.status-pending    { background: var(--color-warning-bg); color: var(--color-warning); }
.status-processing { background: var(--color-primary-bg); color: var(--color-primary); }
.status-ready      { background: var(--color-success-bg); color: var(--color-success); }
.status-failed     { background: var(--color-error-bg); color: var(--color-error); }

.status-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--color-primary-light);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

.card-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-xs);
}

.meta-label { color: var(--color-text-muted); font-weight: var(--font-weight-normal); }
.meta-value { color: var(--color-text-secondary); font-weight: var(--font-weight-medium); }
.meta-sep   { color: var(--color-border); }

.error-hint {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin: 0;
  padding: var(--spacing-1) 0;
}

.btn-delete {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-base);
  transition: all var(--transition-fast);
}

.btn-delete:hover:not(:disabled) {
  background: var(--color-error-bg);
  border-color: var(--color-error-light);
}

.btn-delete:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-error-light);
  border-top-color: var(--color-error);
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

.btn-action {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-base);
  transition: all var(--transition-fast);
}

.btn-action:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary-light);
}

.btn-download:hover {
  background: var(--color-success-bg);
  border-color: var(--color-success-light);
}

.card-actions {
  flex-shrink: 0;
  display: flex;
  gap: var(--spacing-2);
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn var(--transition-fast);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  width: 700px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  animation: slideUp var(--transition-normal);
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.modal-header {
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.btn-close {
  background: transparent;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color var(--transition-fast);
}

.btn-close:hover {
  color: var(--color-text);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-5);
  min-height: 200px;
}

.loading, .empty {
  text-align: center;
  padding: var(--spacing-10);
  color: var(--color-text-muted);
}

.chunks-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.chunk-item {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.chunk-header {
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chunk-position {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

.chunk-category {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.chunk-content {
  padding: var(--spacing-4);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.modal-footer {
  padding: var(--spacing-4) var(--spacing-5);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}

.btn-secondary {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  background: var(--color-bg);
  border-color: var(--color-border-dark);
}

.btn-primary {
  background: var(--color-primary);
  border: none;
  color: var(--color-text-inverse);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}
</style>
