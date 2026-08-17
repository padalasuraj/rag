import { motion } from 'framer-motion'
import { ArrowRight, FileText, Layers, Trash2, Type, Youtube } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { KnowledgeBase } from '@/types'
import { relativeTime } from '@/utils'

interface Props {
  kb: KnowledgeBase
  onDelete: (kb: KnowledgeBase) => void
}

function CountPill({
  icon: Icon,
  value,
  label,
}: {
  icon: typeof FileText
  value: number
  label: string
}) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-muted" title={label}>
      <Icon className="h-3.5 w-3.5 text-ink-dim" />
      {value}
    </span>
  )
}

export function KnowledgeBaseCard({ kb, onDelete }: Props) {
  const navigate = useNavigate()
  const c = kb.source_counts

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      whileHover={{ y: -3 }}
      transition={{ type: 'spring', stiffness: 300, damping: 26 }}
      className="card group relative flex cursor-pointer flex-col p-5"
      onClick={() => navigate(`/app/kb/${kb.id}`)}
    >
      {/* Accent glow on hover */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-grad-accent-soft opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-display text-base font-semibold text-ink">
              {kb.name}
            </h3>
            {kb.is_demo && (
              <span className="flex-none rounded-full bg-violet/15 px-2 py-0.5 text-[0.6rem] font-semibold text-violet">
                demo
              </span>
            )}
          </div>
          <p className="mt-1 line-clamp-2 min-h-[2.5rem] text-sm text-ink-muted">
            {kb.description || 'No description provided.'}
          </p>
        </div>

        {!kb.is_demo && (
          <button
            className="flex-none rounded-lg p-2 text-ink-dim opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
            aria-label="Delete knowledge base"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(kb)
            }}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="relative mt-4 flex items-center gap-4 border-t border-white/5 pt-4">
        <CountPill icon={FileText} value={c.pdf} label="PDF sources" />
        <CountPill icon={Youtube} value={c.youtube} label="YouTube sources" />
        <CountPill icon={Type} value={c.text} label="Text sources" />
        <span className="mx-1 h-3 w-px bg-white/10" />
        <CountPill icon={Layers} value={kb.chunk_count} label="Indexed chunks" />

        <span className="ml-auto flex items-center gap-1 text-xs font-medium text-accent opacity-0 transition group-hover:opacity-100">
          Open
          <ArrowRight className="h-3.5 w-3.5" />
        </span>
      </div>

      <p className="relative mt-2 text-[0.7rem] text-ink-dim">
        Updated {relativeTime(kb.updated_at)}
      </p>
    </motion.div>
  )
}
