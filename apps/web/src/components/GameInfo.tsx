/**
 * Game information panels (Next, Hold, Score, Inspector)
 */

import React, { useState } from 'react'
import type { PieceType, HoldInfo, Episode, Features, LegalMove } from '../types/protocol'

interface NextPanelProps {
  nextQueue: PieceType[]
}

export function NextPanel({ nextQueue }: NextPanelProps) {
  return (
    <div className="panel">
      <h3>Next</h3>
      <div className="piece-preview">
        {nextQueue.map((piece, i) => (
          <div key={i} className="piece-item" style={{ color: getPieceColor(piece) }}>
            {piece}
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
      <div className="piece-preview">
        {hold.type ? (
          <div
            className="piece-item"
            style={{
              color: getPieceColor(hold.type),
              opacity: hold.used ? 0.5 : 1,
            }}
          >
            {hold.type}
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
      <h3 onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        Inspector {expanded ? '▼' : '▶'}
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

function getPieceColor(piece: PieceType): string {
  const colors: Record<PieceType, string> = {
    I: '#00f0f0',
    O: '#f0f000',
    T: '#a000f0',
    S: '#00f000',
    Z: '#f00000',
    J: '#0000f0',
    L: '#f0a000',
  }
  return colors[piece]
}
