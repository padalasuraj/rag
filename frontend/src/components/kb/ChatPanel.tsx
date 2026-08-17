import { AnimatePresence, motion } from 'framer-motion'
import {
  Check,
  Copy,
  CornerDownLeft,
  Filter,
  RotateCcw,
  Send,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { NexusMark } from '@/components/NexusLogo'
import { Citations } from '@/components/kb/Citations'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { api, streamChat } from '@/services/api'
import { useAppStore } from '@/stores/useAppStore'
import type { ChatMessage, SourceType } from '@/types'
import { cn } from '@/utils'

const SUGGESTIONS = [
  'Summarize the key ideas across these sources.',
  'What are the main takeaways?',
  'Explain the most important concept simply.',
  'What questions do these sources answer?',
]

const FILTERS: { id: 'all' | SourceType; label: string }[] = [
  { id: 'all', label: 'All sources' },
  { id: 'pdf', label: 'PDFs only' },
  { id: 'youtube', label: 'YouTube only' },
  { id: 'text', label: 'Text only' },
]

let localId = 0
const nextId = () => `local-${++localId}`

interface Props {
  kbId: string
  hasIndexedContent: boolean
}

export function ChatPanel({ kbId, hasIndexedContent }: Props) {
  const toast = useAppStore((s) => s.toast)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [filter, setFilter] = useState<'all' | SourceType>('all')
  const [showClear, setShowClear] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const streamingIdRef = useRef<string | null>(null)

  // Load prior conversation for this KB.
  useEffect(() => {
    let cancelled = false
    api
      .chatHistory(kbId)
      .then((history) => {
        if (!cancelled) setMessages(history)
      })
      .catch(() => {
        /* empty history is fine */
      })
    return () => {
      cancelled = true
    }
  }, [kbId])

  // Abort any in-flight stream when leaving the panel.
  useEffect(() => () => abortRef.current?.abort(), [])

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
    })
  }, [])

  useEffect(scrollToBottom, [messages, scrollToBottom])

  const patchStreaming = (patch: Partial<ChatMessage>) => {
    const id = streamingIdRef.current
    if (!id) return
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))
  }

  const send = async (question: string) => {
    const q = question.trim()
    if (!q || streaming) return

    setInput('')
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      content: q,
      citations: [],
    }
    const assistantId = nextId()
    streamingIdRef.current = assistantId
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      citations: [],
      streaming: true,
    }
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    await streamChat(
      {
        knowledge_base_id: kbId,
        question: q,
        source_type_filter: filter,
      },
      {
        onCitations: (citations, grounded) => patchStreaming({ citations, grounded }),
        onToken: (text) =>
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + text } : m,
            ),
          ),
        onDone: (relatedQuestions) => {
          patchStreaming({ relatedQuestions, streaming: false })
          setStreaming(false)
          streamingIdRef.current = null
        },
        onError: (message) => {
          patchStreaming({
            content:
              'The assistant ran into a problem answering that. Please check that the backend and your API key are configured, then try again.',
            streaming: false,
          })
          setStreaming(false)
          streamingIdRef.current = null
          toast(message, 'error')
        },
      },
      controller.signal,
    )
  }

  const regenerate = () => {
    // Re-ask the most recent user question and replace the last answer.
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    if (!lastUser || streaming) return
    setMessages((prev) => {
      const idx = prev.map((m) => m.role).lastIndexOf('assistant')
      return idx >= 0 ? prev.slice(0, idx) : prev
    })
    // Defer so state settles before appending the new turn.
    setTimeout(() => send(lastUser.content), 0)
  }

  const clearConversation = async () => {
    try {
      await api.clearHistory(kbId)
      setMessages([])
      setShowClear(false)
    } catch (e: any) {
      toast(e.message || 'Could not clear conversation.', 'error')
    }
  }

  const empty = messages.length === 0

  return (
    <div className="flex h-[calc(100vh-13rem)] min-h-[520px] flex-col">
      {/* Header row: filter + clear */}
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="relative">
          <Filter className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-dim" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as 'all' | SourceType)}
            className="cursor-pointer rounded-xl border border-white/10 bg-white/[0.03] py-2 pl-8 pr-8 text-sm text-ink-muted outline-none transition hover:text-ink focus:border-accent/50"
          >
            {FILTERS.map((f) => (
              <option key={f.id} value={f.id} className="bg-bg-panel">
                {f.label}
              </option>
            ))}
          </select>
        </div>
        {!empty && (
          <button
            onClick={() => setShowClear(true)}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-ink-dim transition hover:bg-white/5 hover:text-ink"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="card min-h-0 flex-1 overflow-y-auto p-4 sm:p-6"
      >
        {empty ? (
          <EmptyState hasIndexedContent={hasIndexedContent} onPick={send} />
        ) : (
          <div className="space-y-6">
            <AnimatePresence initial={false}>
              {messages.map((m) =>
                m.role === 'user' ? (
                  <UserBubble key={m.id} message={m} />
                ) : (
                  <AssistantBubble
                    key={m.id}
                    message={m}
                    onAsk={send}
                    onRegenerate={regenerate}
                    canRegenerate={!streaming && m.id === messages[messages.length - 1]?.id}
                  />
                ),
              )}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="mt-3">
        <div className="glass-strong flex items-end gap-2 rounded-2xl p-2">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send(input)
              }
            }}
            placeholder="Ask something about your sources…"
            className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm text-ink placeholder:text-ink-dim outline-none"
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || streaming}
            className="btn-primary h-10 w-10 flex-none !px-0"
            aria-label="Send"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-1.5 flex items-center justify-center gap-1.5 text-[0.7rem] text-ink-dim">
          <CornerDownLeft className="h-3 w-3" />
          Enter to send · Shift+Enter for a new line · answers are grounded in your sources
        </p>
      </div>

      <ConfirmDialog
        open={showClear}
        destructive
        title="Clear conversation?"
        message="This removes the chat history for this knowledge base. Your sources stay intact."
        confirmLabel="Clear"
        onConfirm={clearConversation}
        onClose={() => setShowClear(false)}
      />
    </div>
  )
}

