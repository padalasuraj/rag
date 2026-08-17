import { Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Modal } from '@/components/ui/Modal'
import { useAppStore } from '@/stores/useAppStore'

/**
 * Modal for creating a new knowledge base. Rendered once in the AppShell and
 * driven by shared store state so both the sidebar and the dashboard can open it.
 */
export function CreateKBModal() {
  const open = useAppStore((s) => s.createKbOpen)
  const close = useAppStore((s) => s.closeCreateKb)
  const createKnowledgeBase = useAppStore((s) => s.createKnowledgeBase)
  const toast = useAppStore((s) => s.toast)
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Reset the form whenever the modal is (re)opened.
  useEffect(() => {
    if (open) {
      setName('')
      setDescription('')
      setSubmitting(false)
    }
  }, [open])

  const submit = async () => {
    const trimmed = name.trim()
    if (!trimmed || submitting) return
    setSubmitting(true)
    try {
      const kb = await createKnowledgeBase(trimmed, description.trim())
      toast(`Created “${kb.name}”.`, 'success')
      close()
      navigate(`/app/kb/${kb.id}`)
    } catch (e: any) {
      toast(e.message || 'Could not create knowledge base.', 'error')
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} onClose={close} title="New knowledge base">
      <div className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-muted">
            Name
          </label>
          <input
            autoFocus
            className="input"
            placeholder="e.g. Machine Learning Course"
            value={name}
            maxLength={120}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-muted">
            Description <span className="text-ink-dim">(optional)</span>
          </label>
          <textarea
            className="input min-h-[84px] resize-none"
            placeholder="What is this collection of sources about?"
            value={description}
            maxLength={400}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <button className="btn-ghost" onClick={close} disabled={submitting}>
          Cancel
        </button>
        <button className="btn-primary" onClick={submit} disabled={!name.trim() || submitting}>
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Create
        </button>
      </div>
    </Modal>
  )
}
