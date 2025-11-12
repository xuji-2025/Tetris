/**
 * TypeScript protocol types matching proto/schema/v1.json
 */

export type PieceType = 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L'

export type FrameAction = 'LEFT' | 'RIGHT' | 'CW' | 'CCW' | 'SOFT' | 'HARD' | 'HOLD' | 'NOOP'

export interface Board {
  w: 10
  h: 20
  cells: number[] // 200 elements (row-major)
  row_heights: number[] // 10 elements
  holes_per_col: number[] // 10 elements
}

export interface CurrentPiece {
  type: PieceType
  x: number
  y: number
  rot: number // 0-3
}

export interface HoldInfo {
  type: PieceType | null
  used: boolean
}

export interface Features {
  agg_height: number
  bumpiness: number
  well_max: number
  holes: number
  row_trans: number
  col_trans: number
}

export interface Episode {
  score: number
  lines_total: number
  top_out: boolean
  seed: number
}

export interface LegalMove {
  x: number
  rot: number
  use_hold: boolean
  harddrop_y: number
}

export interface Config {
  srs: boolean
  hold: boolean
  gravity: 'step'
}

export interface Observation {
  schema_version: 's1.0.0'
  tick: number
  board: Board
  current: CurrentPiece
  next_queue: PieceType[]
  hold: HoldInfo
  features: Features
  episode: Episode
  legal_moves: LegalMove[]
  config: Config
}

// WebSocket Messages

export interface HelloRequest {
  type: 'hello'
  version: 's1.0.0'
}

export interface HelloResponse {
  type: 'hello'
  version: 's1.0.0'
  server: string
}

export interface ResetRequest {
  type: 'reset'
  seed?: number
}

export interface StepRequest {
  type: 'step'
  action: FrameAction
}

export interface SubscribeRequest {
  type: 'subscribe'
  stream?: boolean
}

export interface ObservationResponse {
  type: 'obs'
  data: Observation
  reward: number
  done: boolean
  info: {
    lines_cleared?: number
    delta?: Record<string, number>
    events?: string[]
    [key: string]: any
  }
}

export interface ErrorResponse {
  type: 'error'
  code: string
  message: string
  details?: Record<string, any>
}

export type ServerMessage = HelloResponse | ObservationResponse | ErrorResponse

export type ClientMessage = HelloRequest | ResetRequest | StepRequest | SubscribeRequest
