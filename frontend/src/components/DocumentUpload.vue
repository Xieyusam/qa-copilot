<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentStore } from '../stores/documents'
import { useCategoryStore } from '../stores/categories'

const props = defineProps<{
  open?: boolean
}>()

const emit = defineEmits<{
  (e: 'open'): void
  (e: 'close'): void
}>()

const store = useDocumentStore()
const categoryStore = useCategoryStore()
const isDragging = ref(false)
const localError = ref('')
const justUploaded = ref(false)
const selectedCategory = ref('')

// 加载分类列表
async function loadCategories() {
  try {
    await categoryStore.fetchCategories()
    if (categoryStore.categories.length > 0 && !selectedCategory.value) {
      selectedCategory.value = categoryStore.categories[0].id
    }
  } catch (e) {
    console.error('Failed to load categories:', e)
  }
}

loadCategories()

function validate(file: File): string {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  const ACCEPTED = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.xls']
  if (!ACCEPTED.includes(ext)) return '不支持的格式'
  if (file.size > 50 * 1024 * 1024) return '文件超过 50MB'
  return ''
}

async function handleFile(file: File) {
  localError.value = ''
  justUploaded.value = false
  const err = validate(file)
  if (err) { localError.value = err; return }
  if (!selectedCategory.value) {
    localError.value = '请先选择分类'
    return
  }
  try {
    await store.upload(file, selectedCategory.value)
    justUploaded.value = true
    setTimeout(() => { justUploaded.value = false }, 2500)
  } catch (e: any) {
    localError.value = e?.message || '上传失败'
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) handleFile(input.files[0])
  input.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

const ACCEPTED_TEXT = '.pdf, .docx, .txt, .md, .xlsx'
</script>

<template>
  <div class="upload-dialog">
    <div class="upload-icon-btn" @click="emit('open')">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="17 8 12 3 7 8"></polyline>
        <line x1="12" y1="3" x2="12" y2="15"></line>
      </svg>
      <span>上传文档</span>
    </div>

    <!-- Upload Modal -->
    <Teleport to="body">
      <div v-if="props.open" class="modal-overlay" @click.self="emit('close')">
        <div class="modal-card">
          <div class="modal-header">
            <h3>上传知识文档</h3>
            <button class="btn-close" @click="emit('close')">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="form-item">
              <label>选择知识库</label>
              <select v-model="selectedCategory" class="styled-select">
                <option value="" disabled>请选择分类</option>
                <option v-for="cat in categoryStore.categories" :key="cat.id" :value="cat.id">
                  {{ cat.name }}{{ cat.description ? ` - ${cat.description}` : '' }}
                </option>
              </select>
            </div>

            <div
              class="drop-zone"
              :class="{ dragging: isDragging, uploading: store.uploading, success: justUploaded }"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="onDrop"
            >
              <template v-if="store.uploading">
                <div class="spinner"></div>
                <p class="hint">正在上传...</p>
                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: store.uploadProgress + '%' }"></div>
                </div>
                <p class="progress-text">{{ store.uploadProgress }}%</p>
              </template>

              <template v-else-if="justUploaded">
                <div class="success-icon">✓</div>
                <p class="hint success-text">上传成功</p>
              </template>

              <template v-else>
                <div class="upload-icon-large">📄</div>
                <p class="hint">拖拽文件到此处，或</p>
                <label class="btn-select">
                  选择文件
                  <input type="file" accept=".pdf,.docx,.txt,.md,.xlsx,.xls" hidden @change="onFileChange" />
                </label>
              </template>
            </div>

            <p v-if="localError" class="error-msg">{{ localError }}</p>

            <div class="formats-info">
              <span>支持格式：{{ ACCEPTED_TEXT }}</span>
              <span>最大 50MB</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.upload-dialog {
  display: inline-block;
}

.upload-icon-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.upload-icon-btn:hover {
  background: var(--color-primary-dark);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  width: 440px;
  max-width: 95vw;
  box-shadow: var(--shadow-lg);
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
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-1);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

.modal-body {
  padding: var(--spacing-5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.form-item label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.styled-select {
  width: 100%;
  padding: var(--spacing-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}

.styled-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-8) var(--spacing-5);
  text-align: center;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-3);
}

.drop-zone.dragging {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}

.drop-zone.uploading {
  border-color: var(--color-primary);
  cursor: not-allowed;
}

.drop-zone.success {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.upload-icon-large { font-size: 36px; }
.success-icon { font-size: 36px; color: var(--color-success); }

.hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.success-text { color: var(--color-success); font-weight: var(--font-weight-medium); }

.btn-select {
  padding: var(--spacing-2) var(--spacing-5);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-select:hover { background: var(--color-primary-dark); }

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-primary-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.progress-track {
  width: 200px;
  height: 6px;
  background: var(--color-primary-bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width var(--transition-fast);
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  margin: 0;
}

.error-msg {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin: 0;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
}

.formats-info {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
</style>