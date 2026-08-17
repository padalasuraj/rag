import { FileText, Youtube, Type } from 'lucide-react'
import type { SourceStatus, SourceType } from '@/types'
import { cn } from '@/utils'

export function SourceTypeIcon({
  type,
  className,
}: {
  type: SourceType
  className?: string
}) {
  const Icon = type === 'pdf' ? FileText : type === 'youtube' ? Youtube : Type
  const color =
    type === 'pdf' ? 'text-rose-300' : type === 'youtube' ? 'text-red-400' : 'text-accent'
  return <Icon className={cn('h-4 w-4', color, className)} />
}

const STATUS_STYLE: Record<SourceStatus, string> = {
  pending: 'text-ink-muted bg-white/[0.05] border-white/10',
  processing: 'text-accent bg-accent/10 border-accent/30',
  completed: 'text-success bg-success/10 border-success/30',
  failed: 'text-danger bg-danger/10 border-danger/30',
}

const STATUS_LABEL: Record<SourceStatus, string> = {
  pending: 'Queued',
  processing: 'Processing',
  completed: 'Ready',
  failed: 'Failed',
}

export function StatusBadge({ status }: { status: SourceStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[0.7rem] font-medium',
        STATUS_STYLE[status],
      )}
    >
      {status === 'processing' && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
      )}
      {STATUS_LABEL[status]}
    </span>
  )
}
