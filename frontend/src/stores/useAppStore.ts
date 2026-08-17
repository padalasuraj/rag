import { create } from 'zustand'
import { api } from '@/services/api'
import type { Health, KnowledgeBase } from '@/types'

export interface Toast {
  id: number
  message: string
  variant: 'success' | 'error' | 'info'
}

interface AppState {
  knowledgeBases: KnowledgeBase[]
  loadingKbs: boolean
  health: Health | null
  toasts: Toast[]
  createKbOpen: boolean

  fetchHealth: () => Promise<void>
  fetchKnowledgeBases: () => Promise<void>
  createKnowledgeBase: (name: string, description?: string) => Promise<KnowledgeBase>
  deleteKnowledgeBase: (id: string) => Promise<void>

  openCreateKb: () => void
  closeCreateKb: () => void

  toast: (message: string, variant?: Toast['variant']) => void
  dismissToast: (id: number) => void
}

let toastId = 0

export const useAppStore = create<AppState>((set, get) => ({
  knowledgeBases: [],
  loadingKbs: false,
  health: null,
  toasts: [],
  createKbOpen: false,

  openCreateKb: () => set({ createKbOpen: true }),
  closeCreateKb: () => set({ createKbOpen: false }),

  fetchHealth: async () => {
    try {
      const health = await api.health()
      set({ health })
    } catch {
      set({ health: null })
    }
  },

  fetchKnowledgeBases: async () => {
    set({ loadingKbs: true })
    try {
      const kbs = await api.listKnowledgeBases()
      set({ knowledgeBases: kbs })
    } catch (e: any) {
      get().toast(e.message || 'Could not load knowledge bases.', 'error')
    } finally {
      set({ loadingKbs: false })
    }
  },

  createKnowledgeBase: async (name, description = '') => {
    const kb = await api.createKnowledgeBase(name, description)
    set({ knowledgeBases: [kb, ...get().knowledgeBases] })
    return kb
  },

  deleteKnowledgeBase: async (id) => {
    await api.deleteKnowledgeBase(id)
    set({ knowledgeBases: get().knowledgeBases.filter((k) => k.id !== id) })
  },

  toast: (message, variant = 'info') => {
    const id = ++toastId
    set({ toasts: [...get().toasts, { id, message, variant }] })
    setTimeout(() => get().dismissToast(id), 4200)
  },

  dismissToast: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}))
