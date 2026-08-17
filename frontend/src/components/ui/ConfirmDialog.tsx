import { AlertTriangle } from 'lucide-react'
import { Modal } from './Modal'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  busy?: boolean
  onConfirm: () => void
  onClose: () => void
}

/**
 * Small confirmation dialog for destructive or irreversible actions
 * (delete a knowledge base, remove a source, clear a conversation).
 */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  busy = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} className="max-w-md">
      <div className="flex gap-4">
        {destructive && (
          <div className="mt-0.5 flex h-10 w-10 flex-none items-center justify-center rounded-xl border border-danger/30 bg-danger/10">
            <AlertTriangle className="h-5 w-5 text-danger" />
          </div>
        )}
        <div className="flex-1">
          <h2 className="font-display text-lg font-semibold">{title}</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{message}</p>
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose} disabled={busy}>
          {cancelLabel}
        </button>
        <button
          className={destructive ? 'btn-danger-ghost' : 'btn-primary'}
          onClick={onConfirm}
          disabled={busy}
        >
          {confirmLabel}
        </button>
      </div>
    </Modal>
  )
}
