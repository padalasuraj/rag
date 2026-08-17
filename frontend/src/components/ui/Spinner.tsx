import { cn } from '@/utils'

/** Minimal accent-colored spinner. Size in Tailwind h/w units via `className`. */
export function Spinner({ className }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={cn(
        'inline-block animate-spin rounded-full border-2 border-white/15 border-t-accent',
        'h-4 w-4',
        className,
      )}
    />
  )
}
