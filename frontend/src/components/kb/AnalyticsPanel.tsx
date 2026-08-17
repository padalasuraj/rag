import { motion } from 'framer-motion'
import {
  Activity,
  BarChart3,
  FileStack,
  Gauge,
  Layers,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Timer,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { SourceTypeIcon } from '@/components/SourceTypeIcon'
import { Spinner } from '@/components/ui/Spinner'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/useAppStore'
import type { Analytics } from '@/types'
import { cn } from '@/utils'

interface Props {
  kbId: string
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: typeof Activity
  label: string
  value: string
  sub?: string
  accent?: 'accent' | 'success' | 'violet' | 'warn'
}) {
  const ring =
    accent === 'success'
      ? 'text-success'
      : accent === 'violet'
        ? 'text-violet'
        : accent === 'warn'
          ? 'text-warn'
          : 'text-accent'
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-5"
    >
      <div className="flex items-center gap-2 text-ink-muted">
        <Icon className={cn('h-4 w-4', ring)} />
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <p className="mt-3 font-display text-2xl font-semibold text-ink">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-ink-dim">{sub}</p>}
    </motion.div>
  )
}

export function AnalyticsPanel({ kbId }: Props) {
  const toast = useAppStore((s) => s.toast)
  const [data, setData] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await api.analytics(kbId))
    } catch (e: any) {
      toast(e.message || 'Could not load analytics.', 'error')
    } finally {
      setLoading(false)
    }
  }, [kbId, toast])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-ink-muted">
        <Spinner className="h-5 w-5" />
        Crunching the numbers…
      </div>
    )
  }

  if (!data) return null

  const groundedPct = Math.round(data.grounded_answer_rate * 100)
  const scorePct = Math.round(data.avg_retrieval_score * 100)
  const maxHits = Math.max(1, ...data.most_queried_sources.map((s) => s.query_hits))

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-display text-base font-semibold">Retrieval analytics</h3>
          <p className="text-sm text-ink-muted">
            How this knowledge base is performing across questions asked.
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-ink-dim transition hover:bg-white/5 hover:text-ink"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={FileStack}
          label="Sources"
          value={String(data.total_sources)}
          sub={`${data.total_chunks} indexed chunks`}
        />
        <StatCard
          icon={MessageSquare}
          label="Questions"
          value={String(data.questions_asked)}
          sub="asked so far"
          accent="violet"
        />
        <StatCard
          icon={ShieldCheck}
          label="Grounded"
          value={`${groundedPct}%`}
          sub="answered from sources"
          accent="success"
        />
        <StatCard
          icon={Timer}
          label="Avg latency"
          value={data.avg_latency_ms ? `${(data.avg_latency_ms / 1000).toFixed(1)}s` : '—'}
          sub="per answer"
          accent="warn"
        />
      </div>

      {data.questions_asked === 0 ? (
        <div className="card mt-4 flex flex-col items-center px-6 py-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-grad-accent-soft">
            <BarChart3 className="h-5 w-5 text-accent" />
          </div>
          <p className="mt-3 text-sm font-medium text-ink">No questions yet</p>
          <p className="mt-1 max-w-xs text-xs text-ink-muted">
            Head to the Chat tab and ask something. Retrieval quality and source usage will
            show up here.
          </p>
        </div>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {/* Retrieval quality */}
          <div className="card p-5">
            <div className="flex items-center gap-2 text-ink-muted">
              <Gauge className="h-4 w-4 text-accent" />
              <span className="text-xs font-medium uppercase tracking-wider">
                Retrieval quality
              </span>
            </div>
            <div className="mt-4 space-y-4">
              <Meter label="Avg relevance score" pct={scorePct} tone="accent" />
              <Meter label="Grounded answer rate" pct={groundedPct} tone="success" />
            </div>
            <p className="mt-4 text-xs leading-relaxed text-ink-dim">
              Relevance is the mean cosine similarity of retrieved chunks. Grounded rate is the
              share of answers backed by sources rather than the honest “not found” fallback.
            </p>
          </div>

          {/* Most queried sources */}
          <div className="card p-5">
            <div className="flex items-center gap-2 text-ink-muted">
              <Layers className="h-4 w-4 text-violet" />
              <span className="text-xs font-medium uppercase tracking-wider">
                Most queried sources
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {data.most_queried_sources.length === 0 && (
                <p className="text-xs text-ink-dim">No source usage recorded yet.</p>
              )}
              {data.most_queried_sources.map((s) => (
                <div key={s.source_id}>
                  <div className="mb-1 flex items-center gap-2 text-xs">
                    <SourceTypeIcon type={s.source_type} className="flex-none" />
                    <span className="min-w-0 flex-1 truncate text-ink-muted">{s.title}</span>
                    <span className="flex-none font-mono text-ink-dim">{s.query_hits}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/10">
                    <motion.div
                      className="h-full rounded-full bg-grad-accent"
                      initial={{ width: 0 }}
                      animate={{ width: `${(s.query_hits / maxHits) * 100}%` }}
                      transition={{ type: 'spring', stiffness: 180, damping: 28 }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Meter({
  label,
  pct,
  tone,
}: {
  label: string
  pct: number
  tone: 'accent' | 'success'
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="text-ink-muted">{label}</span>
        <span className="font-mono text-ink">{pct}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <motion.div
          className={cn(
            'h-full rounded-full',
            tone === 'success' ? 'bg-success' : 'bg-grad-accent',
          )}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: 'spring', stiffness: 180, damping: 28 }}
        />
      </div>
    </div>
  )
}
