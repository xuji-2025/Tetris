/**
 * WebSocket client hook for TetrisCore server
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import type {
  ServerMessage,
  ObservationResponse,
  ErrorResponse,
  FrameAction,
  CompareObsResponse,
  CompareCompleteResponse,
} from '../types/protocol'

interface UseGameConnectionProps {
  url: string
  onObservation?: (data: ObservationResponse) => void
  onCompareObs?: (data: CompareObsResponse) => void
  onCompareComplete?: (data: CompareCompleteResponse) => void
  onError?: (error: ErrorResponse) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useGameConnection({
  url,
  onObservation,
  onCompareObs,
  onCompareComplete,
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
        } else if (message.type === 'compare_obs') {
          onCompareObs?.(message)
        } else if (message.type === 'compare_complete') {
          onCompareComplete?.(message)
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

  // Start AI play
  const aiPlay = useCallback((agentType: 'random' | 'dellacherie', speed: number = 1.0, seed?: number) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'ai_play',
          agent_type: agentType,
          speed,
          seed,
          max_pieces: 1000,
        })
      )
    }
  }, [])

  // Stop AI play
  const aiStop = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'ai_stop',
        })
      )
    }
  }, [])

  // Start comparison mode
  const compareStart = useCallback((
    agent1: string,
    agent2: string,
    speed: number,
    maxPieces: number,
    seed?: number
  ) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'compare_start',
          agent1,
          agent2,
          speed,
          max_pieces: maxPieces,
          seed,
        })
      )
    }
  }, [])

  // Stop comparison mode
  const compareStop = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'compare_stop',
        })
      )
    }
  }, [])

  // Set comparison speed
  const compareSetSpeed = useCallback((speed: number) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(
        JSON.stringify({
          type: 'compare_set_speed',
          speed,
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
    aiPlay,
    aiStop,
    compareStart,
    compareStop,
    compareSetSpeed,
  }
}
