const KEY = 'stt-consent'

export function hasConsent(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

export function saveConsent(): void {
  try {
    localStorage.setItem(KEY, '1')
  } catch {
    // storage unavailable: the notice will simply show again next time
  }
}
