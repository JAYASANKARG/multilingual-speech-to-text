import { describe, expect, it } from 'vitest'
import { createDownsampler } from './downsample'

function tone(n: number, value: number): Float32Array {
  return new Float32Array(n).fill(value)
}

describe('downsampler', () => {
  it('emits 3200-byte frames (100 ms) at 16 kHz from 48 kHz input', () => {
    const d = createDownsampler(48000)
    const frames = d.push(tone(4800, 0.25))
    expect(frames).toHaveLength(1)
    expect(frames[0].byteLength).toBe(3200)
  })

  it('handles 44.1 kHz input', () => {
    const d = createDownsampler(44100)
    let bytes = 0
    for (let i = 0; i < 10; i++) for (const f of d.push(tone(4410, 0.1))) bytes += f.byteLength
    expect(bytes).toBeGreaterThanOrEqual(3200 * 9)
    expect(bytes).toBeLessThanOrEqual(3200 * 10)
  })

  it('passes 16 kHz audio through as little-endian signed 16-bit', () => {
    const d = createDownsampler(16000)
    const input = new Float32Array(1600)
    input[0] = 0.5
    input[1] = -0.5
    const [frame] = d.push(input)
    const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength)
    expect(Math.abs(view.getInt16(0, true) - 16384)).toBeLessThanOrEqual(1)
    expect(Math.abs(view.getInt16(2, true) + 16384)).toBeLessThanOrEqual(1)
  })

  it('clamps out-of-range samples', () => {
    const d = createDownsampler(16000)
    const input = new Float32Array(1600)
    input[0] = 3
    input[1] = -3
    const [frame] = d.push(input)
    const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength)
    expect(view.getInt16(0, true)).toBe(32767)
    expect(view.getInt16(2, true)).toBe(-32768)
  })

  it('carries leftovers across pushes', () => {
    const d = createDownsampler(16000)
    expect(d.push(tone(800, 0.1))).toHaveLength(0)
    expect(d.push(tone(800, 0.1))).toHaveLength(1)
  })
})
