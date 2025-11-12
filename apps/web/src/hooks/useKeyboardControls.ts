/**
 * Keyboard controls for Tetris
 */

import { useEffect } from 'react'
import type { FrameAction } from '../types/protocol'

interface UseKeyboardControlsProps {
  onAction: (action: FrameAction) => void
  enabled?: boolean
}

const KEY_MAP: Record<string, FrameAction> = {
  ArrowLeft: 'LEFT',
  ArrowRight: 'RIGHT',
  ArrowDown: 'SOFT',
  ArrowUp: 'HARD', // Alternative for hard drop
  ' ': 'HARD', // Space for hard drop
  z: 'CCW', // Z for counter-clockwise
  Z: 'CCW',
  x: 'CW', // X for clockwise
  X: 'CW',
  Shift: 'HOLD', // Shift for hold
  c: 'HOLD', // C for hold (alternative)
  C: 'HOLD',
}

export function useKeyboardControls({
  onAction,
  enabled = true,
}: UseKeyboardControlsProps) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      const action = KEY_MAP[event.key]

      if (action) {
        event.preventDefault()
        onAction(action)
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onAction, enabled])
}
