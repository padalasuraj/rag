import { AnimatePresence, motion } from 'framer-motion'
import {
  ExternalLink,
  FileText,
  FileUp,
  Layers,
  Loader2,
  Plus,
  RotateCw,
  Trash2,
  Type,
  Youtube,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { SourceTypeIcon, StatusBadge } from '@/components/SourceTypeIcon'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Spinner } from '@/components/ui/Spinner'
import { api, pdfFileUrl } from '@/services/api'
import { useAppStore } from '@/stores/useAppStore'
import type { Source, SourceType } from '@/types'
import { cn, relativeTime } from '@/utils'

const ADD_TABS: { id: SourceType; label: string; icon: typeof FileText }[] = [
  { id: 'pdf', label: 'PDF', icon: FileText },
  { id: 'youtube', label: 'YouTube', icon: Youtube },
  { id: 'text', label: 'Text', icon: Type },
]

const POLL_MS = 2500

interface Props {
  kbId: string
  onChanged: () => void
}

export function SourcesPanel({ kbId, onChanged }: Props) {
  const toast = useAppStore((s) => s.toast)
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<SourceType>('pdf')
  const [pendingDelete, setPendingDelete] = useState<Source | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      try {
        const list = await api.listSources(kbId)
        setSources(list)
      } catch (e: any) {
        if (!silent) toast(e.message || 'Could not load sources.', 'error')
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [kbId, toast],
  )

  useEffect(() => {
    load()
  }, [load])

  // Poll while any source is still being ingested, then refresh KB counts once done.
  const wasProcessing = useRef(false)
  useEffect(() => {
    const active = sources.some((s) => s.status === 'pending' || s.status === 'processing')
    if (active) {
      wasProcessing.current = true
      const t = setInterval(() => load(true), POLL_MS)
      return () => clearInterval(t)
    }
    if (wasProcessing.current) {
      wasProcessing.current = false
      onChanged() // counts/chunks changed — let the parent refresh the KB
    }
  }, [sources, load, onChanged])

  const addSource = (created: Source) => {
    setSources((prev) => [created, ...prev])
  }

  const handleReindex = async (s: Source) => {
    try {
      const updated = await api.reindexSource(s.id)
      setSources((prev) => prev.map((x) => (x.id === s.id ? updated : x)))
      toast('Re-indexing started.', 'info')
    } catch (e: any) {
      toast(e.message || 'Could not re-index.', 'error')
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.deleteSource(pendingDelete.id)
      setSources((prev) => prev.filter((x) => x.id !== pendingDelete.id))
      toast('Source removed.', 'success')
      setPendingDelete(null)
      onChanged()
    } catch (e: any) {
      toast(e.message || 'Could not remove source.', 'error')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
      {/* Add source */}
      <div className="card h-fit p-5">
        <h3 className="font-display text-base font-semibold">Add a source</h3>
        <p className="mt-1 text-sm text-ink-muted">
          Everything you add is chunked, embedded, and indexed for retrieval.
        </p>

        <div className="mt-4 inline-flex rounded-xl border border-white/10 bg-white/[0.03] p-1">
          {ADD_TABS.map((t) => {
            const Icon = t.icon
            const on = t.id === tab
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition',
                  on ? 'bg-white/10 text-ink' : 'text-ink-muted hover:text-ink',
                )}
              >
                <Icon className="h-4 w-4" />
                {t.label}
              </button>
            )
          })}
        </div>

        <div className="mt-4">
          {tab === 'pdf' && (
            <PdfAdd kbId={kbId} onAdded={addSource} toast={toast} />
          )}
          {tab === 'youtube' && (
            <YouTubeAdd kbId={kbId} onAdded={addSource} toast={toast} />
          )}
          {tab === 'text' && <TextAdd kbId={kbId} onAdded={addSource} toast={toast} />}
        </div>
      </div>

      {/* Source list */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-display text-base font-semibold">
            Sources{' '}
            <span className="text-ink-dim">({sources.length})</span>
          </h3>
          {sources.some((s) => s.status === 'processing' || s.status === 'pending') && (
            <span className="flex items-center gap-1.5 text-xs text-accent">
              <Spinner className="h-3.5 w-3.5" />
              Indexing…
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-ink-muted">
            <Spinner className="h-5 w-5" />
            Loading sources…
          </div>
        ) : sources.length === 0 ? (
          <div className="card flex flex-col items-center px-6 py-14 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-grad-accent-soft">
              <FileUp className="h-5 w-5 text-accent" />
            </div>
            <p className="mt-3 text-sm font-medium text-ink">No sources yet</p>
            <p className="mt-1 max-w-xs text-xs text-ink-muted">
              Add a PDF, YouTube video, or some text on the left to start building this
              knowledge base.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {sources.map((s) => (
                <SourceRow
                  key={s.id}
                  source={s}
                  onReindex={handleReindex}
                  onDelete={setPendingDelete}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        destructive
        busy={deleting}
        title="Remove source?"
        message={
          pendingDelete
            ? `“${pendingDelete.title}” and its indexed chunks will be removed from this knowledge base.`
            : ''
        }
        confirmLabel="Remove"
        onConfirm={confirmDelete}
        onClose={() => !deleting && setPendingDelete(null)}
      />
    </div>
  )
}

/* --------------------------------- Rows ---------------------------------- */

function SourceRow({
  source,
  onReindex,
  onDelete,
}: {
  source: Source
  onReindex: (s: Source) => void
  onDelete: (s: Source) => void
}) {
  const busy = source.status === 'pending' || source.status === 'processing'
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ type: 'spring', stiffness: 300, damping: 28 }}
      className="card flex items-center gap-3 p-3.5"
    >
      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-white/10 bg-white/[0.03]">
        <SourceTypeIcon type={source.source_type} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium text-ink">{source.title}</p>
          <StatusBadge status={source.status} />
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-[0.7rem] text-ink-dim">
          {source.status === 'completed' && (
            <span className="inline-flex items-center gap-1">
              <Layers className="h-3 w-3" />
              {source.num_chunks} chunks
            </span>
          )}
          {busy && <span className="text-accent">Extracting &amp; embedding…</span>}
          {source.status === 'failed' && (
            <span className="truncate text-danger" title={source.error || ''}>
              {source.error || 'Ingestion failed'}
            </span>
          )}
          {!busy && source.status !== 'failed' && (
            <span>Added {relativeTime(source.created_at)}</span>
          )}
        </div>
      </div>

      <div className="flex flex-none items-center gap-1">
        {source.source_type === 'pdf' && source.status === 'completed' && (
          <a
            href={pdfFileUrl(source.id)}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg p-2 text-ink-dim transition hover:bg-white/10 hover:text-ink"
            title="Open PDF"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
        {(source.status === 'completed' || source.status === 'failed') && (
          <button
            onClick={() => onReindex(source)}
            className="rounded-lg p-2 text-ink-dim transition hover:bg-white/10 hover:text-ink"
            title="Re-index"
          >
            <RotateCw className="h-4 w-4" />
          </button>
        )}
        {busy ? (
          <span className="p-2">
            <Loader2 className="h-4 w-4 animate-spin text-accent" />
          </span>
        ) : (
          <button
            onClick={() => onDelete(source)}
            className="rounded-lg p-2 text-ink-dim transition hover:bg-danger/10 hover:text-danger"
            title="Remove"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </motion.div>
  )
}

/* ------------------------------ Add: PDF --------------------------------- */

type ToastFn = (message: string, variant?: 'success' | 'error' | 'info') => void

function PdfAdd({
  kbId,
  onAdded,
  toast,
}: {
  kbId: string
  onAdded: (s: Source) => void
  toast: ToastFn
}) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const upload = async (files: FileList | File[]) => {
    const pdfs = Array.from(files).filter(
      (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'),
    )
    if (pdfs.length === 0) {
      toast('Please choose PDF files.', 'error')
      return
    }
    setUploading((n) => n + pdfs.length)
    for (const file of pdfs) {
      try {
        const src = await api.addPdf(kbId, file)
        onAdded(src)
      } catch (e: any) {
        toast(`${file.name}: ${e.message || 'upload failed'}`, 'error')
      } finally {
        setUploading((n) => n - 1)
      }
    }
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          upload(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition',
          dragging
            ? 'border-accent bg-accent/5'
            : 'border-white/15 bg-white/[0.02] hover:border-accent/40 hover:bg-white/[0.04]',
        )}
      >
        <FileUp className={cn('h-7 w-7', dragging ? 'text-accent' : 'text-ink-muted')} />
        <p className="mt-3 text-sm font-medium text-ink">
          Drop PDFs here, or click to browse
        </p>
        <p className="mt-1 text-xs text-ink-dim">
          Text-based PDFs work best. You can add several at once.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) upload(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
      {uploading > 0 && (
        <p className="mt-3 flex items-center gap-2 text-xs text-accent">
          <Spinner className="h-3.5 w-3.5" />
          Uploading {uploading} file{uploading > 1 ? 's' : ''}…
        </p>
      )}
    </div>
  )
}

/* ---------------------------- Add: YouTube ------------------------------- */

function YouTubeAdd({
  kbId,
  onAdded,
  toast,
}: {
  kbId: string
  onAdded: (s: Source) => void
  toast: ToastFn
}) {
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    const trimmed = url.trim()
    if (!trimmed || busy) return
    setBusy(true)
    try {
      const src = await api.addYouTube(kbId, trimmed)
      onAdded(src)
      setUrl('')
      toast('Fetching transcript…', 'info')
    } catch (e: any) {
      toast(e.message || 'Could not add video.', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink-muted">
          YouTube URL
        </label>
        <input
          className="input"
          placeholder="https://www.youtube.com/watch?v=…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
      </div>
      <p className="text-xs text-ink-dim">
        The video must have captions/transcript available. Citations will link back to the
        exact timestamp.
      </p>
      <button className="btn-primary w-full" onClick={submit} disabled={!url.trim() || busy}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        Add video
      </button>
    </div>
  )
}

/* ------------------------------ Add: Text -------------------------------- */

const TEXT_MAX = 50000

function TextAdd({
  kbId,
  onAdded,
  toast,
}: {
  kbId: string
  onAdded: (s: Source) => void
  toast: ToastFn
}) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    if (!title.trim() || !content.trim() || busy) return
    setBusy(true)
    try {
      const src = await api.addText(kbId, title.trim(), content.trim())
      onAdded(src)
      setTitle('')
      setContent('')
      toast('Indexing text…', 'info')
    } catch (e: any) {
      toast(e.message || 'Could not add text.', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink-muted">Title</label>
        <input
          className="input"
          placeholder="e.g. Meeting notes — Q3 planning"
          value={title}
          maxLength={160}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <div>
        <div className="mb-1.5 flex items-center justify-between">
          <label className="text-sm font-medium text-ink-muted">Content</label>
          <span
            className={cn(
              'text-[0.7rem]',
              content.length > TEXT_MAX ? 'text-danger' : 'text-ink-dim',
            )}
          >
            {content.length.toLocaleString()} / {TEXT_MAX.toLocaleString()}
          </span>
        </div>
        <textarea
          className="input min-h-[160px] resize-y font-mono text-[0.8rem]"
          placeholder="Paste an article, notes, documentation…"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
      </div>
      <button
        className="btn-primary w-full"
        onClick={submit}
        disabled={!title.trim() || !content.trim() || content.length > TEXT_MAX || busy}
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        Add text
      </button>
    </div>
  )
}
