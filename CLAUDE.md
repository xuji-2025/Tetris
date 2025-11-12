# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TetrisCore is a dual-purpose Tetris implementation designed for both human play (web UI) and AI training (structured API). The codebase enforces deterministic game rules with a clean separation between engine logic and presentation.

**Key Design Principle**: Engine exposes structured state (not pixels), making it suitable for RL agents while remaining human-playable.

## Commands

### Development

```bash
# Start full dev environment (backend + frontend)
./scripts/dev.sh

# Backend only (Python WebSocket server on :8000)
cd engine/python && uv run uvicorn api.server:app --reload --port 8000

# Frontend only (Vite dev server on :3000)
cd apps/web && pnpm dev
```

### Testing

```bash
# Run Python unit tests
cd engine/python && uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_env.py -v

# Run single test
uv run pytest tests/test_env.py::test_env_reset -v

# Test WebSocket server (requires server running)
uv run python tests/test_client.py           # Basic test
uv run python tests/test_client.py multiple  # Multiple games
uv run python tests/test_client.py interactive  # Interactive mode
```

### Code Quality

```bash
# Format Python code
cd engine/python && uv run black tetris_core/ tests/
uv run ruff check tetris_core/ tests/

# Format TypeScript code
cd apps/web && pnpm prettier --write "src/**/*.{ts,tsx}"
pnpm eslint src/
```

### Dependencies

```bash
# Install/update Python dependencies
cd engine/python && uv sync --extra dev

# Install/update JavaScript dependencies
pnpm install
```

## Architecture

### Coordinate System (CRITICAL)

Board uses **screen coordinates**:
- `y=0` is the **TOP** of the board (skyline)
- `y=19` is the **BOTTOM** of the board (where lines clear)
- Pieces spawn at `y=1` (near top)
- Gravity moves pieces **DOWN**: `y` increases (from 0 → 19)
- Hard drop: increment `y` until collision

This is consistent throughout:
- `piece.move(0, 1)` moves DOWN
- `piece.move(0, -1)` moves UP
- `board.get(x, y)` where low y = top, high y = bottom

### State Flow

```
TetrisEnv (env.py)
  ├─ Board (board.py): 10×20 grid, collision, line clearing
  ├─ Piece (piece.py): Tetromino shapes in 4 rotations
  ├─ SevenBagRNG (rng.py): Deterministic 7-bag randomizer
  ├─ SRSRules (rules.py): Super Rotation System wall kicks
  ├─ LockDelay (rules.py): 30-tick (0.5s) lock timer
  └─ Features (features.py): Engineered metrics (height, holes, bumpiness, etc.)
```

**Step Cycle** (60 ticks/second):
1. Apply player action (move, rotate, drop, hold, noop)
2. Apply gravity (every 48 ticks = 1G)
3. Check lock delay (if piece on ground for 30 ticks → lock)
4. Lock piece → clear lines → spawn next
5. Compute features + legal moves
6. Return observation

### Two Action Paradigms

**Frame Actions** (human):
- `LEFT`, `RIGHT`, `CW`, `CCW`, `SOFT`, `HARD`, `HOLD`, `NOOP`
- One action per tick
- Gravity and lock delay apply automatically

**Placement Actions** (AI, future):
- `{x, rot, use_hold}` - directly specify final placement
- Not yet implemented in `env.step()`, but legal moves are pre-computed

### Observation Schema

All observations follow `proto/schema/v1.json` (version `s1.0.0`). Key fields:

- `board.cells`: Flat array[200] (row-major: `cells[y*10 + x]`)
- `board.row_heights`: Height of each column (for features)
- `current`: Active piece `{type, x, y, rot}`
- `next_queue`: Upcoming 3 pieces (from 7-bag RNG)
- `hold`: Held piece `{type, used}` (used=true blocks swap until next lock)
- `features`: Engineered metrics `{agg_height, bumpiness, holes, row_trans, col_trans, well_max}`
- `legal_moves`: All valid placements `[{x, rot, use_hold, harddrop_y}]`
- `episode`: `{score, lines_total, top_out, seed}`

**Legal Moves Computation**:
- Tests all (x, rot) pairs for current piece (+ hold piece if available)
- Simulates hard drop from top (`y=0`) to find landing position
- Returns only collision-free placements
- Cost: ~80 collision checks (cheap: <1ms)

### Module Responsibilities

**tetris_core/rng.py**:
- 7-bag ensures all 7 pieces appear before any repeats
- `peek(n)` allows lookahead without consuming
- Fully deterministic with seed

**tetris_core/piece.py**:
- `PIECE_SHAPES`: Defines all 4 rotations for 7 piece types
- `get_cells()`: Returns absolute board coordinates for piece's 4 blocks
- Pieces are **immutable**: `move()` and `rotate()` return new instances

**tetris_core/board.py**:
- Flat array `cells[200]` (0=empty, 1-7=piece types)
- `collides(piece)`: Checks boundaries + existing blocks
- `clear_lines()`: Shifts rows down after clearing
- `get_column_heights()` / `get_holes_per_column()`: Used by features

