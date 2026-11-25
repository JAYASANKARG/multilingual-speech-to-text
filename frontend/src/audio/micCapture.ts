import { createDownsampler } from './downsample'

export type CaptureErrorKind = 'mic_denied' | 'mic_unavailable' | 'unsupported'

export class CaptureError extends Error {
  kind: CaptureErrorKind

  constructor(kind: CaptureErrorKind, message: string) {
    super(message)
    this.kind = kind
  }
}

export interface Capture {
  stop(): void
}

export async function startCapture(
  onFrame: (frame: ArrayBuffer) => void,
  onLevel?: (level: number) => void,
): Promise<Capture> {
  if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === 'undefined') {
    throw new CaptureError('unsupported', 'This browser cannot capture microphone audio.')
  }

  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    })
  } catch (err) {
    const name = err instanceof DOMException ? err.name : ''
    if (name === 'NotAllowedError' || name === 'SecurityError')
      throw new CaptureError('mic_denied', 'Microphone access was blocked.')
    throw new CaptureError('mic_unavailable', 'No microphone was found.')
  }

  const context = new AudioContext()
  try {
    await context.audioWorklet.addModule('/pcm-worklet.js')
  } catch {
    stream.getTracks().forEach((t) => t.stop())
    await context.close()
    throw new CaptureError('unsupported', 'This browser cannot process microphone audio.')
  }

  const source = context.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(context, 'pcm-capture')
  const mute = context.createGain()
  mute.gain.value = 0
  const downsampler = createDownsampler(context.sampleRate)
  node.port.onmessage = (event: MessageEvent<Float32Array>) => {
    if (onLevel) {
      const samples = event.data
      let sum = 0
      for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i]
      const rms = Math.sqrt(sum / samples.length)
      // dBFS mapped from −60 dB (silence) to 0 dB (clipping).
      onLevel(Math.min(1, Math.max(0, (20 * Math.log10(rms + 1e-6) + 60) / 60)))
    }
    for (const frame of downsampler.push(event.data)) {
      onFrame(frame.buffer.slice(frame.byteOffset, frame.byteOffset + frame.byteLength) as ArrayBuffer)
    }
  }
  source.connect(node)
  node.connect(mute).connect(context.destination)
  if (context.state === 'suspended') await context.resume()

  return {
    stop() {
      node.port.onmessage = null
      source.disconnect()
      node.disconnect()
      stream.getTracks().forEach((t) => t.stop())
      void context.close()
    },
  }
}
