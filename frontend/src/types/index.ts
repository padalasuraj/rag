export type SourceType = 'pdf' | 'youtube' | 'text'
export type SourceStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface SourceCounts {
  total: number
  pdf: number
  youtube: number
  text: number
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string
  is_demo: boolean
  created_at: string
  updated_at: string
  source_counts: SourceCounts
  chunk_count: number
}

export interface Source {
  id: string
  knowledge_base_id: string
  source_type: SourceType
  title: string
  status: SourceStatus
  error?: string | null
  num_chunks: number
  meta: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Citation {
  index: number
  source_id: string
  chunk_id: string
  source_type: SourceType
  title: string
  snippet: string
  score: number
  page?: number | null
  start_seconds?: number | null
  section?: string | null
  url?: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  created_at?: string
  grounded?: boolean
  relatedQuestions?: string[]
  streaming?: boolean
}

export interface QuizOption {
  label: string
  text: string
}

export interface QuizQuestion {
  question: string
  options: QuizOption[]
  correct_label: string
  explanation: string
  citation?: Citation | null
}

export interface QuizResponse {
  questions: QuizQuestion[]
}

export interface SourceUsage {
  source_id: string
  title: string
  source_type: SourceType
  query_hits: number
}

export interface Analytics {
  knowledge_base_id: string
  total_sources: number
  total_chunks: number
  questions_asked: number
  grounded_answer_rate: number
  avg_retrieval_score: number
  avg_latency_ms: number
  most_queried_sources: SourceUsage[]
}

export interface Health {
  status: string
  app: string
  environment: string
  vector_store: string
  llm_model: string
  embedding_model: string
  openai_key_present: boolean
}
