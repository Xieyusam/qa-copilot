import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  type Category,
  type CategoryCreate,
  type CategoryUpdate,
} from '../api/categories'

export const useCategoryStore = defineStore('categories', () => {
  const categories = ref<Category[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * 加载分类列表
   */
  async function fetchCategories() {
    loading.value = true
    error.value = null
    try {
      categories.value = await getCategories()
    } catch (e: any) {
      error.value = e?.message || '加载分类失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建分类
   */
  async function addCategory(data: CategoryCreate) {
    loading.value = true
    error.value = null
    try {
      const newCategory = await createCategory(data)
      categories.value.push(newCategory)
      return newCategory
    } catch (e: any) {
      error.value = e?.message || '创建分类失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新分类
   */
  async function editCategory(id: string, data: CategoryUpdate) {
    loading.value = true
    error.value = null
    try {
      const updated = await updateCategory(id, data)
      const index = categories.value.findIndex(c => c.id === id)
      if (index !== -1) {
        categories.value[index] = updated
      }
      return updated
    } catch (e: any) {
      error.value = e?.message || '更新分类失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除分类
   */
  async function removeCategory(id: string) {
    loading.value = true
    error.value = null
    try {
      await deleteCategory(id)
      categories.value = categories.value.filter(c => c.id !== id)
    } catch (e: any) {
      error.value = e?.message || '删除分类失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 根据ID获取分类名称
   */
  function getCategoryName(id: string): string {
    const cat = categories.value.find(c => c.id === id)
    return cat?.name || id
  }

  return {
    categories,
    loading,
    error,
    fetchCategories,
    addCategory,
    editCategory,
    removeCategory,
    getCategoryName,
  }
})