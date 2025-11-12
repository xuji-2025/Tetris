import React, { useCallback, useEffect, useMemo } from 'react'
import { useGameConnection } from './hooks/useGameConnection'
import { useKeyboardControls } from './hooks/useKeyboardControls'
import { useGameStore } from './stores/gameStore'
import { GameBoard } from './components/GameBoard'
import { NextPanel, HoldPanel, ScorePanel, InspectorPanel } from './components/GameInfo'
import './App.css'

const WS_URL = 'ws://localhost:8000/ws'

function App() {
  const {
    observation,
    done,
    info,
    setObservation,
    setConnected,
  } = useGameStore()

  // WebSocket connection
  const { isConnected, reset, step } = useGameConnection({
    url: WS_URL,
    onObservation: setObservation,
    onConnect: () => {
      setConnected(true)
    },
    onDisconnect: () => setConnected(false),
    onError: (error) => console.error('Game error:', error),
  })

  // Game loop - tick the engine at 60Hz
  // Only start after we have an observation (game has been initialized)
  useEffect(() => {
    if (!isConnected || !observation || done) return

    const interval = setInterval(() => {
      step('NOOP')
    }, 1000 / 60) // 60 FPS

    return () => clearInterval(interval)
  }, [isConnected, observation, done]) // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard controls
  useKeyboardControls({
    onAction: step,
    enabled: isConnected && !done,
  })

  // Compute ghost position
  const ghostY = useMemo(() => {
    if (!observation?.current || !observation?.legal_moves) return undefined

    const current = observation.current
    const ghostMove = observation.legal_moves.find(
      (m) => m.x === current.x && m.rot === current.rot && !m.use_hold
    )

    return ghostMove?.harddrop_y
  }, [observation])

  const handleReset = useCallback(() => {
    reset(Date.now() % 1000000)
  }, [reset])

  // Create empty/default observation for initial display
  const displayObservation = observation || {
    hold: { type: null, used: false },
    episode: { score: 0, lines_total: 0, top_out: false, seed: 0 },
    board: { w: 10, h: 20, cells: new Array(200).fill(0), row_heights: new Array(10).fill(0), holes_per_col: new Array(10).fill(0) },
    current: { type: 'I' as const, x: 3, y: 1, rot: 0 },
    next_queue: [],
    features: { agg_height: 0, bumpiness: 0, well_max: 0, holes: 0, row_trans: 0, col_trans: 0 },
    legal_moves: []
  }

  return (
    <div className="app">
      <header>
        <h1>TetrisCore</h1>
        <button onClick={handleReset} className="reset-btn" disabled={!isConnected}>
          New Game
        </button>
      </header>

      {!isConnected && (
        <div className="connecting-message">
          <p>Connecting to server...</p>
          <p className="hint">Make sure the backend is running on port 8000</p>
        </div>
      )}

      {isConnected && (
        <div className="game-container">
          <div className="left-panel">
            <HoldPanel hold={displayObservation.hold} />
            <ScorePanel episode={displayObservation.episode} />
          </div>

          <div className="board-container">
            <GameBoard
              board={displayObservation.board}
              currentPiece={observation ? displayObservation.current : undefined}
              ghostY={observation ? ghostY : undefined}
            />
            {done && (
              <div className="game-over-overlay">
                <h2>Game Over!</h2>
                <p>Score: {displayObservation.episode.score}</p>
                <p>Lines: {displayObservation.episode.lines_total}</p>
                <button onClick={handleReset}>Play Again</button>
              </div>
            )}
          </div>

          <div className="right-panel">
            <NextPanel nextQueue={displayObservation.next_queue} />
            <InspectorPanel
              features={displayObservation.features}
              legalMoves={displayObservation.legal_moves}
            />
          </div>
        </div>
      )}

      <footer>
        <div className="controls-info">
          <h3>Controls</h3>
          <div className="controls-grid">
            <div className="control">
              <kbd>←</kbd> <kbd>→</kbd> Move
            </div>
            <div className="control">
              <kbd>↓</kbd> Soft Drop
            </div>
            <div className="control">
              <kbd>Space</kbd> Hard Drop
            </div>
            <div className="control">
              <kbd>Z</kbd> <kbd>X</kbd> Rotate
            </div>
            <div className="control">
              <kbd>Shift</kbd> <kbd>C</kbd> Hold
            </div>
          </div>
        </div>
        {info.events && info.events.length > 0 && (
          <div className="events">
            Events: {info.events.join(', ')}
          </div>
        )}
      </footer>
    </div>
  )
}

export default App
