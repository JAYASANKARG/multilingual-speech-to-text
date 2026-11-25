import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { hasConsent, saveConsent } from '../lib/consent'
import PrivacyNotice from './PrivacyNotice'

describe('PrivacyNotice', () => {
  it('states where audio goes and that free-tier data may be used by Google', () => {
    render(<PrivacyNotice onAccept={() => {}} onDecline={() => {}} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent(/Gemini/)
    expect(dialog).toHaveTextContent(/improve/i)
  })

  it('calls onAccept / onDecline', async () => {
    const onAccept = vi.fn()
    const onDecline = vi.fn()
    render(<PrivacyNotice onAccept={onAccept} onDecline={onDecline} />)
    await userEvent.click(screen.getByRole('button', { name: /no thanks/i }))
    expect(onDecline).toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: /i understand/i }))
    expect(onAccept).toHaveBeenCalled()
  })

  it('remembers consent and survives broken storage', () => {
    localStorage.clear()
    expect(hasConsent()).toBe(false)
    saveConsent()
    expect(hasConsent()).toBe(true)
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(hasConsent()).toBe(false)
    spy.mockRestore()
  })
})
