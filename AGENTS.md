# Repository Guidelines

## Project Structure & Module Organization
The monorepo keeps real-time logic in `engine/python/tetris_core` (FastAPI server + agent runtime) and the TypeScript client in `apps/web` (Vite + React). Back-end tests live in `engine/python/tests`, while shared JSON schemas sit under `proto/schema`. Automation and codegen utilities (`dev.sh`, `gen-types.sh`) are in `scripts`. Keep data files, logs, or training artifacts out of the repo; only commit reproducible assets such as schema updates or seed fixtures.

## Build, Test, and Development Commands
- `pnpm install && cd engine/python && uv sync` – install JS and Python dependencies.
- `pnpm dev` or `./scripts/dev.sh` – launch both FastAPI (port 8000) and Vite (port 3000).
- `cd apps/web && pnpm dev` – run the web UI alone.
- `cd engine/python && uv run pytest tests/ -v` – execute the deterministic engine test suite.
- `pnpm lint` plus `cd engine/python && uv run black tetris_core tests && uv run ruff check` – enforce formatting/linting for both stacks.

## Coding Style & Naming Conventions
Python uses type-annotated modules, snake_case functions, and PascalCase classes (`DellacherieAgent`). Run Black (line length 88) before committing; Ruff guards imports and docstrings. TypeScript follows strict mode with 2-space indentation, PascalCase React components, camelCase hooks/stores (`useGameConnection`, `gameStore`). Rely on Prettier for formatting and ESLint for lint rules; keep CSS utility classes scoped in `App.css` or component-level styles.

## Testing Guidelines
Pytest cases should mirror the module under test (e.g., `tests/test_env.py` for `env.py`) and seed RNG-dependent checks to `42` unless another seed is required. Focus on: movement/rotation legality, WebSocket protocol invariants, and agent heuristics. When adding regression coverage, include fixture descriptions in docstrings and prefer parametrized tests over loops. Frontend changes should include at least a manual sanity check against the running FastAPI server; document any manual steps in the PR description.

## Commit & Pull Request Guidelines
Commit history favors short, imperative summaries (`fix ghost position disappear problem`). Keep related changes in a single commit when possible, reference subsystems (`api:`, `web:`) when clarity helps, and avoid WIP text. PRs must describe the change, list test commands run, attach screenshots/GIFs for UI shifts, and link issues or protocol tickets. Note schema bumps explicitly and regenerate TypeScript types via `pnpm gen-types` when touching `proto/schema`. Request reviews from both engine and web owners if changes cross the boundary.

## Security & Configuration Tips
Do not embed API keys or training datasets; load secrets via environment variables consumed by `scripts/dev.sh`. When adjusting protocol versions, update `proto/schema/v1.json`, regenerate clients, and increment `schema_version` constants. Preserve default ports (8000/3000) unless coordinated, so agent automation scripts remain compatible.