**tetris_core/rules.py**:
- `SRSRules`: Wall kick tables for J/L/S/T/Z (5 tests) and I-piece (5 tests), O-piece doesn't kick
- `try_rotate()`: Attempts basic rotation, then tests kick offsets in order
- `LockDelay`: Tracks ticks on ground; piece locks after 30 ticks

**tetris_core/features.py**:
- Classic heuristics for board evaluation
- `aggregate_height`: Sum of column heights
- `bumpiness`: Sum of |height[i] - height[i+1]|
- `holes`: Empty cells with filled cells above
- `row_trans`/`col_trans`: Transitions between filled/empty
- `well_max`: Deepest valley between higher neighbors

**tetris_core/env.py**:
- Main game loop: `reset(seed)` → `step(action)` → `{obs, reward, done, info}`
- `info.delta`: Feature deltas (for reward shaping in RL)
- `info.events`: `["lock", "clear", "spawn", "hard_drop", "top_out"]`
- **No baked reward function**: Engine only exposes raw state changes

## Protocol & Future Rust Port

**Schema Location**: `proto/schema/v1.json` (JSON Schema Draft 7)

**Current Approach**:
- Python: Hand-written `@dataclass` in `api/protocol.py`, validated in tests
- TypeScript: Hand-written interfaces (or generate via `json-schema-to-typescript`)
- **Rust (future)**: `serde` will derive types directly from JSON

**Versioning**:
- Breaking changes → bump major (`s2.0.0`)
- Pre-release (current): free to change protocol

**Wire Format**: JSON over WebSocket
- Messages: `hello`, `reset`, `step`, `subscribe`, error
- Example: `{"type": "step", "action": "LEFT"}`

## Development Workflow

### Adding a New Piece Type

1. Add shape to `PIECE_SHAPES` in `piece.py` (4 rotations, 4 cells each)
2. Add to `SevenBagRNG.PIECES` in `rng.py`
3. Add spawn position to `get_spawn_position()` in `piece.py`
4. Add mapping in `board.lock_piece()` for cell encoding
5. Update schema: Add to `PieceType` enum in `proto/schema/v1.json`
6. Write tests in `tests/test_piece.py`

### Modifying Game Rules

**Gravity**: Change `TetrisEnv.GRAVITY_TICKS` (lower = faster fall)
**Lock Delay**: Pass `lock_delay_ticks` to `TetrisEnv.__init__()`
**SRS**: Modify kick tables in `rules.py` (follow SRS spec)
**Scoring**: Edit `calculate_score()` in `rules.py`

### Testing Philosophy

- **Unit tests**: Core mechanics (collision, rotation, line clear, RNG determinism)
- **Golden replays** (future): Fixed seed + action sequence → assert final board checksum
- **E2E** (future): Boot server, send WebSocket commands, verify observation

## Common Pitfalls

1. **Coordinate confusion**: Always remember `y=0` is TOP, `y=19` is BOTTOM
2. **Piece immutability**: Never modify piece in-place; use `piece.move()` / `piece.rotate()`
3. **Hold semantics**: `hold_used_this_turn` prevents double-swap; resets on piece lock
4. **Legal moves**: Don't confuse with pathfinding—we only check final placement validity
5. **Lock delay**: Piece must stay on ground for 30 consecutive ticks; moving resets timer

## WebSocket Server

**Location**: `engine/python/api/server.py`

The WebSocket server provides a JSON-based protocol for remote game control.

### Protocol Messages

**Client → Server**:
- `{"type": "hello", "version": "s1.0.0"}` - Handshake
- `{"type": "reset", "seed": 42}` - Reset game (seed optional)
- `{"type": "step", "action": "LEFT"}` - Execute action
- `{"type": "subscribe", "stream": true}` - Enable streaming mode

**Server → Client**:
- `{"type": "hello", "version": "s1.0.0", "server": "tetris-core-py"}` - Handshake response
- `{"type": "obs", "data": {...}, "reward": 0.0, "done": false, "info": {...}}` - Observation
- `{"type": "error", "code": "INVALID_ACTION", "message": "..."}` - Error

### Session Management

Each WebSocket connection maintains an independent `GameSession`:
- `session.env` - TetrisEnv instance
- `session.initialized` - Whether game has been reset
- `session.streaming` - Whether to auto-stream observations (future feature)

### Error Codes

- `INVALID_MESSAGE` - Malformed JSON or unknown message type
- `INVALID_ACTION` - Unknown action string
- `GAME_NOT_INITIALIZED` - Must send reset before step
- `GAME_OVER` - Game has ended
- `VERSION_MISMATCH` - Client/server version incompatible (not enforced yet)

### Testing WebSocket Server

```bash
# Terminal 1: Start server
cd engine/python && uv run uvicorn api.server:app --reload --port 8000

# Terminal 2: Run test client
uv run python tests/test_client.py
```

## Future Work (Not Yet Implemented)

- Web UI React components (scaffolded but not wired)
- Replay system (`replay.py` needs JSONL writer/reader)
- Placement action support in `env.step()` (legal moves computed but not executable)
- Golden replay tests in CI
- Streaming mode (auto-send observations after each step)
- Rust engine port (maintain identical semantics + same JSON schema)
