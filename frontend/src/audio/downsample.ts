const TARGET_RATE = 16000
const FRAME_SAMPLES = 1600 // 100 ms at 16 kHz

export interface Downsampler {
  /** Feed mono Float32 samples; returns zero or more 100 ms PCM16LE frames (3200 bytes each). */
  push(samples: Float32Array): Uint8Array[]
}

function toInt16(sample: number): number {
  const clamped = Math.max(-1, Math.min(1, sample))
  return Math.round(clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff)
}

export function createDownsampler(inputRate: number): Downsampler {
  const ratio = inputRate / TARGET_RATE
  let input = new Float32Array(0)
  let position = 0 // fractional read position within `input`
  let out = new Int16Array(FRAME_SAMPLES)
  let outLen = 0

  return {
    push(samples) {
      const merged = new Float32Array(input.length + samples.length)
      merged.set(input)
      merged.set(samples, input.length)
      input = merged

      const frames: Uint8Array[] = []
      // Box filter: average every input sample that falls inside one output sample's window.
      while (Math.ceil(position + ratio) <= input.length) {
        const start = Math.floor(position)
        const end = Math.max(start + 1, Math.ceil(position + ratio))
        let sum = 0
        for (let i = start; i < end; i++) sum += input[i]
        out[outLen++] = toInt16(sum / (end - start))
        position += ratio
        if (outLen === FRAME_SAMPLES) {
          const bytes = new Uint8Array(FRAME_SAMPLES * 2)
          const view = new DataView(bytes.buffer)
          for (let i = 0; i < FRAME_SAMPLES; i++) view.setInt16(i * 2, out[i], true)
          frames.push(bytes)
          out = new Int16Array(FRAME_SAMPLES)
          outLen = 0
        }
      }
      const consumed = Math.floor(position)
      if (consumed > 0) {
        input = input.slice(consumed)
        position -= consumed
      }
      return frames
    },
  }
}
