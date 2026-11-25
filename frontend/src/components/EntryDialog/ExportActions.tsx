import { useState } from 'react'

interface Props {
  text: string
  createdAt: string
}

function exportFilename(createdAt: string): string {
  const stamp = new Date(createdAt).toISOString().replace(/[-:]/g, '').slice(0, 15)
  return `transcription-${stamp}.txt`
}

export default function ExportActions({ text, createdAt }: Props) {
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const copy = async () => {
    setError(null)
    if (!navigator.clipboard?.writeText) {
      setError('Copying is not available here. Select the text and copy it manually.')
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Copying was blocked. Select the text and copy it manually.')
    }
  }

  const download = () => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = exportFilename(createdAt)
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="export-actions">
      <button onClick={copy}>Copy</button>
      <button onClick={download}>Download .txt</button>
      {copied && <span role="status">Copied</span>}
      {error && <span role="alert">{error}</span>}
    </div>
  )
}
