/**
 * Zustand store for game state
 */

import { create } from 'zustand'
import type { Observation, ObservationResponse, GameState as ComparisonGameState, ComparisonStats, FinalGameStats } from '../types/protocol'

interface GameState {
  // Mode
  mode: 'single' | 'compare'

  // Single player state
  observation: Observation | null
  reward: number
  done: boolean
  info: Record<string, any>

  // Connection state
  isConnected: boolean
  isPaused: boolean

  // AI state (single player)
  isAIPlaying: boolean
  selectedAgent: 'random' | 'dellacherie'
  playbackSpeed: number

  // Comparison mode state
  isComparing: boolean
  comparisonAgent1: 'random' | 'dellacherie'
  comparisonAgent2: 'random' | 'dellacherie'
  comparisonSpeed: number
  comparisonMaxPieces: number
  comparisonSeed: number
  game1: ComparisonGameState | null
  game2: ComparisonGameState | null
  comparisonStats: ComparisonStats | null
  comparisonComplete: { winner: 'agent1' | 'agent2' | null; game1: FinalGameStats; game2: FinalGameStats } | null

  // Actions
  setMode: (mode: 'single' | 'compare') => void
  setObservation: (response: ObservationResponse) => void
  setConnected: (connected: boolean) => void
  setPaused: (paused: boolean) => void
  setAIPlaying: (playing: boolean) => void
  setSelectedAgent: (agent: 'random' | 'dellacherie') => void
  setPlaybackSpeed: (speed: number) => void

  // Comparison actions
  setComparing: (comparing: boolean) => void
  setComparisonAgent1: (agent: 'random' | 'dellacherie') => void
  setComparisonAgent2: (agent: 'random' | 'dellacherie') => void
  setComparisonSpeed: (speed: number) => void
  setComparisonMaxPieces: (pieces: number) => void
  setComparisonSeed: (seed: number) => void
  setComparisonState: (game1: ComparisonGameState, game2: ComparisonGameState, stats: ComparisonStats) => void
  setComparisonComplete: (winner: 'agent1' | 'agent2' | null, game1: FinalGameStats, game2: FinalGameStats) => void
  clearComparisonComplete: () => void

  reset: () => void
}

export const useGameStore = create<GameState>((set) => ({
  // Initial state - Mode
  mode: 'single',

  // Initial state - Single player
  observation: null,
  reward: 0,
  done: false,
  info: {},
  isConnected: false,
  isPaused: false,
  isAIPlaying: false,
  selectedAgent: 'dellacherie',
  playbackSpeed: 1.0,

  // Initial state - Comparison
  isComparing: false,
  comparisonAgent1: 'random',
  comparisonAgent2: 'dellacherie',
  comparisonSpeed: 1.0,
  comparisonMaxPieces: 1000,
  comparisonSeed: Date.now(),
  game1: null,
  game2: null,
  comparisonStats: null,
  comparisonComplete: null,

  // Mode actions
  setMode: (mode) =>
    set({ mode }),

  // Single player actions
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

  setAIPlaying: (playing) =>
    set({ isAIPlaying: playing }),

  setSelectedAgent: (agent) =>
    set({ selectedAgent: agent }),

  setPlaybackSpeed: (speed) =>
    set({ playbackSpeed: speed }),

  // Comparison actions
  setComparing: (comparing) =>
    set({ isComparing: comparing }),

  setComparisonAgent1: (agent) =>
    set({ comparisonAgent1: agent }),

  setComparisonAgent2: (agent) =>
    set({ comparisonAgent2: agent }),

  setComparisonSpeed: (speed) =>
    set({ comparisonSpeed: speed }),

  setComparisonMaxPieces: (pieces) =>
    set({ comparisonMaxPieces: pieces }),

  setComparisonSeed: (seed) =>
    set({ comparisonSeed: seed }),

  setComparisonState: (game1, game2, stats) =>
    set({
      game1,
      game2,
      comparisonStats: stats,
    }),

  setComparisonComplete: (winner, game1Stats, game2Stats) => {
    console.log('Setting comparison complete:', { winner, game1Stats, game2Stats })
    set({
      isComparing: false,
      comparisonComplete: {
        winner,
        game1: game1Stats,
        game2: game2Stats,
      },
    })
  },

  clearComparisonComplete: () =>
    set({ comparisonComplete: null }),

  reset: () =>
    set({
      observation: null,
      reward: 0,
      done: false,
      info: {},
      isAIPlaying: false,
      game1: null,
      game2: null,
      comparisonStats: null,
      comparisonComplete: null,
    }),
}))
