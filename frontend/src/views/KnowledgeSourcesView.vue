<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import DocumentList from '../components/DocumentList.vue'
import CategoryManager from '../components/CategoryManager.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { useDocumentStore } from '../stores/documents'
import { useCategoryStore } from '../stores/categories'
import { useAuthStore } from '../stores/auth'
import DocumentUploadPanel from '../components/DocumentUploadPanel.vue'
import type { Category } from '../api/categories'

const store = useDocumentStore()
const categoryStore = useCategoryStore()
const authStore = useAuthStore()
const categoryManagerRef = ref<InstanceType<typeof CategoryManager> | null>(null)

const currentView = ref<'categories' | 'documents'>('categories')
const selectedCategoryId = ref('')
const showUploadModal = ref(false)
const deleteTarget = ref<Category | null>(null)
const deleteError = ref('')

const isAdmin = computed(() => authStore.user?.role === 'admin')

// 当前选中的分类信息
const selectedCategory = computed(() =>
  categoryStore.categories.find(c => c.id === selectedCategoryId.value)
)

// 各分类下的文档数量
const categoryDocCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const doc of store.documents) {
    if (doc.kbCategoryId) {
      counts[doc.kbCategoryId] = (counts[doc.kbCategoryId] || 0) + 1
    }
  }
  return counts
})

// 分类删除
function askDeleteCategory(cat: Category) {
  deleteTarget.value = cat
}

async function confirmDeleteCategory() {
  if (!deleteTarget.value) return
  deleteError.value = ''
  try {
    await categoryStore.removeCategory(deleteTarget.value.id)
    deleteTarget.value = null
  } catch (e: any) {
    deleteError.value = e.message || '删除失败'
  }
}

// 返回分类列表
function goBack() {
  currentView.value = 'categories'
  selectedCategoryId.value = ''
}

// 进入某个分类的文档列表
function enterCategory(categoryId: string) {
  selectedCategoryId.value = categoryId
  currentView.value = 'documents'
}

// 刷新文档列表
async function refreshDocuments() {
  try {
    await store.fetchDocuments()
  } catch (e) {
    console.error('Failed to refresh documents:', e)
  }
}

// 页面加载时获取数据
onMounted(async () => {
  await Promise.all([
    categoryStore.fetchCategories(),
    store.fetchDocuments(),
  ])
})
</script>

<template>
  <div class="docs-layout">
    <!-- 右侧主内容 -->
    <section class="main-panel">
      <!-- ====== 一级视图：分类列表 ====== -->
      <template v-if="currentView === 'categories'">
        <div class="panel-header">
          <div class="header-left">
            <h2 class="panel-title">知识库管理</h2>
          </div>
          <div class="header-actions">
            <span class="doc-count">{{ categoryStore.categories.length }} 个分类</span>
            <button class="btn-create" @click="categoryManagerRef?.openCreateForm()">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              新建分类
            </button>
          </div>
        </div>

        <!-- 分类列表 -->
        <div class="category-list">
          <div
            v-for="cat in categoryStore.categories"
            :key="cat.id"
            class="category-card"
            @click="enterCategory(cat.id)"
          >
            <div class="category-info">
              <span class="category-name">{{ cat.name }}</span>
              <span v-if="cat.description" class="category-desc">{{ cat.description }}</span>
            </div>
            <div class="category-meta">
              <span class="doc-count-badge">{{ categoryDocCounts[cat.id] || 0 }} 个文档</span>
              <div class="card-actions" @click.stop>
                <button
                  class="btn-icon"
                  title="编辑分类"
                  @click="categoryManagerRef?.openEditForm(cat)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                  </svg>
                </button>
                <button
                  class="btn-icon btn-icon-danger"
                  title="删除分类"
                  @click="askDeleteCategory(cat)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="arrow-icon">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="categoryStore.categories.length === 0" class="empty-state">
            <span>暂无分类，请点击「新建分类」创建</span>
          </div>
        </div>
      </template>

      <!-- ====== 二级视图：文档列表 ====== -->
      <template v-else>
        <div class="panel-header">
          <div class="header-left">
            <button class="btn-back" @click="goBack">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
              返回
            </button>
            <h2 class="panel-title">{{ selectedCategory?.name || '文档列表' }}</h2>
          </div>
          <div class="header-actions">
            <span class="doc-count">
              {{ categoryDocCounts[selectedCategoryId] || 0 }} 个文档
            </span>
            <button class="btn-refresh" @click="refreshDocuments" title="刷新文档列表">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
              刷新
            </button>
            <DocumentUploadPanel
              :open="showUploadModal"
              :default-category-id="selectedCategoryId"
              @open="showUploadModal = true"
              @close="showUploadModal = false"
              @uploaded="refreshDocuments()"
            />
          </div>
        </div>

        <!-- 文档列表（按当前分类筛选） -->
        <div class="panel-content">
          <DocumentList :filter-category-id="selectedCategoryId" @refresh="refreshDocuments()" />
        </div>
      </template>
    </section>

    <!-- 分类管理弹窗（管理员） -->
    <CategoryManager
      v-if="isAdmin"
      ref="categoryManagerRef"
    />

    <!-- 分类删除确认 -->
    <ConfirmDialog
      v-if="deleteTarget"
      title="删除分类"
      :message="deleteError || `确定要删除分类「${deleteTarget.name}」吗？此操作不可恢复。`"
      confirmText="删除"
      :loading="categoryStore.loading"
      @confirm="confirmDeleteCategory"
      @cancel="deleteTarget = null; deleteError = ''"
    />
  </div>
</template>

<style scoped>
.docs-layout {
  height: 100%;
  padding: var(--spacing-5);
  overflow: hidden;
}

.main-panel {
  height: 100%;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-header {
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  background: var(--color-bg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.panel-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.doc-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

/* ====== 分类列表（一级视图） ====== */
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
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.category-card:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-hover);
}

.category-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.category-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.category-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.card-actions {
  display: flex;
  gap: var(--spacing-1);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.category-card:hover .card-actions {
  opacity: 1;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.btn-icon:hover {
  background: var(--color-primary-bg);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-icon-danger:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error-light);
  color: var(--color-error);
}

.doc-count-badge {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-hover);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
}

.arrow-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* ====== 返回按钮 ====== */
.btn-back {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-back:hover {
  color: var(--color-text);
  border-color: var(--color-text-secondary);
}

/* ====== 新建按钮 ====== */
.btn-create {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-create:hover {
  background: var(--color-primary-dark);
}

/* ====== 刷新按钮 ====== */
.btn-refresh {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-refresh:hover {
  color: var(--color-text);
  border-color: var(--color-text-secondary);
}

/* ====== 文档内容区 ====== */
.panel-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.panel-content > :deep(.doc-list) {
  height: 100%;
}
</style>
