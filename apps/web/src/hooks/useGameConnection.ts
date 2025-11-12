/**
 * WebSocket client hook for TetrisCore server
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import type {
  ServerMessage,
  ObservationResponse,
  ErrorResponse,
  FrameAction,
} from '../types/protocol'

interface UseGameConnectionProps {
  url: string
  onObservation?: (data: ObservationResponse) => void
  onError?: (error: ErrorResponse) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useGameConnection({
  url,
  onObservation,
  onError,
  onConnect,
  onDisconnect,
}: UseGameConnectionProps) {
  const ws = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Connect to WebSocket
  useEffect(() => {
    const socket = new WebSocket(url)

    const connectHandler = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      setConnectionError(null)

      // Send hello
      socket.send(
        JSON.stringify({
          type: 'hello',
          version: 's1.0.0',
        })
      )

      onConnect?.()
    }

    const messageHandler = (event: MessageEvent) => {
      try {
        const message: ServerMessage = JSON.parse(event.data)

        if (message.type === 'hello') {
          console.log('Server handshake:', message)
        } else if (message.type === 'obs') {
          onObservation?.(message)
        } else if (message.type === 'error') {
          console.error('Server error:', message)
          onError?.(message)
        }
      } catch (err) {
        console.error('Failed to parse message:', err)
      }
    }

    const errorHandler = (error: Event) => {
      console.error('WebSocket error:', error)
      setConnectionError('Connection error')
    }

    const closeHandler = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      onDisconnect?.()
    }

    socket.onopen = connectHandler
    socket.onmessage = messageHandler
    socket.onerror = errorHandler
    socket.onclose = closeHandler

    ws.current = socket

    return () => {
      socket.close()
    }
    // Only reconnect if URL changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])

  // Send reset request
  const reset = useCallback((seed?: number) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'reset',
          seed,
        })
      )
    }
  }, [])

  // Send step request
  const step = useCallback((action: FrameAction) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'step',
          action,
        })
      )
    }
  }, [])

  // Subscribe to streaming mode
  const subscribe = useCallback((stream: boolean = true) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'subscribe',
          stream,
        })
      )
    }
  }, [])

  return {
    isConnected,
    connectionError,
    reset,
    step,
    subscribe,
  }
}
