import { motion } from 'framer-motion'
import {
  ArrowLeft,
  BarChart3,
  FileText,
  GraduationCap,
  Layers,
  MessageSquare,
  Type,
  Youtube,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AnalyticsPanel } from '@/components/kb/AnalyticsPanel'
import { ChatPanel } from '@/components/kb/ChatPanel'
import { QuizPanel } from '@/components/kb/QuizPanel'
import { SourcesPanel } from '@/components/kb/SourcesPanel'
import { Spinner } from '@/components/ui/Spinner'
import { Tabs, type TabItem } from '@/components/ui/Tabs'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/useAppStore'
import type { KnowledgeBase } from '@/types'

type TabId = 'sources' | 'chat' | 'quiz' | 'analytics'

export function KnowledgeBasePage() {
  const { id = '' } = useParams()
  const toast = useAppStore((s) => s.toast)
  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [tab, setTab] = useState<TabId>('sources')

  const loadKb = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      try {
        const data = await api.getKnowledgeBase(id)
        setKb(data)
        setNotFound(false)
      } catch (e: any) {
        if (e.status === 404) setNotFound(true)
        else toast(e.message || 'Could not load knowledge base.', 'error')
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [id, toast],
  )

  useEffect(() => {
    loadKb()
  }, [loadKb])

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-ink-muted">
        <Spinner className="h-5 w-5" />
        Loading knowledge base…
      </div>
    )
  }

  if (notFound || !kb) {
    return (
      <div className="mx-auto max-w-md px-5 py-24 text-center">
        <h2 className="font-display text-lg font-semibold">Knowledge base not found</h2>
        <p className="mt-1.5 text-sm text-ink-muted">
          It may have been deleted. Head back to your dashboard.
        </p>
        <Link to="/app" className="btn-primary mt-6 inline-flex">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </div>
    )
  }

  const c = kb.source_counts
  const hasIndexedContent = kb.chunk_count > 0

  const tabs: TabItem<TabId>[] = [
    { id: 'sources', label: 'Sources', icon: FileText, badge: c.total },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'quiz', label: 'Study', icon: GraduationCap },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  ]

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-6 sm:px-8">
      {/* Header */}
      <Link
        to="/app"
        className="mb-4 inline-flex items-center gap-1.5 text-xs font-medium text-ink-dim transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All knowledge bases
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <h1 className="truncate font-display text-2xl font-semibold tracking-tight">
              {kb.name}
            </h1>
            {kb.is_demo && (
              <span className="rounded-full bg-violet/15 px-2 py-0.5 text-[0.65rem] font-semibold text-violet">
                demo
              </span>
            )}
          </div>
          {kb.description && (
            <p className="mt-1 max-w-2xl text-sm text-ink-muted">{kb.description}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-ink-dim">
            <span className="inline-flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" /> {c.pdf} PDF
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Youtube className="h-3.5 w-3.5" /> {c.youtube} video
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Type className="h-3.5 w-3.5" /> {c.text} text
            </span>
            <span className="h-3 w-px bg-white/10" />
            <span className="inline-flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5" /> {kb.chunk_count} chunks indexed
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-6 overflow-x-auto pb-1">
        <Tabs tabs={tabs} active={tab} onChange={setTab} />
      </div>

      {/* Panel */}
      <motion.div
        key={tab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="mt-6"
      >
        {tab === 'sources' && (
          <SourcesPanel kbId={kb.id} onChanged={() => loadKb(true)} />
        )}
        {tab === 'chat' && <ChatPanel kbId={kb.id} hasIndexedContent={hasIndexedContent} />}
        {tab === 'quiz' && <QuizPanel kbId={kb.id} hasIndexedContent={hasIndexedContent} />}
        {tab === 'analytics' && <AnalyticsPanel kbId={kb.id} />}
      </motion.div>
    </div>
  )
}
