import { AnimatePresence } from 'framer-motion'
import { Database, Plus, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { KnowledgeBaseCard } from '@/components/dashboard/KnowledgeBaseCard'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Spinner } from '@/components/ui/Spinner'
import { useAppStore } from '@/stores/useAppStore'
import type { KnowledgeBase } from '@/types'

export function DashboardPage() {
  const knowledgeBases = useAppStore((s) => s.knowledgeBases)
  const loadingKbs = useAppStore((s) => s.loadingKbs)
  const fetchKnowledgeBases = useAppStore((s) => s.fetchKnowledgeBases)
  const deleteKnowledgeBase = useAppStore((s) => s.deleteKnowledgeBase)
  const openCreateKb = useAppStore((s) => s.openCreateKb)
  const toast = useAppStore((s) => s.toast)

  const [pendingDelete, setPendingDelete] = useState<KnowledgeBase | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchKnowledgeBases()
  }, [fetchKnowledgeBases])

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteKnowledgeBase(pendingDelete.id)
      toast(`Deleted “${pendingDelete.name}”.`, 'success')
      setPendingDelete(null)
    } catch (e: any) {
      toast(e.message || 'Could not delete knowledge base.', 'error')
    } finally {
      setDeleting(false)
    }
  }

  const isEmpty = !loadingKbs && knowledgeBases.length === 0

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Knowledge bases
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Group your sources, then chat with an assistant grounded in them.
          </p>
        </div>
        <button className="btn-primary" onClick={openCreateKb}>
          <Plus className="h-4 w-4" />
          New knowledge base
        </button>
      </div>

      {loadingKbs && knowledgeBases.length === 0 && (
        <div className="flex items-center justify-center gap-3 py-24 text-ink-muted">
          <Spinner className="h-5 w-5" />
          Loading your knowledge bases…
        </div>
      )}

      {isEmpty && (
        <div className="card mt-8 flex flex-col items-center px-6 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-grad-accent-soft">
            <Database className="h-6 w-6 text-accent" />
          </div>
          <h2 className="mt-4 font-display text-lg font-semibold">
            Create your first knowledge base
          </h2>
          <p className="mt-1.5 max-w-md text-sm text-ink-muted">
            Add PDFs, YouTube videos, or pasted text. NexusRAG indexes them so you can
            ask questions and get answers with citations back to the exact source.
          </p>
          <button className="btn-primary mt-6" onClick={openCreateKb}>
            <Sparkles className="h-4 w-4" />
            Get started
          </button>
        </div>
      )}

      {!isEmpty && (
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {knowledgeBases.map((kb) => (
              <KnowledgeBaseCard key={kb.id} kb={kb} onDelete={setPendingDelete} />
            ))}
          </AnimatePresence>
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        destructive
        busy={deleting}
        title="Delete knowledge base?"
        message={
          pendingDelete
            ? `“${pendingDelete.name}” and all of its sources, chunks, and chat history will be permanently removed. This cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        onConfirm={confirmDelete}
        onClose={() => !deleting && setPendingDelete(null)}
      />
    </div>
  )
}
