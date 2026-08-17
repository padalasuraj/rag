import { AnimatePresence, motion } from 'framer-motion'
import {
  Check,
  GraduationCap,
  Loader2,
  RefreshCw,
  Sparkles,
  Trophy,
  X,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Citations } from '@/components/kb/Citations'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/useAppStore'
import type { QuizQuestion, Source } from '@/types'
import { cn } from '@/utils'

type Phase = 'setup' | 'loading' | 'active' | 'done'
const COUNTS = [3, 5, 8]

interface Props {
  kbId: string
  hasIndexedContent: boolean
}

export function QuizPanel({ kbId, hasIndexedContent }: Props) {
  const toast = useAppStore((s) => s.toast)
  const [phase, setPhase] = useState<Phase>('setup')
  const [sources, setSources] = useState<Source[]>([])
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [count, setCount] = useState(5)

  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [score, setScore] = useState(0)

  useEffect(() => {
    api
      .listSources(kbId)
      .then((list) => setSources(list.filter((s) => s.status === 'completed')))
      .catch(() => {})
  }, [kbId])

  const start = async () => {
    setPhase('loading')
    try {
      const res = await api.quiz(kbId, sourceId, count)
      if (!res.questions?.length) {
        toast('Not enough indexed content to build a quiz yet.', 'error')
        setPhase('setup')
        return
      }
      setQuestions(res.questions)
      setCurrent(0)
      setSelected(null)
      setScore(0)
      setPhase('active')
    } catch (e: any) {
      toast(e.message || 'Could not generate a quiz.', 'error')
      setPhase('setup')
    }
  }

  const choose = (label: string) => {
    if (selected) return
    setSelected(label)
    if (label === questions[current].correct_label) setScore((s) => s + 1)
  }

  const next = () => {
    if (current + 1 >= questions.length) {
      setPhase('done')
    } else {
      setCurrent((c) => c + 1)
      setSelected(null)
    }
  }

  const reset = () => {
    setPhase('setup')
    setQuestions([])
    setSelected(null)
    setCurrent(0)
    setScore(0)
  }

  if (!hasIndexedContent) {
    return (
      <PanelEmpty
        icon={<GraduationCap className="h-6 w-6 text-accent" />}
        title="Study mode needs sources"
        body="Add and index at least one source, then generate a quiz drawn straight from your material — every answer comes with an explanation and a citation."
      />
    )
  }

  /* ------------------------------- Setup -------------------------------- */
  if (phase === 'setup' || phase === 'loading') {
    return (
      <div className="mx-auto max-w-lg">
        <div className="card p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-grad-accent-soft">
              <GraduationCap className="h-5 w-5 text-accent" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold">Generate a quiz</h3>
              <p className="text-sm text-ink-muted">
                Questions are written from your indexed content.
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-ink-muted">
                Number of questions
              </label>
              <div className="inline-flex rounded-xl border border-white/10 bg-white/[0.03] p-1">
                {COUNTS.map((n) => (
                  <button
                    key={n}
                    onClick={() => setCount(n)}
                    className={cn(
                      'rounded-lg px-4 py-1.5 text-sm font-medium transition',
                      n === count ? 'bg-grad-accent text-bg' : 'text-ink-muted hover:text-ink',
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-ink-muted">
                Scope
              </label>
              <select
                value={sourceId ?? 'all'}
                onChange={(e) =>
                  setSourceId(e.target.value === 'all' ? null : e.target.value)
                }
                className="input cursor-pointer"
              >
                <option value="all" className="bg-bg-panel">
                  All sources in this knowledge base
                </option>
                {sources.map((s) => (
                  <option key={s.id} value={s.id} className="bg-bg-panel">
                    {s.title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            className="btn-primary mt-6 w-full"
            onClick={start}
            disabled={phase === 'loading'}
          >
            {phase === 'loading' ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Writing questions…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate quiz
              </>
            )}
          </button>
        </div>
      </div>
    )
  }

  /* -------------------------------- Done -------------------------------- */
  if (phase === 'done') {
    const pct = Math.round((score / questions.length) * 100)
    const good = pct >= 70
    return (
      <div className="mx-auto max-w-lg">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card flex flex-col items-center p-8 text-center"
        >
          <div
            className={cn(
              'flex h-16 w-16 items-center justify-center rounded-2xl border',
              good
                ? 'border-success/30 bg-success/10'
                : 'border-warn/30 bg-warn/10',
            )}
          >
            <Trophy className={cn('h-8 w-8', good ? 'text-success' : 'text-warn')} />
          </div>
          <h3 className="mt-4 font-display text-2xl font-semibold">
            {score} / {questions.length}
          </h3>
          <p className="mt-1 text-sm text-ink-muted">
            You scored {pct}%. {good ? 'Strong grasp of the material.' : 'Worth another pass.'}
          </p>
          <div className="mt-6 flex gap-2">
            <button className="btn-ghost" onClick={reset}>
              <RefreshCw className="h-4 w-4" />
              New quiz
            </button>
            <button className="btn-primary" onClick={start}>
              <Sparkles className="h-4 w-4" />
              Retry
            </button>
          </div>
        </motion.div>
      </div>
    )
  }

  /* ------------------------------- Active ------------------------------- */
  const q = questions[current]
  const answered = selected !== null
  const progress = ((current + (answered ? 1 : 0)) / questions.length) * 100

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between text-xs text-ink-muted">
          <span>
            Question {current + 1} of {questions.length}
          </span>
          <span>Score {score}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
          <motion.div
            className="h-full rounded-full bg-grad-accent"
            animate={{ width: `${progress}%` }}
            transition={{ type: 'spring', stiffness: 200, damping: 30 }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={current}
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -24 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="card p-6"
        >
          <h3 className="font-display text-lg font-medium leading-snug">{q.question}</h3>

          <div className="mt-5 space-y-2.5">
            {q.options.map((opt) => {
              const isCorrect = opt.label === q.correct_label
              const isPicked = opt.label === selected
              const state = !answered
                ? 'idle'
                : isCorrect
                  ? 'correct'
                  : isPicked
                    ? 'wrong'
                    : 'muted'
              return (
                <button
                  key={opt.label}
                  onClick={() => choose(opt.label)}
                  disabled={answered}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition',
                    state === 'idle' &&
                      'border-white/10 bg-white/[0.02] hover:border-accent/40 hover:bg-white/[0.05]',
                    state === 'correct' && 'border-success/40 bg-success/10 text-ink',
                    state === 'wrong' && 'border-danger/40 bg-danger/10 text-ink',
                    state === 'muted' && 'border-white/5 bg-white/[0.01] text-ink-muted',
                  )}
                >
                  <span
                    className={cn(
                      'flex h-6 w-6 flex-none items-center justify-center rounded-md border font-mono text-xs font-semibold',
                      state === 'correct'
                        ? 'border-success/40 bg-success/20 text-success'
                        : state === 'wrong'
                          ? 'border-danger/40 bg-danger/20 text-danger'
                          : 'border-white/10 text-ink-muted',
                    )}
                  >
                    {opt.label}
                  </span>
                  <span className="flex-1">{opt.text}</span>
                  {state === 'correct' && <Check className="h-4 w-4 text-success" />}
                  {state === 'wrong' && <X className="h-4 w-4 text-danger" />}
                </button>
              )
            })}
          </div>

          <AnimatePresence>
            {answered && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="overflow-hidden"
              >
                <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.02] p-4">
                  <p className="text-[0.7rem] font-semibold uppercase tracking-wider text-ink-dim">
                    Explanation
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-ink/90">{q.explanation}</p>
                  {q.citation && <Citations citations={[q.citation]} />}
                </div>

                <div className="mt-4 flex justify-end">
                  <button className="btn-primary" onClick={next}>
                    {current + 1 >= questions.length ? 'See results' : 'Next question'}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function PanelEmpty({
  icon,
  title,
  body,
}: {
  icon: ReactNode
  title: string
  body: string
}) {
  return (
    <div className="card mx-auto flex max-w-md flex-col items-center px-6 py-14 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-grad-accent-soft">
        {icon}
      </div>
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 text-xs text-ink-muted">{body}</p>
    </div>
  )
}
