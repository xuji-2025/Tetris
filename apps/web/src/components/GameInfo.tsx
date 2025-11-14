/**
 * Game information panels (Next, Hold, Score, Inspector)
 */

import { useState, useEffect, useRef } from 'react'
import type { PieceType, HoldInfo, Episode, Features, LegalMove } from '../types/protocol'

// Piece shapes and colors (matching GameBoard.tsx)
const PIECE_SHAPES: Record<PieceType, number[][][]> = {
  I: [
    [[0, 1], [1, 1], [2, 1], [3, 1]],
    [[2, 0], [2, 1], [2, 2], [2, 3]],
    [[0, 2], [1, 2], [2, 2], [3, 2]],
    [[1, 0], [1, 1], [1, 2], [1, 3]],
  ],
  O: [
    [[1, 0], [2, 0], [1, 1], [2, 1]],
    [[1, 0], [2, 0], [1, 1], [2, 1]],
    [[1, 0], [2, 0], [1, 1], [2, 1]],
    [[1, 0], [2, 0], [1, 1], [2, 1]],
  ],
  T: [
    [[1, 0], [0, 1], [1, 1], [2, 1]],
    [[1, 0], [1, 1], [2, 1], [1, 2]],
    [[0, 1], [1, 1], [2, 1], [1, 2]],
    [[1, 0], [0, 1], [1, 1], [1, 2]],
  ],
  S: [
    [[1, 0], [2, 0], [0, 1], [1, 1]],
    [[1, 0], [1, 1], [2, 1], [2, 2]],
    [[1, 1], [2, 1], [0, 2], [1, 2]],
    [[0, 0], [0, 1], [1, 1], [1, 2]],
  ],
  Z: [
    [[0, 0], [1, 0], [1, 1], [2, 1]],
    [[2, 0], [1, 1], [2, 1], [1, 2]],
    [[0, 1], [1, 1], [1, 2], [2, 2]],
    [[1, 0], [0, 1], [1, 1], [0, 2]],
  ],
  J: [
    [[0, 0], [0, 1], [1, 1], [2, 1]],
    [[1, 0], [2, 0], [1, 1], [1, 2]],
    [[0, 1], [1, 1], [2, 1], [2, 2]],
    [[1, 0], [1, 1], [0, 2], [1, 2]],
  ],
  L: [
    [[2, 0], [0, 1], [1, 1], [2, 1]],
    [[1, 0], [1, 1], [1, 2], [2, 2]],
    [[0, 1], [1, 1], [2, 1], [0, 2]],
    [[0, 0], [1, 0], [1, 1], [1, 2]],
  ],
}

const PIECE_COLORS: Record<PieceType, string> = {
  I: '#00f0f0',
  O: '#f0f000',
  T: '#a000f0',
  S: '#00f000',
  Z: '#f00000',
  J: '#0000f0',
  L: '#f0a000',
}

interface PiecePreviewProps {
  piece: PieceType
  opacity?: number
}

function PiecePreview({ piece, opacity = 1 }: PiecePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const CELL_SIZE = 12
    const GRID_SIZE = 4

    // Clear canvas
    ctx.fillStyle = '#1a1a1a'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Draw piece (rotation 0)
    const shape = PIECE_SHAPES[piece][0]
    ctx.fillStyle = PIECE_COLORS[piece]
    ctx.globalAlpha = opacity

    for (const [dx, dy] of shape) {
      ctx.fillRect(
        dx * CELL_SIZE,
        dy * CELL_SIZE,
        CELL_SIZE,
        CELL_SIZE
      )

      // Border
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 1
      ctx.strokeRect(
        dx * CELL_SIZE,
        dy * CELL_SIZE,
        CELL_SIZE,
        CELL_SIZE
      )
    }

    ctx.globalAlpha = 1
  }, [piece, opacity])

  return (
    <canvas
      ref={canvasRef}
      width={48}
      height={48}
      style={{
        display: 'block',
        margin: '0 auto',
        background: '#1a1a1a',
        borderRadius: '4px',
      }}
    />
  )
}

interface NextPanelProps {
  nextQueue: PieceType[]
}

export function NextPanel({ nextQueue }: NextPanelProps) {
  return (
    <div className="panel">
      <h3>Next</h3>
      <div className="piece-preview-list">
        {nextQueue.map((piece, i) => (
          <div key={i} className="piece-preview-item">
            <PiecePreview piece={piece} />
          </div>
        ))}
      </div>
    </div>
  )
}

interface HoldPanelProps {
  hold: HoldInfo
}

export function HoldPanel({ hold }: HoldPanelProps) {
  return (
    <div className="panel">
      <h3>Hold</h3>
      <div className="piece-preview-list">
        {hold.type ? (
          <div className="piece-preview-item">
            <PiecePreview piece={hold.type} opacity={hold.used ? 0.5 : 1} />
          </div>
        ) : (
          <div className="empty">-</div>
        )}
      </div>
    </div>
  )
}

interface ScorePanelProps {
  episode: Episode
}

export function ScorePanel({ episode }: ScorePanelProps) {
  return (
    <div className="panel">
      <h3>Stats</h3>
      <div className="stats">
        <div className="stat-row">
          <span className="label">Score:</span>
          <span className="value">{episode.score}</span>
        </div>
        <div className="stat-row">
          <span className="label">Lines:</span>
          <span className="value">{episode.lines_total}</span>
        </div>
        <div className="stat-row">
          <span className="label">Seed:</span>
          <span className="value">{episode.seed}</span>
        </div>
        {episode.top_out && (
          <div className="game-over">GAME OVER</div>
        )}
      </div>
    </div>
  )
}

interface InspectorPanelProps {
  features: Features
  legalMoves: LegalMove[]
}

export function InspectorPanel({ features, legalMoves }: InspectorPanelProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="panel inspector">
      <h3 onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer', userSelect: 'none' }}>
        Inspector <span className={`inspector-arrow ${expanded ? 'expanded' : ''}`}>▶</span>
      </h3>
      {expanded && (
        <>
          <div className="section">
            <h4>Features</h4>
            <div className="features">
              <div className="feature-row">
                <span className="label">Height:</span>
                <span className="value">{features.agg_height}</span>
              </div>
              <div className="feature-row">
                <span className="label">Bumpiness:</span>
                <span className="value">{features.bumpiness}</span>
              </div>
              <div className="feature-row">
                <span className="label">Holes:</span>
                <span className="value">{features.holes}</span>
              </div>
              <div className="feature-row">
                <span className="label">Wells:</span>
                <span className="value">{features.well_max}</span>
              </div>
              <div className="feature-row">
                <span className="label">Row Trans:</span>
                <span className="value">{features.row_trans}</span>
              </div>
              <div className="feature-row">
                <span className="label">Col Trans:</span>
                <span className="value">{features.col_trans}</span>
              </div>
            </div>
          </div>
          <div className="section">
            <h4>Legal Moves</h4>
            <div className="legal-moves">
              {legalMoves.length} positions available
            </div>
          </div>
        </>
      )}
    </div>
  )
}
