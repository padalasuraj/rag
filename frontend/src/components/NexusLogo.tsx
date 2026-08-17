import { cn } from '@/utils'

export function NexusMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={cn('h-7 w-7', className)}>
      <defs>
        <linearGradient id="nexusMark" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop stopColor="#00DBDE" />
          <stop offset="1" stopColor="#7C5CFF" />
        </linearGradient>
      </defs>
      <path
        d="M32 6 L54 19 V45 L32 58 L10 45 V19 Z"
        stroke="url(#nexusMark)"
        strokeWidth="2.5"
        fill="rgba(0,219,222,0.06)"
        strokeLinejoin="round"
      />
      <g stroke="url(#nexusMark)" strokeWidth="2" strokeLinecap="round" opacity="0.9">
        <line x1="32" y1="32" x2="32" y2="12" />
        <line x1="32" y1="32" x2="49" y2="42" />
        <line x1="32" y1="32" x2="15" y2="42" />
      </g>
      <circle cx="32" cy="12" r="3.5" fill="#00DBDE" />
      <circle cx="49" cy="42" r="3.5" fill="#7C5CFF" />
      <circle cx="15" cy="42" r="3.5" fill="#7C5CFF" />
      <circle cx="32" cy="32" r="6" fill="url(#nexusMark)" />
    </svg>
  )
}

export function NexusLogo({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <NexusMark />
      <span className="font-display text-lg font-semibold tracking-tight">
        Nexus<span className="text-gradient">RAG</span>
      </span>
    </div>
  )
}
