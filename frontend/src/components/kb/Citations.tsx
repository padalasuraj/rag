import { Clock, ExternalLink, FileText, Quote } from 'lucide-react'
import { useState } from 'react'
import { SourceTypeIcon } from '@/components/SourceTypeIcon'
import { Modal } from '@/components/ui/Modal'
import { pdfFileUrl } from '@/services/api'
import type { Citation } from '@/types'
import { cn, formatTimestamp } from '@/utils'

/** Human-readable locator badge: PDF page number or YouTube timestamp. */
function LocatorBadge({ citation }: { citation: Citation }) {
  if (citation.source_type === 'pdf' && citation.page != null) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[0.65rem] text-ink-muted">
        <FileText className="h-3 w-3" />
        p.{citation.page}
      </span>
    )
  }
  if (citation.source_type === 'youtube' && citation.start_seconds != null) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[0.65rem] text-ink-muted">
        <Clock className="h-3 w-3" />
        {formatTimestamp(citation.start_seconds)}
      </span>
    )
  }
  return null
}

interface Props {
  citations: Citation[]
  compact?: boolean
}

/**
 * Renders the sources behind a grounded answer. Each citation is clickable:
 *  - PDF    → opens the stored file at the exact page (#page=N)
 *  - YouTube→ opens the video at the exact timestamp (&t=SECONDS)
 *  - text   → opens a modal with the retrieved snippet
 *
 * The deep-link targets are computed from real retrieved-chunk metadata on the
 * backend, so they always point at genuine evidence for the answer.
 */
export function Citations({ citations, compact = false }: Props) {
  const [active, setActive] = useState<Citation | null>(null)

  if (!citations.length) return null

  const openCitation = (c: Citation) => {
    if (c.source_type === 'youtube' && c.url) {
      window.open(c.url, '_blank', 'noopener,noreferrer')
    } else if (c.source_type === 'pdf') {
      window.open(pdfFileUrl(c.source_id, c.page), '_blank', 'noopener,noreferrer')
    } else {
      setActive(c)
    }
  }

  const external = (c: Citation) => c.source_type === 'youtube' || c.source_type === 'pdf'

  return (
    <div className={cn('space-y-2', !compact && 'mt-3')}>
      {!compact && (
        <p className="text-[0.7rem] font-semibold uppercase tracking-wider text-ink-dim">
          Sources
        </p>
      )}
      <div className="flex flex-col gap-1.5">
        {citations.map((c) => (
          <button
            key={`${c.chunk_id}-${c.index}`}
            onClick={() => openCitation(c)}
            className="group flex items-center gap-2.5 rounded-lg border border-white/5 bg-white/[0.02] px-2.5 py-2 text-left transition hover:border-accent/30 hover:bg-white/[0.05]"
          >
            <span className="flex h-5 w-5 flex-none items-center justify-center rounded-md bg-grad-accent-soft font-mono text-[0.65rem] font-semibold text-accent">
              {c.index}
            </span>
            <SourceTypeIcon type={c.source_type} className="flex-none" />
            <span className="min-w-0 flex-1 truncate text-xs font-medium text-ink-muted group-hover:text-ink">
              {c.title}
            </span>
            <LocatorBadge citation={c} />
            {external(c) && (
              <ExternalLink className="h-3 w-3 flex-none text-ink-dim group-hover:text-accent" />
            )}
          </button>
        ))}
      </div>

      <Modal
        open={!!active}
        onClose={() => setActive(null)}
        title={active?.title || 'Source excerpt'}
      >
        {active && (
          <div>
            <div className="mb-3 flex items-center gap-2">
              <SourceTypeIcon type={active.source_type} />
              <LocatorBadge citation={active} />
              <span className="ml-auto text-[0.7rem] text-ink-dim">
                relevance {(active.score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="relative rounded-xl border border-white/10 bg-black/30 p-4">
              <Quote className="absolute -left-1 -top-2 h-6 w-6 text-accent/20" />
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink/90">
                {active.snippet}
              </p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
