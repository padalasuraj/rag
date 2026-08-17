import { motion } from 'framer-motion'

/**
 * The signature visual: labeled source nodes stream into a central RAG core,
 * which emits a grounded, cited answer. Built as one self-contained, responsive
 * SVG with lightweight SMIL motion (no JS animation loop, respects reduced
 * motion via the global CSS rule).
 */
export function PipelineDiagram() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
      className="w-full"
      aria-hidden
    >
      <svg viewBox="0 0 560 420" className="h-auto w-full">
        <defs>
          <linearGradient id="core" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#00DBDE" />
            <stop offset="1" stopColor="#7C5CFF" />
          </linearGradient>
          <linearGradient id="stroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#00DBDE" stopOpacity="0.1" />
            <stop offset="1" stopColor="#7C5CFF" stopOpacity="0.5" />
          </linearGradient>
          <filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="8" />
          </filter>
        </defs>

        {/* Connectors (faint) */}
        <g fill="none" stroke="url(#stroke)" strokeWidth="1.5">
          <path id="p-pdf" d="M150 92 C 210 92, 210 210, 256 210" />
          <path id="p-yt" d="M150 210 L 256 210" />
          <path id="p-txt" d="M150 328 C 210 328, 210 210, 256 210" />
          <path id="p-out" d="M346 210 L 396 210" />
        </g>

        {/* Streaming data packets */}
        {[
          { p: '#p-pdf', delay: '0s', c: '#00DBDE' },
          { p: '#p-pdf', delay: '1.3s', c: '#00DBDE' },
          { p: '#p-yt', delay: '0.6s', c: '#00DBDE' },
          { p: '#p-txt', delay: '0.3s', c: '#7C5CFF' },
          { p: '#p-txt', delay: '1.6s', c: '#7C5CFF' },
        ].map((d, i) => (
          <circle key={i} r="3" fill={d.c}>
            <animateMotion dur="2.6s" begin={d.delay} repeatCount="indefinite" rotate="auto">
              <mpath href={d.p} />
            </animateMotion>
          </circle>
        ))}
        {/* Output packets */}
        {['0s', '1.1s'].map((delay, i) => (
          <circle key={`o${i}`} r="3" fill="#34D399">
            <animateMotion dur="2.2s" begin={delay} repeatCount="indefinite">
              <mpath href="#p-out" />
            </animateMotion>
          </circle>
        ))}

        {/* Source nodes */}
        <SourceNode x={24} y={70} label="PDF" sub="Documents" dot="#F5A3B7" />
        <SourceNode x={24} y={188} label="YouTube" sub="Transcripts" dot="#F87171" />
        <SourceNode x={24} y={306} label="Text" sub="Notes" dot="#00DBDE" />

        {/* RAG core */}
        <g>
          <circle cx="301" cy="210" r="52" fill="url(#core)" opacity="0.18" filter="url(#soft)" />
          {[0, 1].map((i) => (
            <circle
              key={i}
              cx="301"
              cy="210"
              r="46"
              fill="none"
              stroke="url(#core)"
              strokeWidth="1.5"
              opacity="0.6"
            >
              <animate attributeName="r" values="42;60" dur="3s" begin={`${i * 1.5}s`} repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.6;0" dur="3s" begin={`${i * 1.5}s`} repeatCount="indefinite" />
            </circle>
          ))}
          <polygon
            points="301,168 337,189 337,231 301,252 265,231 265,189"
            fill="rgba(10,17,32,0.9)"
            stroke="url(#core)"
            strokeWidth="2"
          />
          <text x="301" y="205" textAnchor="middle" className="fill-ink font-display" fontSize="15" fontWeight="600">
            RAG
          </text>
          <text x="301" y="222" textAnchor="middle" fill="#8A93A6" fontSize="8.5" letterSpacing="1.5">
            ENGINE
          </text>
        </g>

        {/* Grounded answer card */}
        <g transform="translate(396, 150)">
          <rect width="148" height="120" rx="14" fill="rgba(14,22,38,0.9)" stroke="rgba(255,255,255,0.1)" />
          <circle cx="18" cy="22" r="4" fill="#34D399" />
          <text x="30" y="26" fill="#34D399" fontSize="9" fontWeight="600" letterSpacing="0.5">
            GROUNDED
          </text>
          <rect x="16" y="40" width="116" height="6" rx="3" fill="rgba(230,237,246,0.5)" />
          <rect x="16" y="54" width="98" height="6" rx="3" fill="rgba(230,237,246,0.3)" />
          <rect x="16" y="68" width="108" height="6" rx="3" fill="rgba(230,237,246,0.3)" />
          {/* citation chips */}
          <rect x="16" y="88" width="52" height="18" rx="9" fill="rgba(0,219,222,0.12)" stroke="rgba(0,219,222,0.4)" />
          <text x="42" y="100" textAnchor="middle" fill="#00DBDE" fontSize="8">
            p.12
          </text>
          <rect x="74" y="88" width="58" height="18" rx="9" fill="rgba(124,92,255,0.12)" stroke="rgba(124,92,255,0.4)" />
          <text x="103" y="100" textAnchor="middle" fill="#B7A6FF" fontSize="8">
            18:42
          </text>
        </g>
      </svg>
    </motion.div>
  )
}

function SourceNode({
  x,
  y,
  label,
  sub,
  dot,
}: {
  x: number
  y: number
  label: string
  sub: string
  dot: string
}) {
  return (
    <g transform={`translate(${x}, ${y})`}>
      <rect width="126" height="44" rx="12" fill="rgba(14,22,38,0.9)" stroke="rgba(255,255,255,0.1)" />
      <circle cx="20" cy="22" r="5" fill={dot} />
      <text x="36" y="19" fill="#E6EDF6" fontSize="12" fontWeight="600">
        {label}
      </text>
      <text x="36" y="33" fill="#8A93A6" fontSize="9">
        {sub}
      </text>
    </g>
  )
}
