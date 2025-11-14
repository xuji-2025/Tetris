/**
 * Tetris game board renderer
 */

import { useEffect, useRef } from 'react'
import type { Board, CurrentPiece, PieceType } from '../types/protocol'

interface GameBoardProps {
  board: Board
  currentPiece?: CurrentPiece
  ghostY?: number
}

const CELL_SIZE = 30
const COLORS: Record<number, string> = {
  0: '#1a1a1a', // Empty
  1: '#00f0f0', // I - cyan
  2: '#f0f000', // O - yellow
  3: '#a000f0', // T - purple
  4: '#00f000', // S - green
  5: '#f00000', // Z - red
  6: '#0000f0', // J - blue
  7: '#f0a000', // L - orange
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

// Piece shapes (same as Python)
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

export function GameBoard({ board, currentPiece, ghostY }: GameBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Draw board cells
    for (let y = 0; y < board.h; y++) {
      for (let x = 0; x < board.w; x++) {
        const cellValue = board.cells[y * board.w + x]
        const color = COLORS[cellValue]

        ctx.fillStyle = color
        ctx.fillRect(
          x * CELL_SIZE,
          y * CELL_SIZE,
          CELL_SIZE,
          CELL_SIZE
        )

        // Grid lines
        ctx.strokeStyle = '#333'
        ctx.strokeRect(
          x * CELL_SIZE,
          y * CELL_SIZE,
          CELL_SIZE,
          CELL_SIZE
        )
      }
    }

    // Draw ghost piece
    if (currentPiece && ghostY !== undefined) {
      const shape = PIECE_SHAPES[currentPiece.type][currentPiece.rot]
      ctx.fillStyle = PIECE_COLORS[currentPiece.type] + '40' // Semi-transparent

      for (const [dx, dy] of shape) {
        const x = currentPiece.x + dx
        const y = ghostY + dy

        if (x >= 0 && x < board.w && y >= 0 && y < board.h) {
          ctx.fillRect(
            x * CELL_SIZE,
            y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE
          )
        }
      }
    }

    // Draw current piece
    if (currentPiece) {
      const shape = PIECE_SHAPES[currentPiece.type][currentPiece.rot]
      ctx.fillStyle = PIECE_COLORS[currentPiece.type]

      for (const [dx, dy] of shape) {
        const x = currentPiece.x + dx
        const y = currentPiece.y + dy

        if (x >= 0 && x < board.w && y >= 0 && y < board.h) {
          ctx.fillRect(
            x * CELL_SIZE,
            y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE
          )

          // Piece border
          ctx.strokeStyle = '#fff'
          ctx.strokeRect(
            x * CELL_SIZE,
            y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE
          )
        }
      }
    }
  }, [board, currentPiece, ghostY])

  return (
    <canvas
      ref={canvasRef}
      width={board.w * CELL_SIZE}
      height={board.h * CELL_SIZE}
      style={{
        border: '2px solid #444',
        boxShadow: '0 4px 8px rgba(0,0,0,0.5)',
      }}
    />
  )
}
