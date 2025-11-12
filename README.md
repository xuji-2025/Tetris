# TetrisCore

A dual-purpose Tetris implementation designed for both human play and AI training. The engine exposes structured state (not pixels), making it suitable for RL agents while remaining fully playable by humans.

## Features

### Game Engine
- **Deterministic gameplay**: Seeded 7-bag RNG ensures reproducible games
- **SRS rotation system**: Full Super Rotation System with wall kick tables
- **Modern mechanics**: Lock delay (30 ticks), hold functionality, ghost piece preview
- **Structured observations**: Board state, legal moves, engineered features (height, holes, bumpiness, transitions)
- **60Hz tick rate**: Real-time gameplay with configurable gravity

### Web Interface
- **Real-time play**: WebSocket connection to Python backend
- **Full game controls**: Keyboard input for movement, rotation, drop, and hold
- **Visual feedback**: Ghost piece showing landing position
- **Game info panels**: Next queue, hold piece, score, lines cleared
- **Developer tools**: Inspector panel showing engineered features and legal move count

### API & Protocol
- **WebSocket server**: JSON-based protocol (FastAPI + uvicorn)
- **Versioned schema**: Protocol v1.0.0 defined in `proto/schema/v1.json`
- **Gym-like interface**: `reset(seed)` and `step(action)` methods
- **Frame actions**: LEFT, RIGHT, CW, CCW, SOFT, HARD, HOLD, NOOP
- **Rich observations**: Full game state with features and legal moves

## Quick Start

### Install Dependencies

```bash
# Install frontend dependencies (requires pnpm)
pnpm install

# Install backend dependencies (requires uv)
cd engine/python && uv sync
```

### Run Development Environment

```bash
# Start both backend and frontend
./scripts/dev.sh

# Or start individually:
# Backend (Python WebSocket server on :8000)
cd engine/python && uv run uvicorn api.server:app --reload --port 8000

# Frontend (Vite dev server on :3000)
cd apps/web && pnpm dev
```

### Run Tests

```bash
cd engine/python

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_env.py -v

# Test WebSocket server (requires server running)
uv run python tests/test_client.py           # Basic test
uv run python tests/test_client.py multiple  # Multiple games
uv run python tests/test_client.py interactive  # Interactive mode
```

## Controls

- **←/→**: Move left/right
- **↓**: Soft drop (move down faster)
- **Space**: Hard drop (instant placement)
- **Z/X**: Rotate counter-clockwise/clockwise
- **Shift/C**: Hold current piece

## Project Structure

```
tetris/
├── apps/web/              # React frontend
│   ├── src/
│   │   ├── components/    # GameBoard, GameInfo panels
│   │   ├── hooks/         # WebSocket connection, keyboard controls
│   │   ├── stores/        # Zustand state management
│   │   └── types/         # TypeScript protocol types
│   └── vite.config.ts
├── engine/python/         # Core game engine
│   ├── tetris_core/       # Game logic
│   │   ├── env.py         # Main game environment
│   │   ├── board.py       # 10×20 grid, collision, line clearing
│   │   ├── piece.py       # Tetromino shapes (all 4 rotations)
│   │   ├── rng.py         # Deterministic 7-bag randomizer
│   │   ├── rules.py       # SRS wall kicks, lock delay, scoring
│   │   └── features.py    # Engineered metrics for RL
│   ├── api/               # WebSocket server
│   │   ├── server.py      # FastAPI WebSocket endpoint
│   │   └── protocol.py    # Protocol dataclasses
│   ├── tests/             # Unit tests (24/24 passing)
│   └── pyproject.toml     # uv configuration
├── proto/schema/          # Protocol definitions
│   └── v1.json            # JSON Schema for observations/actions
└── scripts/               # Development tools
    ├── dev.sh             # Start full dev environment
    └── gen-types.sh       # Generate TypeScript types (future)
```

## Architecture

### Coordinate System

The board uses screen coordinates (y=0 is TOP, y=19 is BOTTOM):
- Pieces spawn at y=1 (near top)
- Gravity moves pieces DOWN (increasing y: 0 → 19)
- Hard drop increments y until collision

### Game Loop

Each `step()` call processes one tick (1/60th second):
1. Apply player action (move, rotate, drop, hold, or noop)
2. Apply gravity (every 48 ticks = 1G)
3. Check lock delay (piece locks after 30 ticks on ground)
4. Lock piece → clear lines → spawn next → check top-out
5. Compute features and legal moves
6. Return observation with full game state

### Observation Schema

All observations follow `proto/schema/v1.json` (version `s1.0.0`):

```json
{
  "schema_version": "s1.0.0",
  "tick": 1234,
  "board": {
    "w": 10, "h": 20,
    "cells": [...],  // Flat array[200], row-major
    "row_heights": [...],  // Height of each column
    "holes_per_col": [...]
  },
  "current": {"type": "T", "x": 4, "y": 8, "rot": 0},
  "next_queue": ["O", "I", "S"],
  "hold": {"type": "L", "used": false},
  "features": {
    "agg_height": 42,
    "bumpiness": 8,
    "holes": 3,
    "well_max": 2,
    "row_trans": 15,
    "col_trans": 12
  },
  "legal_moves": [
    {"x": 0, "rot": 0, "use_hold": false, "harddrop_y": 18},
    ...
  ],
  "episode": {
    "score": 1200,
    "lines_total": 5,
    "top_out": false,
    "seed": 42
  }
}
```

### Engineered Features

For RL training, the engine computes classic heuristics:
- **aggregate_height**: Sum of column heights
- **bumpiness**: Sum of |height[i] - height[i+1]|
- **holes**: Empty cells with filled cells above
- **row_trans/col_trans**: Transitions between filled/empty cells
- **well_max**: Deepest valley between higher neighbors

### Legal Moves

The engine pre-computes all valid placements (~80 positions):
- Tests all (x, rot) combinations for current piece
- Includes hold piece if available and not yet used
- Simulates hard drop from top to find landing position
- Returns only collision-free placements
- Computed in <1ms (no expensive pathfinding)

## WebSocket Protocol

### Messages (Client → Server)

```json
{"type": "hello", "version": "s1.0.0"}
{"type": "reset", "seed": 42}
{"type": "step", "action": "LEFT"}
{"type": "subscribe", "stream": true}
```

### Messages (Server → Client)

```json
{"type": "hello", "version": "s1.0.0", "server": "tetris-core-py"}
{"type": "obs", "data": {...}, "reward": 0.0, "done": false, "info": {...}}
{"type": "error", "code": "INVALID_ACTION", "message": "..."}
```

## Development

### Code Quality

```bash
# Format Python code
cd engine/python
uv run black tetris_core/ tests/
uv run ruff check tetris_core/ tests/

# Format TypeScript code
cd apps/web
pnpm prettier --write "src/**/*.{ts,tsx}"
pnpm eslint src/
```

### Testing Philosophy

- **Unit tests**: Core mechanics (collision, rotation, line clear, RNG determinism)
- **WebSocket tests**: Manual testing via `test_client.py`
- **All 24 tests passing**: Clean test suite with full coverage of core logic

## Future Work

- **AI/RL Integration**: Placement actions, batch processing, training examples
- **Replay System**: JSONL recording/playback for analysis
- **Golden Replays**: Fixed seed + action sequence → assert final state
- **CI/CD**: GitHub Actions for tests and linting
- **Gameplay Polish**: Levels, sound effects, mobile controls
- **Rust Port**: Maintain identical semantics with same JSON schema

## License

MIT

## Contributing

See `CLAUDE.md` for detailed development guidelines and architecture documentation.
