import { useEffect, useRef } from 'react'

const BAR_COUNT = 28

// A fixed bell shape, taller toward the middle, with deterministic jitter so the ribbon reads as
// a real meter rather than a row of identical bars.
const SHAPE = Array.from({ length: BAR_COUNT }, (_, i) => {
  const centre = (BAR_COUNT - 1) / 2
  const distance = Math.abs(i - centre) / centre
  return 0.32 + 0.68 * (1 - distance) ** 0.85
})

const JITTER = Array.from({ length: BAR_COUNT }, (_, i) => 0.84 + 0.16 * Math.abs(Math.sin(i * 12.9898)))

interface Props {
  /** Latest 0..1 microphone level. Undefined falls back to a resting meter. */
  levelRef?: { current: number }
  active: boolean
}

const RESTING = (i: number) => 0.1 + 0.32 * SHAPE[i] * JITTER[i]

export default function LevelRibbon({ levelRef, active }: Props) {
  const bars = useRef<Array<HTMLSpanElement | null>>([])

  useEffect(() => {
    const nodes = bars.current
    if (!nodes.length) return

    const paint = (i: number, value: number) => {
      nodes[i]?.style.setProperty('transform', `scaleY(${value.toFixed(3)})`)
    }

    if (!active) {
      for (let i = 0; i < nodes.length; i++) paint(i, RESTING(i))
      return
    }

    let frame = 0
    let last = 0
    let smoothed = 0

    const tick = (now: number) => {
      frame = requestAnimationFrame(tick)
      if (now - last < 33) return
      last = now

      const level = Math.max(0, Math.min(1, levelRef?.current ?? 0))
      smoothed += (level - smoothed) * 0.22
      for (let i = 0; i < nodes.length; i++) {
        const wobble = 0.92 + 0.08 * Math.sin(now / 130 + i * 0.7)
        const target = 0.12 + smoothed * 0.88 * SHAPE[i] * JITTER[i] * wobble
        paint(i, Math.max(0.1, Math.min(1, target)))
      }
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [active, levelRef])

  return (
    <span className={`level${active ? ' is-active' : ''}`} aria-hidden="true">
      {SHAPE.map((_, i) => (
        <span
          key={i}
          ref={(node) => {
            bars.current[i] = node
          }}
          className="level-bar"
          style={{ transform: `scaleY(${RESTING(i).toFixed(3)})` }}
        />
      ))}
    </span>
  )
}
