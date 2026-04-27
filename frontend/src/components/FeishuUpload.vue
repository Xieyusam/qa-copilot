<script setup lang="ts">
import { ref } from 'vue'
import { useCategoryStore } from '../stores/categories'
import { createFeishuDocument, listFeishuDocuments, type FeishuDocumentCreate } from '../api/feishu'

const props = defineProps<{
  open?: boolean
  defaultCategoryId?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const categoryStore = useCategoryStore()
const localError = ref('')
const submitting = ref(false)
const justSubmitted = ref(false)

const formUrl = ref('')
const formType = ref('doc')
const formTitle = ref('')
const selectedCategory = ref('')

const STRATEGIES = [
  { value: 'recursive_text', label: '递归文本切分（通用）' },
  { value: 'semantic', label: '语义切分（AI 边界检测）' },
  { value: 'sentence', label: '句子切分（正则标点）' },
  { value: 'sliding_window', label: '滑动窗口（固定 token 重叠）' },
  { value: 'markdown', label: 'Markdown 切分（保留标题结构）' },
  { value: 'excel', label: 'Excel 切分（保持表格结构）' },
]

const formChunkingStrategy = ref('recursive_text')
const syncEnabled = ref(true)
const syncIntervalHours = ref(24)

async function loadCategories() {
  if (categoryStore.categories.length === 0) {
    try {
      await categoryStore.fetchCategories()
    } catch (e) {
      console.error('Failed to load categories:', e)
    }
  }
}

function onOpen(categoryId?: string) {
  selectedCategory.value = categoryId || props.defaultCategoryId || ''
  loadCategories()
  localError.value = ''
  justSubmitted.value = false
  formUrl.value = ''
  formType.value = 'doc'
  formTitle.value = ''
  formChunkingStrategy.value = 'recursive_text'
  syncEnabled.value = true
  syncIntervalHours.value = 24
}

function validate(): string {
  if (!formUrl.value.trim()) return '请输入飞书文档链接'
  if (!formUrl.value.includes('feishu.cn') && !formUrl.value.includes('larksuite.com')) {
    return '请输入有效的飞书文档链接'
  }
  if (!formTitle.value.trim()) return '请输入文档标题'
  if (!selectedCategory.value) {
    // 自动选择第一个可用分类
    if (categoryStore.categories.length > 0) {
      selectedCategory.value = categoryStore.categories[0].id
    } else {
      return '请先创建知识库分类'
    }
  }
  return ''
}

async function handleSubmit() {
  localError.value = ''
  const err = validate()
  if (err) { localError.value = err; return }

  submitting.value = true
  try {
    const data: FeishuDocumentCreate = {
      feishu_doc_url: formUrl.value.trim(),
      feishu_doc_type: formType.value,
      title: formTitle.value.trim(),
      kb_category_id: selectedCategory.value,
      is_active: true,
      sync_interval_hours: syncEnabled.value ? syncIntervalHours.value : -1,
    }
    await createFeishuDocument(data)

    // 轮询飞书文档同步状态，直到非 pending
    const pollInterval = setInterval(async () => {
      try {
        const docs = await listFeishuDocuments()
        const updated = docs.find(d => d.feishu_doc_url === formUrl.value.trim())
        if (updated && updated.last_sync_status !== 'pending') {
          clearInterval(pollInterval)
          if (updated.last_sync_status === 'failed') {
            localError.value = `同步失败: ${updated.last_sync_error || '飞书 API 未配置'}`
          } else if (updated.last_sync_status === 'success') {
            justSubmitted.value = true
            setTimeout(() => {
              justSubmitted.value = false
              emit('close')
            }, 1500)
          }
        }
      } catch {
        // ignore polling errors
      }
    }, 2000)
    // 最多轮询 30 秒
    setTimeout(() => clearInterval(pollInterval), 30000)
  } catch (e: any) {
    localError.value = e?.message || '注册失败'
  } finally {
    submitting.value = false
  }
}

defineExpose({ onOpen })
</script>

<template>
  <Teleport to="body">
    <div v-if="props.open" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-card">
        <div class="modal-header">
          <h3>注册飞书文档</h3>
          <button class="btn-close" @click="emit('close')">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <div v-if="justSubmitted" class="success-state">
            <div class="success-icon">✓</div>
            <p class="success-text">注册成功</p>
          </div>

          <template v-else>
            <div class="form-item">
              <label>飞书文档链接</label>
              <input
                v-model="formUrl"
                type="text"
                class="form-input"
                placeholder="https://feishu.cn/docx/xxx"
              >
            </div>

            <div class="form-item">
              <label>文档标题</label>
              <input
                v-model="formTitle"
                type="text"
                class="form-input"
                placeholder="给文档起一个名称"
              >
            </div>

            <div class="form-item">
              <label>文档类型</label>
              <select v-model="formType" class="form-input">
                <option value="doc">文档 (Doc)</option>
                <option value="sheet">表格 (Sheet)</option>
                <option value="bitable">多维表格 (Bitable)</option>
              </select>
            </div>

            <div class="form-item">
              <label>分片策略</label>
              <select v-model="formChunkingStrategy" class="form-input">
                <option v-for="s in STRATEGIES" :key="s.value" :value="s.value">
                  {{ s.label }}
                </option>
              </select>
            </div>

            <div class="form-item">
              <label class="checkbox-label">
                <input type="checkbox" v-model="syncEnabled">
                开启定时更新
              </label>
            </div>

            <template v-if="syncEnabled">
              <div class="form-item">
                <label>更新间隔（小时）</label>
                <input v-model.number="syncIntervalHours" type="number" class="form-input" min="1" max="168">
              </div>
            </template>

            <p v-if="localError" class="error-msg">{{ localError }}</p>

            <p class="form-hint">
              <span>支持 docx、sheet、bitable 格式</span>
            </p>

            <button
              class="btn-submit"
              :disabled="submitting"
              @click="handleSubmit"
            >
              <span v-if="submitting" class="spinner-sm"></span>
              <span v-else>确认注册</span>
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
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
  width: 420px;
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

.form-input {
  width: 100%;
  padding: var(--spacing-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background: var(--color-bg);
  color: var(--color-text);
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.form-row {
  display: flex;
  gap: var(--spacing-4);
}

.form-row .form-item {
  flex: 1;
}

.error-msg {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin: 0;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
}

.form-hint {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 0;
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
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-submit:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-6);
}

.success-icon {
  font-size: 40px;
  color: var(--color-success);
}

.success-text {
  color: var(--color-success);
  font-weight: var(--font-weight-medium);
  margin: 0;
}
</style>
