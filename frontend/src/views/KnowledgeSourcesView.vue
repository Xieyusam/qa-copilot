<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DocumentList from '../components/DocumentList.vue'
import CategoryManager from '../components/CategoryManager.vue'
import CategorySelect from '../components/CategorySelect.vue'
import { useDocumentStore } from '../stores/documents'
import { useCategoryStore } from '../stores/categories'
import { useAuthStore } from '../stores/auth'
import DocumentUpload from '../components/DocumentUpload.vue'

const store = useDocumentStore()
const categoryStore = useCategoryStore()
const authStore = useAuthStore()
const categoryManagerRef = ref<InstanceType<typeof CategoryManager> | null>(null)

const activeTab = ref<'documents' | 'categories'>('documents')
const showUploadModal = ref(false)
const filterCategoryId = ref('')

const isAdmin = computed(() => authStore.user?.role === 'admin')

// 切换 Tab 时重置筛选
watch(activeTab, (tab) => {
  if (tab === 'documents') {
    // 文档 Tab 不重置筛选
  } else {
    filterCategoryId.value = ''
  }
})

const filteredCount = computed(() => {
  if (!filterCategoryId.value) return store.documents.length
  return store.documents.filter(d => d.kbCategory === filterCategoryId.value).length
})
</script>

<template>
  <div class="docs-layout">
    <!-- 右侧主内容 -->
    <section class="main-panel">
      <div class="panel-header">
        <div class="header-left">
          <h2 class="panel-title">知识库管理</h2>
          <!-- Admin Tabs -->
          <div v-if="isAdmin" class="tabs">
            <button
              :class="['tab-btn', { active: activeTab === 'documents' }]"
              @click="activeTab = 'documents'"
            >
              文档
            </button>
            <button
              :class="['tab-btn', { active: activeTab === 'categories' }]"
              @click="activeTab = 'categories'"
            >
              分类
            </button>
          </div>
        </div>
        <div class="header-actions">
          <template v-if="activeTab === 'documents'">
            <span class="doc-count">{{ filteredCount }} 个文档</span>
            <CategorySelect
              v-model="filterCategoryId"
              placeholder="全部分类"
              class="header-filter-select"
            />
            <button
              v-if="filterCategoryId"
              class="btn-clear-filter"
              @click="filterCategoryId = ''"
            >
              ×
            </button>
            <DocumentUpload :open="showUploadModal" @open="showUploadModal = true" @close="showUploadModal = false" />
          </template>
          <template v-else>
            <span class="doc-count">{{ categoryStore.categories.length }} 个分类</span>
            <button class="btn-create" @click="categoryManagerRef?.openCreateForm()">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              新建分类
            </button>
          </template>
        </div>
      </div>

      <!-- Content -->
      <div class="panel-content">
        <DocumentList v-if="activeTab === 'documents'" :filter-category-id="filterCategoryId" />
        <CategoryManager v-else-if="activeTab === 'categories'" ref="categoryManagerRef" />
      </div>
    </section>
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
  gap: var(--spacing-5);
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

.header-filter-select {
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
  flex-shrink: 0;
}

.btn-clear-filter:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
}

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

.tabs {
  display: flex;
  gap: var(--spacing-1);
  background: var(--color-bg-hover);
  padding: var(--spacing-1);
  border-radius: var(--radius-md);
}

.tab-btn {
  padding: var(--spacing-2) var(--spacing-4);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn.active {
  background: var(--color-bg-card);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.panel-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.panel-content > :deep(.doc-list) {
  height: 100%;
}
</style>