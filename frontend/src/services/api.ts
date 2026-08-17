import type {
  Analytics,
  Citation,
  ChatMessage,
  Health,
  KnowledgeBase,
  QuizResponse,
  Source,
  SourceType,
} from '@/types'

// Same-origin by default: the Vite dev server and the nginx prod build both
// proxy /api to the backend, so relative URLs work everywhere (incl. SSE).
export const API_BASE = import.meta.env.VITE_API_URL || '/api'

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(detail, res.status)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** Build a deep link to a PDF page for a citation. */
export function pdfFileUrl(sourceId: string, page?: number | null): string {
  const base = `${API_BASE}/sources/${sourceId}/file`
  return page ? `${base}#page=${page}` : base
}

export interface StreamHandlers {
  onCitations?: (citations: Citation[], grounded: boolean) => void
  onToken?: (text: string) => void
  onDone?: (relatedQuestions: string[], latencyMs: number) => void
  onError?: (message: string) => void
}

/**
 * Stream a grounded answer over server-sent events. Parses the `data: {json}`
 * protocol emitted by the backend's rag_service.answer_stream.
 */
export async function streamChat(
  payload: {
    knowledge_base_id: string
    question: string
    source_type_filter?: 'all' | SourceType
  },
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  })

  if (!res.ok || !res.body) {
    handlers.onError?.('The assistant is unavailable right now. Please try again.')
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE events are separated by a blank line.
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const evt of events) {
      const line = evt.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      const jsonStr = line.slice('data:'.length).trim()
      if (!jsonStr) continue
      let data: any
      try {
        data = JSON.parse(jsonStr)
      } catch {
        continue
      }
      switch (data.type) {
        case 'citations':
          handlers.onCitations?.(data.citations || [], data.grounded)
          break
        case 'token':
          handlers.onToken?.(data.text || '')
          break
        case 'done':
          handlers.onDone?.(data.related_questions || [], data.latency_ms || 0)
          break
        case 'error':
          handlers.onError?.(data.message || 'Something went wrong.')
          break
      }
    }
  }
}

export const api = {
  health: () => request<Health>('/health'),

  // Knowledge bases
  listKnowledgeBases: () => request<KnowledgeBase[]>('/knowledge-bases'),
  getKnowledgeBase: (id: string) => request<KnowledgeBase>(`/knowledge-bases/${id}`),
  createKnowledgeBase: (name: string, description = '') =>
    request<KnowledgeBase>('/knowledge-bases', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),
  updateKnowledgeBase: (id: string, patch: { name?: string; description?: string }) =>
    request<KnowledgeBase>(`/knowledge-bases/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
  deleteKnowledgeBase: (id: string) =>
    request<void>(`/knowledge-bases/${id}`, { method: 'DELETE' }),

  // Sources
  listSources: (kbId: string) =>
    request<Source[]>(`/sources?knowledge_base_id=${kbId}`),
  getSource: (id: string) => request<Source>(`/sources/${id}`),
  addYouTube: (knowledge_base_id: string, url: string) =>
    request<Source>('/sources/youtube', {
      method: 'POST',
      body: JSON.stringify({ knowledge_base_id, url }),
    }),
  addText: (knowledge_base_id: string, title: string, content: string) =>
    request<Source>('/sources/text', {
      method: 'POST',
      body: JSON.stringify({ knowledge_base_id, title, content }),
    }),
  addPdf: async (knowledge_base_id: string, file: File): Promise<Source> => {
    const form = new FormData()
    form.append('knowledge_base_id', knowledge_base_id)
    form.append('file', file)
    const res = await fetch(`${API_BASE}/sources/pdf`, { method: 'POST', body: form })
    if (!res.ok) {
      let detail = 'Upload failed.'
      try {
        detail = (await res.json()).detail || detail
      } catch {
        /* ignore */
      }
      throw new ApiError(detail, res.status)
    }
    return res.json()
  },
  reindexSource: (id: string) =>
    request<Source>(`/sources/${id}/reindex`, { method: 'POST' }),
  deleteSource: (id: string) => request<void>(`/sources/${id}`, { method: 'DELETE' }),

  // Chat history
  chatHistory: (kbId: string) => request<ChatMessage[]>(`/chat/${kbId}/history`),
  clearHistory: (kbId: string) =>
    request<void>(`/chat/${kbId}/history`, { method: 'DELETE' }),

  // AI features
  summarize: (source_id: string, mode: 'summary' | 'key_points' | 'eli5') =>
    request<{ mode: string; result: string }>('/summarize', {
      method: 'POST',
      body: JSON.stringify({ source_id, mode }),
    }),
  quiz: (knowledge_base_id: string, source_id: string | null, num_questions = 5) =>
    request<QuizResponse>('/quiz', {
      method: 'POST',
      body: JSON.stringify({ knowledge_base_id, source_id, num_questions }),
    }),

  // Analytics
  analytics: (kbId: string) => request<Analytics>(`/analytics/${kbId}`),
}

export { ApiError }
