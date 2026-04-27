<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentStore } from '../stores/documents'
import { useCategoryStore } from '../stores/categories'
import { createFeishuDocument, type FeishuDocumentCreate } from '../api/feishu'
import { getChunkingConfig } from '../api/categories'

const props = defineProps<{
  open?: boolean
  defaultCategoryId?: string
}>()

const emit = defineEmits<{
  (e: 'open'): void
  (e: 'close'): void
  (e: 'uploaded'): void
}>()

const store = useDocumentStore()
const categoryStore = useCategoryStore()

const activeTab = ref<'upload' | 'feishu'>('upload')
const isDragging = ref(false)
const localError = ref('')
const justUploaded = ref(false)

// 分片策略
const STRATEGIES = [
  { value: 'recursive_text', label: '递归文本切分（通用）' },
  { value: 'semantic', label: '语义切分（AI 边界检测）' },
  { value: 'sentence', label: '句子切分（正则标点）' },
  { value: 'sliding_window', label: '滑动窗口（固定 token 重叠）' },
  { value: 'markdown', label: 'Markdown 切分（保留标题结构）' },
  { value: 'excel', label: 'Excel 切分（保持表格结构）' },
]

// 按文件类型推荐的分片策略
const STRATEGY_BY_TYPE: Record<string, string> = {
  pdf: 'semantic',
  md: 'markdown',
  markdown: 'markdown',
  docx: 'recursive_text',
  txt: 'recursive_text',
  xlsx: 'excel',
  xls: 'excel',
}

const chunkingStrategy = ref('recursive_text')
const chunkingMaxTokens = ref(512)
const chunkingOverlap = ref(50)
const showChunkingAdvanced = ref(false)
const selectedFileName = ref('')
const userOverriddenStrategy = ref(false) // 用户是否手动切换过策略

// 飞书表单
const feishuUrl = ref('')
const feishuTitle = ref('')
const feishuType = ref('doc')

async function loadChunkingConfig() {
  if (!props.defaultCategoryId) return
  try {
    const cfg = await getChunkingConfig(props.defaultCategoryId)
    if (cfg) {
      chunkingStrategy.value = cfg.chunking_strategy
      chunkingMaxTokens.value = cfg.max_tokens
      chunkingOverlap.value = cfg.overlap
    }
  } catch (e) {
    console.error('Failed to load chunking config:', e)
  }
}

function onOpen() {
  activeTab.value = 'upload'
  selectedFileName.value = ''
  userOverriddenStrategy.value = false
  loadChunkingConfig()
  localError.value = ''
  justUploaded.value = false
  feishuUrl.value = ''
  feishuTitle.value = ''
  feishuType.value = 'doc'
}

function onStrategyChange() {
  userOverriddenStrategy.value = true
}

function validateFile(file: File): string {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  const ACCEPTED = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.xls']
  if (!ACCEPTED.includes(ext)) return '不支持的格式'
  if (file.size > 100 * 1024 * 1024) return '文件超过 100MB'
  return ''
}

const pendingFile = ref<File | null>(null)

async function handleFile(file: File) {
  localError.value = ''
  const err = validateFile(file)
  if (err) { localError.value = err; return }
  if (!props.defaultCategoryId) {
    localError.value = '未指定目标知识库'
    return
  }

  // 本地预览文件名（不立即上传）
  pendingFile.value = file
  selectedFileName.value = file.name

  // 根据文件类型推荐分片策略（仅当用户未手动覆盖时）
  if (!userOverriddenStrategy.value) {
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    const recommended = STRATEGY_BY_TYPE[ext] || 'recursive_text'
    chunkingStrategy.value = recommended
  }
}

async function confirmUpload() {
  if (!pendingFile.value) return
  localError.value = ''
  try {
    await store.upload(pendingFile.value, props.defaultCategoryId, chunkingStrategy.value)
    justUploaded.value = true
    pendingFile.value = null
    selectedFileName.value = ''
    userOverriddenStrategy.value = false
    setTimeout(() => {
      justUploaded.value = false
      emit('close')
    }, 1500)
  } catch (e: any) {
    localError.value = e?.message || '上传失败'
  }
}

