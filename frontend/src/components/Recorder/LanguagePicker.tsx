import type { Language } from '../../api/types'

interface Props {
  languages: Language[]
  value: string
  onChange: (code: string) => void
  disabled?: boolean
}

export default function LanguagePicker({ languages, value, onChange, disabled }: Props) {
  return (
    <label className="language-picker">
      <span>Language</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code} disabled={!lang.pinnable}>
            {lang.pinnable ? lang.name : `${lang.name} (auto-detect only)`}
          </option>
        ))}
      </select>
    </label>
  )
}
