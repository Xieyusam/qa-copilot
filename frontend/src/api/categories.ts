import { request } from './request'

export interface Category {
  id: string
  name: string
  description: string | null
  created_at: string
  document_count?: number
}

export interface CategoryCreate {
  name: string
  description?: string
}

export interface CategoryUpdate {
  name?: string
  description?: string
}

/**
 * 获取所有分类列表
 */
export async function getCategories(): Promise<Category[]> {
  const res = await request('/api/admin/categories')
  if (!res.ok) {
    throw new Error('获取分类失败')
  }
  const data = await res.json()
  // 后端直接返回列表
  return Array.isArray(data) ? data : data.categories || []
}

/**
 * 创建新分类
 */
export async function createCategory(data: CategoryCreate): Promise<Category> {
  const res = await request('/api/admin/categories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '创建分类失败')
  }
  return res.json()
}

/**
 * 更新分类
 */
export async function updateCategory(id: string, data: CategoryUpdate): Promise<Category> {
  const res = await request(`/api/admin/categories/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '更新分类失败')
  }
  return res.json()
}

/**
 * 删除分类
 */
export async function deleteCategory(id: string): Promise<void> {
  const res = await request(`/api/admin/categories/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '删除分类失败')
  }
}

/**
 * 移动文档到其他分类
 */
export async function moveDocumentCategory(docId: string, categoryId: string): Promise<void> {
  const res = await request(`/api/documents/${docId}/category`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '移动文档失败')
  }
}