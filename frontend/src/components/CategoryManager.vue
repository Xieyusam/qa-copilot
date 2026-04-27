<script setup lang="ts">
import { ref } from 'vue'
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

// 打开编辑弹窗（从模板调用）
function openEditForm(category: Category) {
  editingCategory.value = category
  formName.value = category.name
  formDescription.value = category.description || ''
  formError.value = ''
}

function openCreateForm() {
  editingCategory.value = null
  formName.value = ''
  formDescription.value = ''
  formError.value = ''
  showCreateForm.value = true
}

defineExpose({ openCreateForm, openEditForm })

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

async function confirmDelete() {
  if (!deleteTarget.value) return

  try {
    await store.removeCategory(deleteTarget.value.id)
    displayToast('分类删除成功')
    closeForm()
  } catch (e: any) {
    displayToast(e.message || '删除失败')
  } finally {
    deleteTarget.value = null
  }
}

function askDelete() {
  if (!editingCategory.value) return
  deleteTarget.value = editingCategory.value
}
</script>

<template>
  <div class="category-manager">
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
                rows="2"
                maxlength="200"
              ></textarea>
            </div>

            <p v-if="formError" class="form-error">{{ formError }}</p>
          </div>
          <div class="modal-footer">
            <button
              v-if="editingCategory"
              class="btn-danger"
              :disabled="formLoading"
              @click="askDelete()"
            >
              <span v-if="formLoading" class="btn-spinner"></span>
              <span v-else>删除</span>
            </button>
            <div class="footer-right">
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
  width: 440px;
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
  min-height: 60px;
}

.form-row {
  display: flex;
  gap: var(--spacing-4);
}

.form-row .form-group {
  flex: 1;
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
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-3);
}

.footer-right {
  display: flex;
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

.btn-danger {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-light);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-error);
  cursor: pointer;
  min-width: 80px;
  transition: all var(--transition-fast);
}

.btn-danger:hover:not(:disabled) {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

.btn-danger:disabled {
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

@keyframes spin {
  to { transform: rotate(360deg); }
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