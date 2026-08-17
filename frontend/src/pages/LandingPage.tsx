import { motion } from 'framer-motion'
import {
  ArrowRight,
  BadgeCheck,
  Boxes,
  Database,
  FileText,
  GraduationCap,
  Quote,
  Sparkles,
  Youtube,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { PipelineDiagram } from '@/components/landing/PipelineDiagram'
import { NexusLogo } from '@/components/NexusLogo'

const FEATURES = [
  {
    icon: Boxes,
    title: 'One knowledge base, many sources',
    body: 'Mix PDFs, YouTube videos, and pasted notes in a single searchable base. Ask once, search across all of them.',
  },
  {
    icon: BadgeCheck,
    title: 'Grounded answers, not guesses',
    body: 'Answers come only from your sources. When the material does not cover something, NexusRAG says so instead of inventing it.',
  },
  {
    icon: Quote,
    title: 'Citations you can open',
    body: 'Every answer links back to the exact PDF page or the exact second in a video, so you can verify it in one click.',
  },
  {
    icon: Sparkles,
    title: 'Retrieval that actually retrieves',
    body: 'Semantic search over embeddings, a relevance threshold, and MMR reranking send the model the right context — not noise.',
  },
  {
    icon: GraduationCap,
    title: 'Study, not just search',
    body: 'Turn any source into summaries, key points, plain-English explanations, or an interactive quiz — all grounded in the text.',
  },
  {
    icon: Database,
    title: 'Your infrastructure, your call',
    body: 'Runs locally on ChromaDB out of the box; switch to Pinecone with one environment variable. Nothing else changes.',
  },
]

const STEPS = [
  { n: '01', title: 'Add sources', body: 'Upload PDFs, drop a YouTube link, or paste text.' },
  { n: '02', title: 'Chunk & embed', body: 'Content is cleaned, split, and turned into vectors.' },
  { n: '03', title: 'Retrieve & rerank', body: 'The most relevant passages are selected per question.' },
  { n: '04', title: 'Answer & cite', body: 'A grounded answer streams back with clickable sources.' },
]

export function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-bg/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <NexusLogo />
          <nav className="flex items-center gap-2">
            <a href="#features" className="hidden rounded-lg px-3 py-2 text-sm text-ink-muted transition hover:text-ink sm:block">
              Features
            </a>
            <a href="#how" className="hidden rounded-lg px-3 py-2 text-sm text-ink-muted transition hover:text-ink sm:block">
              How it works
            </a>
            <Link to="/app" className="btn-primary">
              Launch app <ArrowRight className="h-4 w-4" />
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-5 pb-20 pt-14 sm:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="chip mb-5"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Retrieval-Augmented Generation, done right
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.05 }}
              className="font-display text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl"
            >
              Turn your knowledge into an <span className="text-gradient">AI assistant</span>.
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.12 }}
              className="mt-5 max-w-xl text-lg leading-relaxed text-ink-muted"
            >
              Upload documents, connect YouTube videos, or paste your own content.
              Ask questions and get answers grounded in your sources — every claim
              backed by a citation you can open.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.18 }}
              className="mt-8 flex flex-wrap items-center gap-3"
            >
              <Link to="/app" className="btn-primary px-5 py-3 text-base">
                Start building <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/app" className="btn-ghost px-5 py-3 text-base">
                Explore the demo
              </Link>
            </motion.div>
            <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-dim">
              <span className="flex items-center gap-1.5">
                <FileText className="h-4 w-4" /> PDF
              </span>
              <span className="flex items-center gap-1.5">
                <Youtube className="h-4 w-4" /> YouTube
              </span>
              <span className="flex items-center gap-1.5">
                <Sparkles className="h-4 w-4" /> Grounded answers
              </span>
            </div>
          </div>

          <div className="card p-4 sm:p-6">
            <PipelineDiagram />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-6xl px-5 py-16">
        <SectionHeading eyebrow="Pipeline" title="From source to cited answer" />
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.4, delay: i * 0.06 }}
              className="card p-5"
            >
              <div className="font-mono text-sm text-accent">{s.n}</div>
              <h3 className="mt-3 font-display font-semibold">{s.title}</h3>
              <p className="mt-1.5 text-sm text-ink-muted">{s.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-5 py-16">
        <SectionHeading
          eyebrow="Why NexusRAG"
          title="Built like a product, not a demo"
        />
        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="card group p-6 transition hover:border-accent/30"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-grad-accent-soft ring-1 ring-white/10">
                <f.icon className="h-5 w-5 text-accent" />
              </div>
              <h3 className="mt-4 font-display text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Grounded showcase */}
      <section className="mx-auto max-w-6xl px-5 py-16">
        <SectionHeading
          eyebrow="Trust"
          title="It tells you when it doesn't know"
        />
        <div className="mt-10 grid gap-4 lg:grid-cols-2">
          <div className="card p-6">
            <p className="text-sm font-medium text-ink-muted">You ask</p>
            <p className="mt-1 text-ink">
              What are the advantages of logistic regression?
            </p>
            <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <p className="prose-chat">
                Logistic regression is simple, fast to train, and highly
                interpretable, and it outputs calibrated probabilities rather than
                just a label <span className="text-accent">[1]</span>.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="chip text-accent">
                  <FileText className="h-3 w-3" /> Regression&nbsp;Basics — p.1
                </span>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <p className="text-sm font-medium text-ink-muted">You ask</p>
            <p className="mt-1 text-ink">What did the CEO say about 2027 revenue?</p>
            <div className="mt-4 rounded-xl border border-warn/25 bg-warn/[0.06] p-4">
              <p className="text-sm text-warn/90">
                I couldn't find enough information about this in the provided
                sources.
              </p>
            </div>
            <p className="mt-3 text-sm text-ink-dim">
              No fabricated numbers, no invented quotes — just an honest answer.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-5 py-20">
        <div className="card relative overflow-hidden p-10 text-center sm:p-16">
          <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-accent/20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-violet/20 blur-3xl" />
          <h2 className="relative font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Build your knowledge assistant in minutes.
          </h2>
          <p className="relative mx-auto mt-3 max-w-lg text-ink-muted">
            Create a knowledge base, add a few sources, and start asking. Runs
            locally with a single API key.
          </p>
          <Link to="/app" className="btn-primary relative mt-8 px-6 py-3 text-base">
            Launch NexusRAG <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-white/5">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row">
          <NexusLogo />
          <p className="text-sm text-ink-dim">
            A portfolio project demonstrating production-grade RAG.
          </p>
        </div>
      </footer>
    </div>
  )
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="max-w-2xl">
      <div className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-accent">
        {eyebrow}
      </div>
      <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
        {title}
      </h2>
    </div>
  )
}
