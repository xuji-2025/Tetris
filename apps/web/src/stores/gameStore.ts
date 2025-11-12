/**
 * Zustand store for game state
 */

import { create } from 'zustand'
import type { Observation, ObservationResponse } from '../types/protocol'

interface GameState {
  // Current observation
  observation: Observation | null
  reward: number
  done: boolean
  info: Record<string, any>

  // Connection state
  isConnected: boolean
  isPaused: boolean

  // Actions
  setObservation: (response: ObservationResponse) => void
  setConnected: (connected: boolean) => void
  setPaused: (paused: boolean) => void
  reset: () => void
}

export const useGameStore = create<GameState>((set) => ({
  // Initial state
  observation: null,
  reward: 0,
  done: false,
  info: {},
  isConnected: false,
  isPaused: false,

  // Actions
  setObservation: (response) =>
    set({
      observation: response.data,
      reward: response.reward,
      done: response.done,
      info: response.info,
    }),

  setConnected: (connected) =>
    set({ isConnected: connected }),

  setPaused: (paused) =>
    set({ isPaused: paused }),

  reset: () =>
    set({
      observation: null,
      reward: 0,
      done: false,
      info: {},
    }),
}))
