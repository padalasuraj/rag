import { AnimatePresence, motion } from 'framer-motion'
import {
  BookOpen,
  Database,
  HelpCircle,
  Menu,
  Plus,
  Sparkles,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { CreateKBModal } from '@/components/dashboard/CreateKBModal'
import { NexusLogo } from '@/components/NexusLogo'
import { useAppStore } from '@/stores/useAppStore'
import { cn } from '@/utils'

function HealthIndicator() {
  const health = useAppStore((s) => s.health)

  if (!health) {
    return (
      <div className="chip w-full justify-start">
        <span className="h-2 w-2 rounded-full bg-ink-dim" />
        Connecting to API…
      </div>
    )
  }

  const ok = health.openai_key_present
  return (
    <div className="card space-y-2 p-3">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            ok ? 'bg-success shadow-[0_0_10px] shadow-success/60' : 'bg-warn',
          )}
        />
        <span className="text-xs font-medium text-ink">
          {ok ? 'OpenAI connected' : 'No API key set'}
        </span>
      </div>
      <div className="space-y-0.5 text-[0.7rem] text-ink-dim">
        <div className="flex justify-between gap-2">
          <span>Vector store</span>
          <span className="font-mono text-ink-muted">{health.vector_store}</span>
        </div>
        <div className="flex justify-between gap-2">
          <span>Model</span>
          <span className="font-mono text-ink-muted">{health.llm_model}</span>
        </div>
      </div>
    </div>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const knowledgeBases = useAppStore((s) => s.knowledgeBases)
  const openCreateKb = useAppStore((s) => s.openCreateKb)

  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <NavLink to="/app" onClick={onNavigate} className="px-1 pt-1">
        <NexusLogo />
      </NavLink>

      <button
        className="btn-primary w-full"
        onClick={() => {
          openCreateKb()
          onNavigate?.()
        }}
      >
        <Plus className="h-4 w-4" />
        New knowledge base
      </button>

      <nav className="space-y-1">
        <NavLink
          to="/app"
          end
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition',
              isActive
                ? 'bg-white/[0.06] text-ink'
                : 'text-ink-muted hover:bg-white/[0.04] hover:text-ink',
            )
          }
        >
          <Database className="h-4 w-4" />
          Knowledge bases
        </NavLink>
      </nav>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <p className="px-3 pb-2 text-[0.7rem] font-semibold uppercase tracking-wider text-ink-dim">
          Your bases
        </p>
        <div className="space-y-0.5">
          {knowledgeBases.length === 0 && (
            <p className="px-3 py-2 text-xs text-ink-dim">No knowledge bases yet.</p>
          )}
          {knowledgeBases.map((kb) => (
            <NavLink
              key={kb.id}
              to={`/app/kb/${kb.id}`}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition',
                  isActive
                    ? 'bg-white/[0.06] text-ink'
                    : 'text-ink-muted hover:bg-white/[0.04] hover:text-ink',
                )
              }
            >
              <BookOpen className="h-4 w-4 flex-none text-ink-dim group-hover:text-accent" />
              <span className="flex-1 truncate">{kb.name}</span>
              {kb.is_demo && (
                <span className="flex-none rounded-full bg-violet/15 px-1.5 py-0.5 text-[0.6rem] font-semibold text-violet">
                  demo
                </span>
              )}
            </NavLink>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <HealthIndicator />
        <a
          href="https://platform.openai.com/api-keys"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 px-1 text-xs text-ink-dim transition hover:text-ink-muted"
        >
          <HelpCircle className="h-3.5 w-3.5" />
          Where do I get an API key?
        </a>
      </div>
    </div>
  )
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const fetchKnowledgeBases = useAppStore((s) => s.fetchKnowledgeBases)

  useEffect(() => {
    fetchKnowledgeBases()
  }, [fetchKnowledgeBases])

  // Close the mobile drawer on route change.
  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="flex h-full">
      {/* Desktop sidebar */}
      <aside className="hidden w-72 flex-none border-r border-white/10 bg-bg-soft/40 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="fixed inset-0 z-40 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              className="glass-strong absolute inset-y-0 left-0 w-72"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            >
              <SidebarContent onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b border-white/10 bg-bg-soft/40 px-4 py-3 lg:hidden">
          <button
            className="rounded-lg p-2 text-ink-muted transition hover:bg-white/10 hover:text-ink"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <NexusLogo />
          <span className="w-9">
            <Sparkles className="h-4 w-4 text-accent/50" />
          </span>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>

      <CreateKBModal />
    </div>
  )
}
