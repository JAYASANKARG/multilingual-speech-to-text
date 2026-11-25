import { ShieldIcon } from './icons'
import Modal from './Modal'

interface Props {
  onAccept: () => void
  onDecline: () => void
}

export default function PrivacyNotice({ onAccept, onDecline }: Props) {
  return (
    <Modal labelledBy="privacy-title" onClose={onDecline} initialFocus="[data-accept]">
      <div className="privacy-head">
        <span className="privacy-mark" aria-hidden="true">
          <ShieldIcon />
        </span>
        <div>
          <p className="eyebrow">Privacy</p>
          <h2 id="privacy-title">Before you record</h2>
        </div>
      </div>
      <p className="privacy-copy">
        Your voice is streamed to Google&apos;s Gemini speech service to be turned into text. We
        never store the audio, only the text.
      </p>
      <p className="privacy-copy">
        This app uses Gemini&apos;s free tier, and Google may use free-tier data to improve its
        products. Avoid saying anything private or sensitive.
      </p>
      <div className="modal-actions">
        <button onClick={onDecline}>No thanks</button>
        <button className="primary" onClick={onAccept} data-accept>
          I understand
        </button>
      </div>
    </Modal>
  )
}
