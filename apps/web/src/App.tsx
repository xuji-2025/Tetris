import { useCallback, useEffect, useMemo } from 'react'
import { useGameConnection } from './hooks/useGameConnection'
import { useKeyboardControls } from './hooks/useKeyboardControls'
import { useGameStore } from './stores/gameStore'
import { GameBoard } from './components/GameBoard'
import { NextPanel, HoldPanel, ScorePanel, InspectorPanel } from './components/GameInfo'
import './App.css'

const WS_URL = 'ws://localhost:8000/ws'

function App() {
  const {
    mode,
    observation,
    done,
    info,
    setObservation,
    setConnected,
    isAIPlaying,
    selectedAgent,
    playbackSpeed,
    setAIPlaying,
    setSelectedAgent,
    setPlaybackSpeed,
    setMode,
    // Comparison state
    isComparing,
    comparisonAgent1,
    comparisonAgent2,
    comparisonSpeed,
    comparisonMaxPieces,
    comparisonSeed,
    game1,
    game2,
    comparisonStats,
    comparisonComplete,
    setComparing,
    setComparisonAgent1,
    setComparisonAgent2,
    setComparisonSpeed,
    setComparisonMaxPieces,
    setComparisonSeed,
    setComparisonState,
    setComparisonComplete,
    clearComparisonComplete,
  } = useGameStore()

  // WebSocket connection
  const { isConnected, reset, step, aiPlay, aiStop, compareStart, compareStop, compareSetSpeed } = useGameConnection({
    url: WS_URL,
    onObservation: setObservation,
    onCompareObs: (data) => {
      setComparisonState(data.game1, data.game2, data.comparison)
    },
    onCompareComplete: (data) => {
      console.log('Comparison complete received:', data)
      setComparisonComplete(data.winner, data.game1, data.game2)
    },
    onConnect: () => {
      setConnected(true)
    },
    onDisconnect: () => setConnected(false),
    onError: (error) => console.error('Game error:', error),
  })

  // Game loop - tick the engine at 60Hz (only for human play)
  // Only start after we have an observation (game has been initialized)
  useEffect(() => {
    if (!isConnected || !observation || done || isAIPlaying) return

    const interval = setInterval(() => {
      step('NOOP')
    }, 1000 / 60) // 60 FPS

    return () => clearInterval(interval)
  }, [isConnected, observation, done, isAIPlaying]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-stop AI when game ends
  useEffect(() => {
    if (isAIPlaying && done) {
      console.log('Game ended during AI play, stopping AI')
      setAIPlaying(false)
      aiStop()
    }
  }, [isAIPlaying, done, aiStop, setAIPlaying])

  // Keyboard controls (disabled during AI play)
  useKeyboardControls({
    onAction: step,
    enabled: isConnected && !done && !isAIPlaying,
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
    // Stop AI if playing
    if (isAIPlaying) {
      setAIPlaying(false)
      aiStop()
    }
    reset(Date.now() % 1000000)
  }, [reset, isAIPlaying, aiStop, setAIPlaying])

  const handleAIStart = useCallback(() => {
    setAIPlaying(true)
    aiPlay(selectedAgent, playbackSpeed)
  }, [aiPlay, selectedAgent, playbackSpeed, setAIPlaying])

  const handleAIStop = useCallback(() => {
    setAIPlaying(false)
    aiStop()
  }, [aiStop, setAIPlaying])

  const handleAgentChange = useCallback((newAgent: 'random' | 'dellacherie' | 'smartdellacherie') => {
    setSelectedAgent(newAgent)
    // If AI is playing, restart with new agent
    if (isAIPlaying) {
      aiStop()
      // Small delay to ensure stop is processed
      setTimeout(() => {
        aiPlay(newAgent, playbackSpeed)
      }, 50)
    }
  }, [isAIPlaying, playbackSpeed, aiPlay, aiStop, setSelectedAgent])

  const handleSpeedChange = useCallback((newSpeed: number) => {
    setPlaybackSpeed(newSpeed)
    // If AI is playing, restart with new speed
    if (isAIPlaying) {
      aiStop()
      // Small delay to ensure stop is processed
      setTimeout(() => {
        aiPlay(selectedAgent, newSpeed)
      }, 50)
    }
  }, [isAIPlaying, selectedAgent, aiPlay, aiStop, setPlaybackSpeed])

  // Comparison handlers
  const handleCompareStart = useCallback(() => {
    setComparing(true)
    compareStart(comparisonAgent1, comparisonAgent2, comparisonSpeed, comparisonMaxPieces, comparisonSeed)
  }, [compareStart, comparisonAgent1, comparisonAgent2, comparisonSpeed, comparisonMaxPieces, comparisonSeed, setComparing])

  const handleCompareStop = useCallback(() => {
    setComparing(false)
    compareStop()
  }, [compareStop, setComparing])

  const handleComparisonSpeedChange = useCallback((newSpeed: number) => {
    setComparisonSpeed(newSpeed)
    // If comparison is running, send speed change message to backend
    if (isComparing) {
      compareSetSpeed(newSpeed)
    }
  }, [isComparing, compareSetSpeed, setComparisonSpeed])

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

        {/* Mode Toggle */}
        <div className="mode-toggle">
          <button
            className={mode === 'single' ? 'mode-btn active' : 'mode-btn'}
            onClick={() => setMode('single')}
          >
            Single Player
          </button>
          <button
            className={mode === 'compare' ? 'mode-btn active' : 'mode-btn'}
            onClick={() => setMode('compare')}
          >
            Agent Comparison
          </button>
        </div>

        {/* Single Player Controls */}
        {mode === 'single' && (
          <div className="header-controls">
            <button onClick={handleReset} className="reset-btn" disabled={!isConnected}>
              New Game
            </button>

            <div className="ai-controls">
              <label>
                Agent:
                <select
                  value={selectedAgent}
                  onChange={(e) => handleAgentChange(e.target.value as 'random' | 'dellacherie' | 'smartdellacherie')}
                >
                  <option value="dellacherie">Dellacherie</option>
                  <option value="smartdellacherie">Smart Dellacherie</option>
                  <option value="random">Random</option>
                </select>
              </label>

              <label>
                Speed:
                <select
                  value={playbackSpeed}
                  onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
                >
                  <option value="0.5">0.5x</option>
                  <option value="1">1x</option>
                  <option value="2">2x</option>
                  <option value="5">5x</option>
                </select>
              </label>

              {!isAIPlaying ? (
                <button onClick={handleAIStart} className="ai-btn" disabled={!isConnected || !observation}>
                  ▶ AI Take Over
                </button>
              ) : (
                <button onClick={handleAIStop} className="ai-btn stop">
                  ⏸ Hand Back Control
                </button>
              )}
            </div>
          </div>
        )}

        {/* Comparison Mode Controls */}
        {mode === 'compare' && (
          <div className="header-controls">
            <div className="ai-controls">
              <label>
                Agent 1:
                <select
                  value={comparisonAgent1}
                  onChange={(e) => setComparisonAgent1(e.target.value as 'random' | 'dellacherie' | 'smartdellacherie')}
                  disabled={isComparing}
                >
                  <option value="random">Random</option>
                  <option value="dellacherie">Dellacherie</option>
                  <option value="smartdellacherie">Smart Dellacherie</option>
                </select>
              </label>

              <label>
                Agent 2:
                <select
                  value={comparisonAgent2}
                  onChange={(e) => setComparisonAgent2(e.target.value as 'random' | 'dellacherie' | 'smartdellacherie')}
                  disabled={isComparing}
                >
                  <option value="random">Random</option>
                  <option value="dellacherie">Dellacherie</option>
                  <option value="smartdellacherie">Smart Dellacherie</option>
                </select>
              </label>

              <label>
                Speed:
                <select
                  value={comparisonSpeed}
                  onChange={(e) => handleComparisonSpeedChange(parseFloat(e.target.value))}
                  title="Change speed anytime, even during comparison"
                >
                  <option value="0.5">0.5x</option>
                  <option value="1">1x</option>
                  <option value="2">2x</option>
                  <option value="5">5x</option>
                  <option value="10">10x</option>
                  <option value="20">20x</option>
                  <option value="50">50x</option>
                </select>
              </label>

              <label>
                Max Pieces:
                <input
                  type="number"
                  value={comparisonMaxPieces}
                  onChange={(e) => setComparisonMaxPieces(parseInt(e.target.value))}
                  disabled={isComparing}
                  style={{ width: '80px', padding: '0.25rem', background: '#333', color: '#fff', border: '1px solid #555', borderRadius: '4px' }}
                />
              </label>

              {!isComparing ? (
                <button onClick={handleCompareStart} className="ai-btn" disabled={!isConnected}>
                  ▶ Start Comparison
                </button>
              ) : (
                <button onClick={handleCompareStop} className="ai-btn stop">
                  ⏸ Stop
                </button>
              )}
            </div>
          </div>
        )}
      </header>

      {!isConnected && (
        <div className="connecting-message">
          <p>Connecting to server...</p>
          <p className="hint">Make sure the backend is running on port 8000</p>
        </div>
      )}

      {/* Single Player Mode */}
      {isConnected && mode === 'single' && (
        <div className="game-container">
          <div className="left-panel">
            <HoldPanel hold={displayObservation.hold} />
            <ScorePanel episode={displayObservation.episode} />
            <div className="panel">
              <h3>Controls</h3>
              <div className="controls-list">
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
                  <kbd>↑</kbd> Rotate CW
                </div>
                <div className="control">
                  <kbd>Z</kbd> Rotate CCW
                </div>
                <div className="control">
                  <kbd>Shift</kbd> <kbd>C</kbd> Hold
                </div>
              </div>
            </div>
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

      {/* Comparison Mode */}
      {isConnected && mode === 'compare' && (
        <>
        <div className="comparison-container" style={{ position: 'relative' }}>
          {/* Comparison Stats */}
          {comparisonStats && (
            <div className="comparison-stats">
              <div className="stat-box">
                <div className="stat-label">Leader</div>
                <div className="stat-value">
                  {comparisonStats.leader === 'agent1' ? comparisonAgent1.toUpperCase() :
                   comparisonStats.leader === 'agent2' ? comparisonAgent2.toUpperCase() :
                   'TIED'}
                </div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Score Difference</div>
                <div className="stat-value">{Math.abs(comparisonStats.score_diff)}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Efficiency (Agent 1)</div>
                <div className="stat-value">{comparisonStats.efficiency_agent1.toFixed(1)} pts/line</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Efficiency (Agent 2)</div>
                <div className="stat-value">{comparisonStats.efficiency_agent2.toFixed(1)} pts/line</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Avg Clear (Agent 1)</div>
                <div className="stat-value">{comparisonStats.avg_clear_agent1.toFixed(2)} lines</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Avg Clear (Agent 2)</div>
                <div className="stat-value">{comparisonStats.avg_clear_agent2.toFixed(2)} lines</div>
              </div>
            </div>
          )}

          {/* Side-by-side Boards */}
          <div className="comparison-boards">
            {/* Agent 1 */}
            <div className="comparison-game">
              <div className="comparison-game-header">
                <h2>{comparisonAgent1.toUpperCase()}</h2>
                {game1 && (
                  <div className="comparison-game-stats">
                    <div className="progress">Progress: {game1.pieces_played} / {comparisonMaxPieces}</div>
                    <div>Score: {game1.obs.episode.score}</div>
                    <div>Lines: {game1.obs.episode.lines_total}</div>
                    {!game1.active && <div className="topped-out">TOPPED OUT</div>}
                  </div>
                )}
              </div>
              {game1 ? (
                <GameBoard
                  board={game1.obs.board}
                  currentPiece={game1.active ? game1.obs.current : undefined}
                  ghostY={undefined}
                />
              ) : (
                <div className="start-overlay">
                  <p>Waiting to start...</p>
                </div>
              )}
            </div>

            {/* Agent 2 */}
            <div className="comparison-game">
              <div className="comparison-game-header">
                <h2>{comparisonAgent2.toUpperCase()}</h2>
                {game2 && (
                  <div className="comparison-game-stats">
                    <div className="progress">Progress: {game2.pieces_played} / {comparisonMaxPieces}</div>
                    <div>Score: {game2.obs.episode.score}</div>
                    <div>Lines: {game2.obs.episode.lines_total}</div>
                    {!game2.active && <div className="topped-out">TOPPED OUT</div>}
                  </div>
                )}
              </div>
              {game2 ? (
                <GameBoard
                  board={game2.obs.board}
                  currentPiece={game2.active ? game2.obs.current : undefined}
                  ghostY={undefined}
                />
              ) : (
                <div className="start-overlay">
                  <p>Waiting to start...</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Completion Message Overlay */}
        {comparisonComplete && (
          <div className="comparison-complete-overlay">
            <div className="comparison-complete">
              <h2>Comparison Complete!</h2>
              <div className="winner">
                Winner: {comparisonComplete.winner === 'agent1' ? comparisonAgent1.toUpperCase() :
                         comparisonComplete.winner === 'agent2' ? comparisonAgent2.toUpperCase() :
                         'TIE'}
              </div>
              <div className="final-stats">
                <div className="final-stats-column">
                  <h3>{comparisonAgent1.toUpperCase()}</h3>
                  <div>Score: {comparisonComplete.game1.score}</div>
                  <div>Lines: {comparisonComplete.game1.lines}</div>
                  <div>Pieces: {comparisonComplete.game1.pieces}</div>
                  <div>Efficiency: {comparisonComplete.game1.efficiency.toFixed(1)} pts/line</div>
                  {comparisonComplete.game1.topped_out && <div className="topped-out">TOPPED OUT</div>}
                </div>
                <div className="final-stats-column">
                  <h3>{comparisonAgent2.toUpperCase()}</h3>
                  <div>Score: {comparisonComplete.game2.score}</div>
                  <div>Lines: {comparisonComplete.game2.lines}</div>
                  <div>Pieces: {comparisonComplete.game2.pieces}</div>
                  <div>Efficiency: {comparisonComplete.game2.efficiency.toFixed(1)} pts/line</div>
                  {comparisonComplete.game2.topped_out && <div className="topped-out">TOPPED OUT</div>}
                </div>
              </div>
              <button
                onClick={clearComparisonComplete}
                style={{
                  marginTop: '2rem',
                  padding: '0.75rem 2rem',
                  fontSize: '1.1rem',
                  background: '#00f0f0',
                  color: '#000',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                Start New Comparison
              </button>
            </div>
          </div>
        )}
        </>
      )}

      {info.events && info.events.length > 0 && (
        <footer>
          <div className="events">
            Events: {info.events.join(', ')}
          </div>
        </footer>
      )}
    </div>
  )
}

export default App
