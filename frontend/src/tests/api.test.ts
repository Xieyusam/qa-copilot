/**
 * API 层单元测试 — documents.ts & chat.ts
 * 验证 API 函数正确构造请求并解析响应
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock localStorage for Node.js environment
const localStorageMock = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
vi.stubGlobal('localStorage', localStorageMock)

// ---------------------------------------------------------------------------
// documents API
// ---------------------------------------------------------------------------
describe('documents API', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorageMock.getItem.mockReturnValue(null)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('listDocuments calls GET /api/documents', async () => {
    const mockDocs = [
      { id: '1', filename: 'a.pdf', file_type: 'pdf', file_size: 1024, status: 'ready', uploaded_at: '2024-01-01T00:00:00' },
    ]
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDocs,
    } as Response)

    const { listDocuments } = await import('../api/documents')
    const docs = await listDocuments()

    expect(fetch.mock.calls[0][0]).toBe('/api/documents')
    expect(docs).toHaveLength(1)
    expect(docs[0].id).toBe('1')
    expect(docs[0].fileType).toBe('pdf')
    expect(docs[0].fileSize).toBe(1024)
  })

  it('deleteDocument calls DELETE /api/documents/{id}', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true } as Response)

    const { deleteDocument } = await import('../api/documents')
    await deleteDocument('doc-123')

    expect(fetch.mock.calls[0][0]).toBe('/api/documents/doc-123')
    expect(fetch.mock.calls[0][1].method).toBe('DELETE')
  })

  it('getDocumentStatus returns status fields', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 'doc-1', status: 'ready', error_msg: null }),
    } as Response)

    const { getDocumentStatus } = await import('../api/documents')
    const result = await getDocumentStatus('doc-1')

    expect(result.id).toBe('doc-1')
    expect(result.status).toBe('ready')
    expect(result.errorMsg).toBeNull()
  })

  it('listDocuments throws on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: false, status: 500 } as Response)

    const { listDocuments } = await import('../api/documents')
    await expect(listDocuments()).rejects.toThrow('500')
  })
})

// ---------------------------------------------------------------------------
// chat API
// ---------------------------------------------------------------------------
describe('chat API', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    vi.resetModules()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('listSessions calls GET /api/chat/sessions', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { session_id: 's1', title: '对话1', created_at: '2024-01-01T00:00:00', last_active: '2024-01-01T01:00:00' },
      ],
    } as Response)

    const { listSessions } = await import('../api/chat')
    const sessions = await listSessions()

    expect(fetch.mock.calls[0][0]).toBe('/api/chat/sessions')
    expect(sessions).toHaveLength(1)
    expect(sessions[0].sessionId).toBe('s1')
    expect(sessions[0].title).toBe('对话1')
  })

  it('createSession calls POST /api/chat/sessions and returns sessionId', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ session_id: 'new-session-id' }),
    } as Response)

    const { createSession } = await import('../api/chat')
    const result = await createSession()

    expect(fetch.mock.calls[0][0]).toBe('/api/chat/sessions')
    expect(fetch.mock.calls[0][1].method).toBe('POST')
    expect(result.sessionId).toBe('new-session-id')
  })

  it('deleteSession calls DELETE /api/chat/sessions/{id}', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, status: 204 } as Response)

    const { deleteSession } = await import('../api/chat')
    await deleteSession('s1')

    expect(fetch.mock.calls[0][0]).toBe('/api/chat/sessions/s1')
    expect(fetch.mock.calls[0][1].method).toBe('DELETE')
  })

  it('getMessages returns messages with correct fields', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { role: 'user', content: 'hello', timestamp: '2024-01-01T00:00:00', sources: [] },
        { role: 'assistant', content: 'hi', timestamp: '2024-01-01T00:00:01', sources: [
          { doc_id: 'd1', filename: 'doc.pdf', chunk_position: 0 }
        ]},
      ],
    } as Response)

    const { getMessages } = await import('../api/chat')
    const msgs = await getMessages('s1')

    expect(msgs).toHaveLength(2)
    expect(msgs[0].role).toBe('user')
    expect(msgs[1].role).toBe('assistant')
    expect(msgs[1].sources?.[0].docId).toBe('d1')
    expect(msgs[1].sources?.[0].filename).toBe('doc.pdf')
    expect(msgs[1].sources?.[0].chunkPosition).toBe(0)
  })
})