/* ------------------------------- Bubbles --------------------------------- */

function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-grad-accent px-4 py-2.5 text-sm font-medium text-bg shadow-glow">
        {message.content}
      </div>
    </motion.div>
  )
}

function AssistantBubble({
  message,
  onAsk,
  onRegenerate,
  canRegenerate,
}: {
  message: ChatMessage
  onAsk: (q: string) => void
  onRegenerate: () => void
  canRegenerate: boolean
}) {
  const [copied, setCopied] = useState(false)
  const isThinking = message.streaming && !message.content
  const notFound = message.grounded === false

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="mt-0.5 flex h-8 w-8 flex-none items-center justify-center rounded-xl border border-white/10 bg-white/[0.03]">
        <NexusMark className="h-5 w-5" />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={cn(
            'rounded-2xl rounded-tl-md border p-4',
            notFound
              ? 'border-warn/25 bg-warn/[0.06]'
              : 'border-white/10 bg-white/[0.02]',
          )}
        >
          {isThinking ? (
            <div className="flex items-center gap-1.5 py-1">
              <span className="typing-dot" style={{ animationDelay: '0ms' }} />
              <span className="typing-dot" style={{ animationDelay: '150ms' }} />
              <span className="typing-dot" style={{ animationDelay: '300ms' }} />
            </div>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}

          {!message.streaming && message.citations.length > 0 && (
            <Citations citations={message.citations} />
          )}
        </div>

        {/* Action row */}
        {!message.streaming && message.content && (
          <div className="mt-1.5 flex items-center gap-1">
            <button
              onClick={copy}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[0.7rem] text-ink-dim transition hover:bg-white/5 hover:text-ink-muted"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-success" /> Copied
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" /> Copy
                </>
              )}
            </button>
            {canRegenerate && (
              <button
                onClick={onRegenerate}
                className="flex items-center gap-1 rounded-lg px-2 py-1 text-[0.7rem] text-ink-dim transition hover:bg-white/5 hover:text-ink-muted"
              >
                <RotateCcw className="h-3 w-3" /> Regenerate
              </button>
            )}
          </div>
        )}

        {/* Related follow-ups */}
        {!message.streaming &&
          message.relatedQuestions &&
          message.relatedQuestions.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {message.relatedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => onAsk(q)}
                  className="chip transition hover:border-accent/40 hover:text-ink"
                >
                  <Sparkles className="h-3 w-3 text-accent" />
                  {q}
                </button>
              ))}
            </div>
          )}
      </div>
    </motion.div>
  )
}

/* ----------------------------- Empty state ------------------------------- */

function EmptyState({
  hasIndexedContent,
  onPick,
}: {
  hasIndexedContent: boolean
  onPick: (q: string) => void
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center py-10 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-grad-accent-soft">
        <NexusMark className="h-7 w-7" />
      </div>
      <h3 className="mt-4 font-display text-lg font-semibold">Ask your knowledge base</h3>
      <p className="mt-1.5 max-w-sm text-sm text-ink-muted">
        {hasIndexedContent
          ? 'Every answer is grounded in your sources and cites exactly where it came from. If the answer isn’t there, the assistant will tell you.'
          : 'Add and index a source first — then ask away. Answers are grounded strictly in what you’ve added.'}
      </p>
      {hasIndexedContent && (
        <div className="mt-6 grid w-full max-w-md grid-cols-1 gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              className="card px-3.5 py-3 text-left text-sm text-ink-muted transition hover:border-accent/30 hover:text-ink"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
