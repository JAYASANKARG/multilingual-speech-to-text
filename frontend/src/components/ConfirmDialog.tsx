import Modal from './Modal'

interface Props {
  title: string
  message: string
  confirmLabel: string
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({ title, message, confirmLabel, busy, onConfirm, onCancel }: Props) {
  return (
    <Modal role="alertdialog" labelledBy="confirm-title" onClose={onCancel} initialFocus="[data-cancel]">
      <h2 id="confirm-title">{title}</h2>
      <p>{message}</p>
      <div className="modal-actions">
        <button data-cancel onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button className="danger" onClick={onConfirm} disabled={busy}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  )
}
