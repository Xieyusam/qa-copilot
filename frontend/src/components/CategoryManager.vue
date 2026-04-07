<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCategoryStore } from '../stores/categories'
import ConfirmDialog from './ConfirmDialog.vue'
import type { Category } from '../api/categories'

const store = useCategoryStore()

const showCreateForm = ref(false)
const editingCategory = ref<Category | null>(null)
const deleteTarget = ref<Category | null>(null)
const formName = ref('')
const formDescription = ref('')
const formLoading = ref(false)
const formError = ref('')
const toastMessage = ref('')
const showToast = ref(false)

function displayToast(msg: string) {
  toastMessage.value = msg
  showToast.value = true
  setTimeout(() => {
    showToast.value = false
  }, 2500)
}

function openEditForm(category: Category) {
  editingCategory.value = category
  formName.value = category.name
  formDescription.value = category.description || ''
  formError.value = ''
}

function openCreateForm() {
  formName.value = ''
  formDescription.value = ''
  formError.value = ''
  showCreateForm.value = true
}

defineExpose({ openCreateForm })

function closeForm() {
  showCreateForm.value = false
  editingCategory.value = null
  formName.value = ''
  formDescription.value = ''
  formError.value = ''
}

async function handleCreate() {
  if (!formName.value.trim()) {
    formError.value = '请输入分类名称'
    return
  }

  formLoading.value = true
  formError.value = ''

  try {
    await store.addCategory({
      name: formName.value.trim(),
      description: formDescription.value.trim() || undefined,
    })
    displayToast('分类创建成功')
    closeForm()
  } catch (e: any) {
    formError.value = e.message || '创建失败'
  } finally {
    formLoading.value = false
  }
}

async function handleUpdate() {
  if (!editingCategory.value) return
  if (!formName.value.trim()) {
    formError.value = '请输入分类名称'
    return
  }

  formLoading.value = true
  formError.value = ''

  try {
    await store.editCategory(editingCategory.value.id, {
      name: formName.value.trim(),
      description: formDescription.value.trim() || undefined,
    })
    displayToast('分类更新成功')
    closeForm()
  } catch (e: any) {
    formError.value = e.message || '更新失败'
  } finally {
    formLoading.value = false
  }
}

function askDelete(category: Category) {
  deleteTarget.value = category
}

async function confirmDelete() {
  if (!deleteTarget.value) return

  try {
    await store.removeCategory(deleteTarget.value.id)
    displayToast('分类删除成功')
  } catch (e: any) {
    displayToast(e.message || '删除失败')
  } finally {
    deleteTarget.value = null
  }
}

onMounted(async () => {
  try {
    await store.fetchCategories()
  } catch (e) {
    console.error('Failed to load categories:', e)
  }
})
</script>

<template>
  <div class="category-manager">
    <!-- Category List -->
    <div class="category-list">
      <div
        v-for="category in store.categories"
        :key="category.id"
        class="category-card"
      >
        <div class="category-info">
          <div class="category-name">{{ category.name }}</div>
          <div v-if="category.description" class="category-desc">{{ category.description }}</div>
        </div>
        <div class="category-meta">
          <span class="doc-count">{{ category.document_count ?? 0 }} 个文档</span>
        </div>
        <div class="category-actions">
          <button class="btn-icon" @click="openEditForm(category)" title="编辑">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
            </svg>
          </button>
          <button
            class="btn-icon btn-delete"
            :disabled="(category.document_count ?? 0) > 0"
            :title="(category.document_count ?? 0) > 0 ? '该分类下有文档，无法删除' : '删除'"
            @click="askDelete(category)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="store.categories.length === 0 && !store.loading" class="empty-state">
        <div class="empty-icon">📁</div>
        <p>暂无分类</p>
      </div>

      <div v-if="store.loading" class="loading-state">
        <div class="spinner"></div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div v-if="showCreateForm || editingCategory" class="modal-overlay" @click="closeForm">
        <div class="modal" @click.stop>
          <div class="modal-header">
            <h3>{{ editingCategory ? '编辑分类' : '新建分类' }}</h3>
            <button class="btn-close" @click="closeForm">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">分类名称 *</label>
              <input
                v-model="formName"
                type="text"
                class="form-input"
                placeholder="输入分类名称"
                maxlength="50"
              >
            </div>
            <div class="form-group">
              <label class="form-label">分类描述</label>
              <textarea
                v-model="formDescription"
                class="form-input form-textarea"
                placeholder="输入分类描述（可选）"
                rows="3"
                maxlength="200"
              ></textarea>
            </div>
            <p v-if="formError" class="form-error">{{ formError }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="closeForm">取消</button>
            <button
              class="btn-primary"
              :disabled="formLoading"
              @click="editingCategory ? handleUpdate() : handleCreate()"
            >
              <span v-if="formLoading" class="btn-spinner"></span>
              <span v-else>{{ editingCategory ? '保存' : '创建' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      v-if="deleteTarget"
      title="删除分类"
      :message="`确定要删除分类「${deleteTarget.name}」吗？此操作不可恢复。`"
      confirmText="删除"
      :loading="store.loading"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />

    <!-- Toast -->
    <Teleport to="body">
      <div v-if="showToast" class="toast">
        {{ toastMessage }}
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.category-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.category-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.category-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-5);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.category-card:hover {
  border-color: var(--color-border-dark);
  box-shadow: var(--shadow-sm);
}

.category-info {
  flex: 1;
  min-width: 0;
}

.category-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.category-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-1);
}

.category-meta {
  margin: 0 var(--spacing-4);
}

.doc-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
}

.category-actions {
  display: flex;
  gap: var(--spacing-2);
}

.btn-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary-light);
  color: var(--color-primary);
}

.btn-icon.btn-delete:hover:not(:disabled) {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-15);
  gap: var(--spacing-3);
}

.empty-icon { font-size: 40px; }

.empty-state p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-8);
  color: var(--color-text-muted);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  width: 400px;
  max-width: 90vw;
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
  font-size: var(--font-size-xl);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.btn-close:hover {
  color: var(--color-text);
}

.modal-body {
  padding: var(--spacing-5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.form-input {
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text);
  background: var(--color-bg-card);
  outline: none;
  transition: border-color var(--transition-fast);
}

.form-input::placeholder {
  color: var(--color-text-muted);
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin: 0;
}

.modal-footer {
  padding: var(--spacing-4) var(--spacing-5);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}

.btn-secondary {
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  background: var(--color-bg);
  border-color: var(--color-border-dark);
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-inverse);
  cursor: pointer;
  min-width: 80px;
  transition: background var(--transition-fast);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
}

/* Toast */
.toast {
  position: fixed;
  bottom: var(--spacing-6);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--spacing-3) var(--spacing-5);
  background: var(--color-text);
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  box-shadow: var(--shadow-lg);
  z-index: 9999;
  animation: fadeUp 0.3s ease-out;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translate(-50%, 10px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
</style>