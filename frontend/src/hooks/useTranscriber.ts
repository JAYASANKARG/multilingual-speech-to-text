import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { wsUrl } from '../api/client'
import type { ServerMessage } from '../api/types'
import { CaptureError, startCapture, type Capture } from '../audio/micCapture'
import { initialState, reducer } from './transcriptReducer'

const MAX_BUFFERED_FRAMES = 50
const SLOW_CONNECT_MS = 5000

export function useTranscriber() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [slowConnect, setSlowConnect] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const captureRef = useRef<Capture | null>(null)
  const listeningRef = useRef(false)
  const bufferRef = useRef<ArrayBuffer[]>([])

  const teardown = useCallback(() => {
    captureRef.current?.stop()
    captureRef.current = null
    listeningRef.current = false
    bufferRef.current = []
    const ws = wsRef.current
    wsRef.current = null
    if (ws) {
      ws.onclose = null
      ws.onmessage = null
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close()
    }
  }, [])

  useEffect(() => teardown, [teardown])

  useEffect(() => {
    if (state.state !== 'connecting') return
    const timer = setTimeout(() => setSlowConnect(true), SLOW_CONNECT_MS)
    return () => clearTimeout(timer)
  }, [state.state])

  const start = useCallback(
    async (language: string = 'auto') => {
      teardown()
      setSlowConnect(false)
      dispatch({ type: 'start' })

      // Ask for the microphone first so a denial never opens a server session.
      const sendFrame = (frame: ArrayBuffer) => {
        const ws = wsRef.current
        if (listeningRef.current && ws?.readyState === WebSocket.OPEN) ws.send(frame)
        else if (bufferRef.current.length < MAX_BUFFERED_FRAMES) bufferRef.current.push(frame)
      }
      try {
        captureRef.current = await startCapture(sendFrame)
      } catch (err) {
        const kind = err instanceof CaptureError ? err.kind : 'mic_unavailable'
        const message = err instanceof Error ? err.message : 'Microphone unavailable.'
        dispatch({ type: 'local_error', error: { code: kind, message } })
        return
      }

      const ws = new WebSocket(wsUrl(`/api/ws/transcribe?language=${encodeURIComponent(language)}`))
      wsRef.current = ws
      ws.onmessage = (event: MessageEvent<string>) => {
        let msg: ServerMessage
        try {
          msg = JSON.parse(event.data) as ServerMessage
        } catch {
          return
        }
        if (msg.type === 'state' && msg.state === 'listening') {
          listeningRef.current = true
          for (const frame of bufferRef.current) ws.send(frame)
          bufferRef.current = []
        }
        if (msg.type === 'ended' || msg.type === 'error') {
          captureRef.current?.stop()
          captureRef.current = null
        }
        dispatch({ type: 'server', msg })
      }
      ws.onclose = () => {
        captureRef.current?.stop()
        captureRef.current = null
        dispatch({ type: 'socket_closed' })
      }
      ws.onerror = () => {
        // onclose follows and reports the loss
      }
    },
    [teardown],
  )

  const stop = useCallback(() => {
    captureRef.current?.stop()
    captureRef.current = null
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
  }, [])

  const reset = useCallback(() => {
    teardown()
    dispatch({ type: 'reset' })
  }, [teardown])

  return { ...state, slowConnect, start, stop, reset }
}