function cancelUpload() {
  pendingFile.value = null
  selectedFileName.value = ''
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

// 飞书相关
function validateFeishu(): string {
  if (!feishuUrl.value.trim()) return '请输入飞书文档链接'
  if (!feishuUrl.value.includes('feishu.cn') && !feishuUrl.value.includes('larksuite.com')) {
    return '请输入有效的飞书文档链接'
  }
  if (!feishuTitle.value.trim()) return '请输入文档标题'
  if (!props.defaultCategoryId) {
    if (categoryStore.categories.length > 0) {
      // auto-select first category
    } else {
      return '请先创建知识库分类'
    }
  }
  return ''
}

async function handleFeishuSubmit() {
  localError.value = ''
  const err = validateFeishu()
  if (err) { localError.value = err; return }

  try {
    const targetCategoryId = props.defaultCategoryId || categoryStore.categories[0]?.id || ''
    const data: FeishuDocumentCreate = {
      feishu_doc_url: feishuUrl.value.trim(),
      feishu_doc_type: feishuType.value,
      title: feishuTitle.value.trim(),
      kb_category_id: targetCategoryId,
      is_active: true,
      sync_interval_hours: -1,  // 不自动同步
    }
    await createFeishuDocument(data)

    // 立即显示成功状态，不轮询
    justUploaded.value = true
    setTimeout(() => {
      justUploaded.value = false
      emit('close')
      emit('uploaded')  // 通知父组件刷新
    }, 1500)
  } catch (e: any) {
    localError.value = e?.message || '注册失败'
  }
}

defineExpose({ onOpen })
</script>

<template>
  <div class="upload-panel">
    <div class="upload-icon-btn" @click="emit('open')">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="17 8 12 3 7 8"></polyline>
        <line x1="12" y1="3" x2="12" y2="15"></line>
      </svg>
      <span>上传文档</span>
    </div>

    <!-- Modal -->
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

          <!-- Tab 切换 -->
          <div class="tab-nav">
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'upload' }"
              @click="activeTab = 'upload'"
            >
              本地上传
            </button>
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'feishu' }"
              @click="activeTab = 'feishu'"
            >
              飞书文档
            </button>
          </div>

          <div class="modal-body">
            <!-- 上传成功 -->
            <div v-if="justUploaded" class="success-state">
              <div class="success-icon">✓</div>
              <p class="success-text">{{ activeTab === 'feishu' ? '注册成功' : '上传成功' }}</p>
            </div>

            <!-- ====== Tab 1: 本地上传 ====== -->
            <template v-else-if="activeTab === 'upload'">
              <div
                class="drop-zone"
                :class="{ dragging: isDragging, uploading: store.uploading }"
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

                <template v-else-if="pendingFile">
                  <div class="upload-icon-large">📄</div>
                  <p class="selected-file">{{ pendingFile.name }}</p>
                  <p class="hint">文件已就绪</p>
                  <button class="btn-reselect" @click="cancelUpload">重新选择</button>
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

              <!-- 分片策略 -->
              <div class="form-item">
                <div class="chunking-header" @click="showChunkingAdvanced = !showChunkingAdvanced">
                  <label class="form-label">分片策略</label>
                  <span class="chunking-toggle">{{ showChunkingAdvanced ? '收起' : '展开' }}</span>
                </div>
                <select v-model="chunkingStrategy" class="styled-select" @change="onStrategyChange">
                  <option v-for="s in STRATEGIES" :key="s.value" :value="s.value">
                    {{ s.label }}
                  </option>
                </select>
                <p v-if="selectedFileName && !userOverriddenStrategy" class="strategy-hint">
                  已根据文件类型自动推荐策略，可手动切换
                </p>
              </div>

              <div v-if="showChunkingAdvanced" class="chunking-advanced">
                <div class="form-row">
                  <div class="form-item">
                    <label class="form-label">最大 Token 数</label>
                    <input v-model.number="chunkingMaxTokens" type="number" class="styled-input" min="64" max="4096">
                  </div>
                  <div class="form-item">
                    <label class="form-label">重叠 Token 数</label>
                    <input v-model.number="chunkingOverlap" type="number" class="styled-input" min="0" max="256">
                  </div>
                </div>
                <p class="chunking-hint">策略：{{ STRATEGIES.find(s => s.value === chunkingStrategy)?.label }}</p>
              </div>

              <p v-if="localError" class="error-msg">{{ localError }}</p>
              <div class="formats-info">
                <span>支持格式：.pdf, .docx, .txt, .md, .xlsx</span>
                <span>最大 100MB</span>
              </div>

              <!-- Tab1 footer actions (shown when file is selected) -->
              <div v-if="activeTab === 'upload' && pendingFile" class="tab-footer">
                <button class="btn-confirm" :disabled="store.uploading" @click="confirmUpload">
                  <span v-if="store.uploading" class="btn-spinner"></span>
                  <span v-else>确认上传</span>
                </button>
              </div>
            </template>

            <!-- ====== Tab 2: 飞书链接 ====== -->
            <template v-else>
              <div class="form-item">
                <label>飞书文档链接</label>
                <input
                  v-model="feishuUrl"
                  type="text"
                  class="styled-input"
                  placeholder="https://feishu.cn/docx/xxx"
                >
              </div>

              <div class="form-item">
                <label>文档标题</label>
                <input
                  v-model="feishuTitle"
                  type="text"
                  class="styled-input"
                  placeholder="给文档起一个名称"
                >
              </div>

              <div class="form-item">
                <label>文档类型</label>
                <select v-model="feishuType" class="styled-select">
                  <option value="doc">文档 (Doc)</option>
                  <option value="sheet">表格 (Sheet)</option>
                  <option value="bitable">多维表格 (Bitable)</option>
                </select>
              </div>

              <!-- 分片策略 -->
              <div class="form-item">
                <div class="chunking-header" @click="showChunkingAdvanced = !showChunkingAdvanced">
                  <label class="form-label">分片策略</label>
                  <span class="chunking-toggle">{{ showChunkingAdvanced ? '收起' : '展开' }}</span>
                </div>
                <select v-model="chunkingStrategy" class="styled-select" @change="onStrategyChange">
                  <option v-for="s in STRATEGIES" :key="s.value" :value="s.value">
                    {{ s.label }}
                  </option>
                </select>
                <p v-if="selectedFileName && !userOverriddenStrategy" class="strategy-hint">
                  已根据文件类型自动推荐策略，可手动切换
                </p>
              </div>

              <div v-if="showChunkingAdvanced" class="chunking-advanced">
                <div class="form-row">
                  <div class="form-item">
                    <label class="form-label">最大 Token 数</label>
                    <input v-model.number="chunkingMaxTokens" type="number" class="styled-input" min="64" max="4096">
                  </div>
                  <div class="form-item">
                    <label class="form-label">重叠 Token 数</label>
                    <input v-model.number="chunkingOverlap" type="number" class="styled-input" min="0" max="256">
                  </div>
                </div>
              </div>

              <p v-if="localError" class="error-msg">{{ localError }}</p>

              <button class="btn-submit" @click="handleFeishuSubmit">
                确认导入
              </button>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.upload-panel {
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
  width: 480px;
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

/* Tab */
.tab-nav {
  display: flex;
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  flex: 1;
  padding: var(--spacing-3);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-btn:hover:not(.active) {
  color: var(--color-text);
}

.modal-body {
  padding: var(--spacing-5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  max-height: 70vh;
  overflow-y: auto;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.form-item label,
.form-label {
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

.styled-input {
  width: 100%;
  padding: var(--spacing-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-bg);
  color: var(--color-text);
  box-sizing: border-box;
}

.styled-select:focus,
.styled-input:focus {
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

.upload-icon-large { font-size: 36px; }
.success-icon { font-size: 36px; color: var(--color-success); }
.success-text { color: var(--color-success); font-weight: var(--font-weight-medium); margin: 0; }

.hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.selected-file {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.confirm-actions {
  display: flex;
  gap: var(--spacing-3);
  align-items: center;
}

.tab-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding-top: var(--spacing-2);
  border-top: 1px solid var(--color-border);
}

.btn-reselect {
  margin-top: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-3);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-reselect:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-text-secondary);
  color: var(--color-text);
}

.btn-confirm {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2) var(--spacing-5);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  min-width: 100px;
  transition: background var(--transition-fast);
}

.btn-confirm:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

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

.form-row {
  display: flex;
  gap: var(--spacing-4);
}

.form-row .form-item {
  flex: 1;
}

/* Chunking */
.chunking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.chunking-toggle {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

.chunking-advanced {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.chunking-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 0;
}

.strategy-hint {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  margin: var(--spacing-1) 0 0;
}

.checkbox-label {
  display: flex !important;
  flex-direction: row !important;
  align-items: center;
  gap: var(--spacing-2);
  cursor: pointer;
}

.checkbox-label input {
  width: 16px;
  height: 16px;
}

.btn-submit {
  width: 100%;
  padding: var(--spacing-3);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-submit:hover {
  background: var(--color-primary-dark);
}

.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-6);
}
</style>
