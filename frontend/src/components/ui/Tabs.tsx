import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/utils'

export interface TabItem<T extends string> {
  id: T
  label: string
  icon?: LucideIcon
  badge?: number
}

interface TabsProps<T extends string> {
  tabs: TabItem<T>[]
  active: T
  onChange: (id: T) => void
  className?: string
}

/**
 * Segmented control with an animated sliding highlight. Generic over the
 * union of tab ids so callers get type-safe `active`/`onChange`.
 */
export function Tabs<T extends string>({ tabs, active, onChange, className }: TabsProps<T>) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1',
        className,
      )}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active
        const Icon = tab.icon
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition',
              isActive ? 'text-bg' : 'text-ink-muted hover:text-ink',
            )}
          >
            {isActive && (
              <motion.span
                layoutId="tab-highlight"
                className="absolute inset-0 rounded-lg bg-grad-accent shadow-glow"
                transition={{ type: 'spring', stiffness: 380, damping: 30 }}
              />
            )}
            <span className="relative flex items-center gap-2">
              {Icon && <Icon className="h-4 w-4" />}
              {tab.label}
              {tab.badge != null && tab.badge > 0 && (
                <span
                  className={cn(
                    'rounded-full px-1.5 text-[0.65rem] font-semibold',
                    isActive ? 'bg-bg/20 text-bg' : 'bg-white/10 text-ink-muted',
                  )}
                >
                  {tab.badge}
                </span>
              )}
            </span>
          </button>
        )
      })}
    </div>
  )
}
