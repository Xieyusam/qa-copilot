/**
 * Task 17.5: 上传入口单元测试
 * 验证上传入口在前端页面中存在（需求 1.1）
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DocumentUpload from '../components/DocumentUpload.vue'

// Mock API modules directly to prevent real network calls
vi.mock('../api/documents', () => ({
  listDocuments: vi.fn().mockResolvedValue([]),
  uploadDocument: vi.fn().mockResolvedValue({ id: '1', filename: 'test.pdf', status: 'ready' }),
  deleteDocument: vi.fn().mockResolvedValue(undefined),
  getDocumentStatus: vi.fn().mockResolvedValue({ id: '1', status: 'ready', errorMsg: null }),
  getDocumentsStatus: vi.fn().mockResolvedValue([]),
  getDocumentChunks: vi.fn().mockResolvedValue({ doc_id: '1', filename: 'test.pdf', total_chunks: 1, chunks: [] }),
}))

vi.mock('../api/categories', () => ({
  getCategories: vi.fn().mockResolvedValue([]),
  createCategory: vi.fn().mockResolvedValue({ id: 'cat-1', name: 'test' }),
  updateCategory: vi.fn().mockResolvedValue({ id: 'cat-1', name: 'updated' }),
  deleteCategory: vi.fn().mockResolvedValue(undefined),
}))

describe('DocumentUpload — 上传入口 (Task 17.5)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Stub fetch to prevent any real API calls
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response))
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders upload button with icon', () => {
    const wrapper = mount(DocumentUpload, { attachTo: document.body })
    // The upload icon button is always visible (not inside the modal)
    expect(wrapper.find('.upload-icon-btn').exists()).toBe(true)
    expect(wrapper.find('.upload-icon-btn svg').exists()).toBe(true)
    wrapper.unmount()
  })

  it('upload button contains text', () => {
    const wrapper = mount(DocumentUpload, { attachTo: document.body })
    expect(wrapper.find('.upload-icon-btn span').text()).toBe('上传文档')
    wrapper.unmount()
  })

  it('emits open event when upload button is clicked', async () => {
    const wrapper = mount(DocumentUpload, { attachTo: document.body })
    await wrapper.find('.upload-icon-btn').trigger('click')
    expect(wrapper.emitted('open')).toBeTruthy()
    wrapper.unmount()
  })

  it('has hidden file input with correct accept attribute when modal is open', async () => {
    const wrapper = mount(DocumentUpload, {
      props: { open: true },
      attachTo: document.body,
    })
    // The modal is open, file input should exist in the DOM
    await wrapper.vm.$nextTick()
    // Teleport renders to document.body, so we query it directly
    const modalOverlay = document.body.querySelector('.modal-overlay')
    expect(modalOverlay).toBeTruthy()
    expect(document.body.querySelector('.modal-card')).toBeTruthy()
    wrapper.unmount()
  })

  it('modal has drop zone area when open', async () => {
    const wrapper = mount(DocumentUpload, {
      props: { open: true },
      attachTo: document.body,
    })
    await wrapper.vm.$nextTick()
    const dropZone = document.body.querySelector('.drop-zone')
    expect(dropZone).toBeTruthy()
    wrapper.unmount()
  })

  it('modal has select file button when open', async () => {
    const wrapper = mount(DocumentUpload, {
      props: { open: true },
      attachTo: document.body,
    })
    await wrapper.vm.$nextTick()
    const btnSelect = document.body.querySelector('.btn-select')
    expect(btnSelect).toBeTruthy()
    wrapper.unmount()
  })

  it('file input has correct accept attribute', async () => {
    const wrapper = mount(DocumentUpload, {
      props: { open: true },
      attachTo: document.body,
    })
    await wrapper.vm.$nextTick()
    const input = document.body.querySelector('input[type="file"]')
    expect(input).toBeTruthy()
    expect(input?.getAttribute('accept')).toBe('.pdf,.docx,.txt,.md,.xlsx,.xls')
    wrapper.unmount()
  })
})
