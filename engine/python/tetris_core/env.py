"""Tetris environment with gym-like interface.

Provides reset() and step() methods for both human play and RL training.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from tetris_core.board import Board
from tetris_core.piece import Piece, get_spawn_position, PIECE_SHAPES
from tetris_core.rng import SevenBagRNG
from tetris_core.rules import SRSRules, LockDelay, calculate_score
from tetris_core.features import compute_features, compute_feature_deltas


class FrameAction(Enum):
    """Frame-by-frame control actions."""
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CW = "CW"        # Clockwise rotation
    CCW = "CCW"      # Counter-clockwise rotation
    SOFT = "SOFT"    # Soft drop (move down)
    HARD = "HARD"    # Hard drop (instant lock)
    HOLD = "HOLD"    # Hold current piece
    NOOP = "NOOP"    # No operation


@dataclass
class PlacementAction:
    """Direct placement action for AI."""
    x: int
    rot: int
    use_hold: bool


@dataclass
class LegalMove:
    """A legal placement move."""
    x: int
    rot: int
    use_hold: bool
    harddrop_y: int


@dataclass
class Observation:
    """Complete game state observation."""
    schema_version: str
    tick: int
    board: Board
    current: Piece
    next_queue: List[str]
    hold_type: Optional[str]
    hold_used: bool
    features: Dict[str, int]
    score: int
    lines_total: int
    top_out: bool
    seed: int
    legal_moves: List[LegalMove]
    srs_enabled: bool
    hold_enabled: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert observation to dictionary for serialization."""
        return {
            "schema_version": self.schema_version,
            "tick": self.tick,
            "board": {
                "w": self.board.WIDTH,
                "h": self.board.HEIGHT,
                "cells": self.board.to_list(),
                "row_heights": self.board.get_column_heights(),
                "holes_per_col": self.board.get_holes_per_column(),
            },
            "current": {
                "type": self.current.type,
                "x": self.current.x,
                "y": self.current.y,
                "rot": self.current.rot,
            },
            "next_queue": self.next_queue,
            "hold": {
                "type": self.hold_type,
                "used": self.hold_used,
            },
            "features": self.features,
            "episode": {
                "score": self.score,
                "lines_total": self.lines_total,
                "top_out": self.top_out,
                "seed": self.seed,
            },
            "legal_moves": [
                {"x": m.x, "rot": m.rot, "use_hold": m.use_hold, "harddrop_y": m.harddrop_y}
                for m in self.legal_moves
            ],
            "config": {
                "srs": self.srs_enabled,
                "hold": self.hold_enabled,
                "gravity": "step",
            },
        }


@dataclass
class StepResult:
    """Result of a step() call."""
    obs: Observation
    reward: float
    done: bool
    info: Dict[str, Any]


class TetrisEnv:
    """Tetris game environment."""

    SCHEMA_VERSION = "s1.0.0"
    TICKS_PER_SECOND = 60
    GRAVITY_TICKS = 48  # 1G = drop 1 cell every 48 ticks (~1.25 cells/sec)

    def __init__(
        self,
        srs_enabled: bool = True,
        hold_enabled: bool = True,
        lock_delay_ticks: int = 30,
        next_queue_size: int = 3,
    ):
        """Initialize the environment.

        Args:
            srs_enabled: Enable SRS wall kicks
            hold_enabled: Enable hold functionality
            lock_delay_ticks: Lock delay in ticks (default 30 = 0.5s)
            next_queue_size: Number of next pieces to show
        """
        self.srs_enabled = srs_enabled
        self.hold_enabled = hold_enabled
        self.next_queue_size = next_queue_size

        self.board = Board()
        self.rng: Optional[SevenBagRNG] = None
        self.srs = SRSRules(enabled=srs_enabled)
        self.lock_delay = LockDelay(delay_ticks=lock_delay_ticks)

        self.current_piece: Optional[Piece] = None
        self.hold_piece: Optional[str] = None
        self.hold_used_this_turn = False

        self.tick = 0
        self.score = 0
        self.lines_total = 0
        self.done = False
        self.seed = 0

        self.gravity_counter = 0
        self.last_features: Dict[str, int] = {}

    def reset(self, seed: int) -> Observation:
        """Reset the environment with a new seed.

        Args:
            seed: Random seed for reproducibility

        Returns:
            Initial observation
        """
        self.seed = seed
        self.rng = SevenBagRNG(seed)
        self.board = Board()

        self.tick = 0
        self.score = 0
        self.lines_total = 0
        self.done = False
        self.hold_piece = None
        self.hold_used_this_turn = False
        self.gravity_counter = 0

        self._spawn_piece()
        self.last_features = compute_features(self.board)

        return self._build_observation()

    def step(self, action: FrameAction) -> StepResult:
        """Execute one tick of game time with the given action.

        Args:
            action: Frame action to execute

        Returns:
            Step result with observation, reward, done, info
        """
        if self.done:
            return StepResult(self._build_observation(), 0.0, True, {"error": "Game over"})

        events = []
        lines_cleared = 0
        old_features = self.last_features.copy()

        # Execute action
        if action == FrameAction.LEFT:
            self._try_move(-1, 0)
        elif action == FrameAction.RIGHT:
            self._try_move(1, 0)
        elif action == FrameAction.CW:
            self._try_rotate(clockwise=True)
        elif action == FrameAction.CCW:
            self._try_rotate(clockwise=False)
        elif action == FrameAction.SOFT:
            self._try_move(0, 1)  # Soft drop moves DOWN (increasing y)
        elif action == FrameAction.HARD:
            lines_from_drop, spawned = self._hard_drop()
            events.append("hard_drop")
            if lines_from_drop > 0:
                lines_cleared = lines_from_drop
                events.append("clear")
            if spawned:
                events.append("spawn")
        elif action == FrameAction.HOLD:
            if self.hold_enabled:
                self._try_hold()
        # NOOP does nothing

        # Apply gravity (only if not hard dropped)
        if action != FrameAction.HARD:
            self.gravity_counter += 1
            if self.gravity_counter >= self.GRAVITY_TICKS:
                self.gravity_counter = 0
                self._try_move(0, 1)  # Move DOWN (increasing y)

        # Check if piece is on ground and manage lock delay
        # This must happen after every action, not just gravity
        if action != FrameAction.HARD and self.current_piece:
            if self.lock_delay.is_on_ground(self.board, self.current_piece):
                # Piece is on ground
                if not self.lock_delay.active:
                    self.lock_delay.start()
            else:
                # Piece is not on ground (e.g., moved off an edge)
                if self.lock_delay.active:
                    self.lock_delay.reset()

        # Update lock delay
        if self.lock_delay.active:
            if not self.current_piece:
                self.lock_delay.reset()
            elif self.lock_delay.is_on_ground(self.board, self.current_piece):
                if self.lock_delay.tick():
                    # Lock the piece
                    self.board.lock_piece(self.current_piece)
                    events.append("lock")
                    self.lock_delay.reset()

                    # Clear lines
                    lines_cleared = self.board.clear_lines()
                    if lines_cleared > 0:
                        events.append("clear")
                        self.lines_total += lines_cleared
                        self.score += calculate_score(lines_cleared)

                    # Spawn next piece
                    self._spawn_piece()
                    events.append("spawn")
                    self.hold_used_this_turn = False

                    # Check top out
                    if self.board.collides(self.current_piece):
                        self.done = True
                        events.append("top_out")
            else:
                # Piece no longer on ground, reset lock delay
                self.lock_delay.reset()

        self.tick += 1

        # Compute features and deltas
        new_features = compute_features(self.board)
        feature_deltas = compute_feature_deltas(old_features, new_features)
        self.last_features = new_features

        obs = self._build_observation()
        info = {
            "lines_cleared": lines_cleared,
            "delta": feature_deltas,
            "events": events,
        }

        return StepResult(obs, 0.0, self.done, info)

    def step_placement(self, action: PlacementAction) -> StepResult:
        """Execute a placement action (AI interface).

        This is a higher-level interface for RL agents. Instead of frame-by-frame
        control, the agent specifies the final placement (x, rot, use_hold) and
        the environment executes the necessary sequence of moves internally.

        Args:
            action: Placement action specifying target position and hold usage

        Returns:
            Step result with observation, reward, done, info
        """
        if self.done:
            return StepResult(self._build_observation(), 0.0, True, {"error": "Game over"})

        # Save original state in case we need to restore on failure
        original_piece = self.current_piece
        original_hold = self.hold_piece
        original_hold_used = self.hold_used_this_turn

        # Validate action is legal
        legal_moves = self.compute_legal_moves()

        # If no legal moves available, game is over (topped out)
        if not legal_moves:
            self.done = True
            return StepResult(
                self._build_observation(),
                0.0,
                True,
                {"error": "Game over - no legal moves (topped out)"}
            )

        target_move = next(
            (m for m in legal_moves if m.x == action.x and m.rot == action.rot and m.use_hold == action.use_hold),
            None
        )

        if target_move is None:
            # Invalid action - return current state with penalty
            return StepResult(
                self._build_observation(),
                -100.0,
                False,
                {"error": f"Invalid placement action: {action}"}
            )

        events = []
        lines_cleared = 0
        old_features = self.last_features.copy()

        # Execute hold if needed
        if action.use_hold:
            if not self._try_hold():
                # Hold failed (already used this turn) - restore state
                self.current_piece = original_piece
                self.hold_piece = original_hold
                self.hold_used_this_turn = original_hold_used
                return StepResult(
                    self._build_observation(),
                    -100.0,
                    False,
                    {"error": "Cannot hold - already used this turn"}
                )
            events.append("hold")

        # Rotate to target rotation
        target_piece_type = self.current_piece.type
        current_rot = self.current_piece.rot
        target_rot = action.rot

        # Calculate shortest rotation path
        rot_diff = (target_rot - current_rot) % 4
        print(f"[step_placement] Rotating: current_rot={current_rot}, target_rot={target_rot}, rot_diff={rot_diff}", flush=True)
        for i in range(rot_diff):
            if not self._try_rotate(clockwise=True):
                # Rotation failed - restore state
                print(f"[step_placement] Rotation FAILED at step {i}", flush=True)
                self.current_piece = original_piece
                self.hold_piece = original_hold
                self.hold_used_this_turn = original_hold_used
                return StepResult(
                    self._build_observation(),
                    -100.0,
                    False,
                    {"error": f"Failed to rotate to target rotation {target_rot}"}
                )

        # Move to target x position
        target_x = action.x
        current_x = self.current_piece.x
        dx = target_x - current_x

        print(f"[step_placement] Moving horizontally: current_x={current_x}, target_x={target_x}, dx={dx}", flush=True)
        if dx != 0:
            direction = 1 if dx > 0 else -1
            for i in range(abs(dx)):
                print(f"[step_placement] Move step {i+1}/{abs(dx)}: piece.x={self.current_piece.x}, direction={direction}", flush=True)
                if not self._try_move(direction, 0):
                    # Movement failed - restore state
                    print(f"[step_placement] Movement FAILED at step {i}: current_x={self.current_piece.x}, target_x={target_x}", flush=True)
                    print(f"[step_placement] RESTORING: original piece was at x={original_piece.x}, rot={original_piece.rot}", flush=True)
                    self.current_piece = original_piece
                    self.hold_piece = original_hold
                    self.hold_used_this_turn = original_hold_used
                    print(f"[step_placement] RESTORED: current piece now at x={self.current_piece.x}, rot={self.current_piece.rot}", flush=True)
                    return StepResult(
                        self._build_observation(),
                        -100.0,
                        False,
                        {"error": f"Failed to move to target x position {target_x}"}
                    )

        # Hard drop
        lines_from_drop, spawned = self._hard_drop()
        events.append("hard_drop")
        if lines_from_drop > 0:
            lines_cleared = lines_from_drop
            events.append("clear")
        if spawned:
            events.append("spawn")

        # Compute features and deltas
        new_features = compute_features(self.board)
        feature_deltas = compute_feature_deltas(old_features, new_features)
        self.last_features = new_features

        obs = self._build_observation()
        info = {
            "lines_cleared": lines_cleared,
            "delta": feature_deltas,
            "events": events,
        }

        # Compute reward (can be customized by reward shaper later)
        reward = float(lines_cleared * 100)  # Simple: 100 points per line
        if self.done:
            reward -= 500  # Penalty for game over
            events.append("top_out")

        return StepResult(obs, reward, self.done, info)

    def _spawn_piece(self) -> None:
        """Spawn the next piece."""
        next_type = self.rng.next()
        x, y = get_spawn_position(next_type)
        self.current_piece = Piece(next_type, x, y, rot=0)

    def _try_move(self, dx: int, dy: int) -> bool:
        """Try to move the current piece.

        Args:
            dx: Change in x
            dy: Change in y

        Returns:
            True if move succeeded
        """
        if not self.current_piece:
            return False

        new_piece = self.current_piece.move(dx, dy)
        if not self.board.collides(new_piece):
            self.current_piece = new_piece
            return True
        return False

    def _try_rotate(self, clockwise: bool) -> bool:
        """Try to rotate the current piece.

        Args:
            clockwise: Rotation direction

        Returns:
            True if rotation succeeded
        """
        if not self.current_piece:
            return False

        rotated = self.srs.try_rotate(self.board, self.current_piece, clockwise)
        if rotated:
            self.current_piece = rotated
            return True
        return False

    def _hard_drop(self) -> Tuple[int, bool]:
        """Hard drop the current piece.

        Returns:
            Tuple of (lines_cleared, spawned_new_piece)
        """
        if not self.current_piece:
            return (0, False)

        # Drop down until collision (y=0 is top, y=19 is bottom)
        while not self.board.collides(self.current_piece.move(0, 1)):
            self.current_piece = self.current_piece.move(0, 1)

        # Immediately lock
        self.board.lock_piece(self.current_piece)
        lines_cleared = self.board.clear_lines()
        if lines_cleared > 0:
            self.lines_total += lines_cleared
            self.score += calculate_score(lines_cleared)

        self._spawn_piece()
        self.hold_used_this_turn = False

        if self.board.collides(self.current_piece):
            self.done = True

        return (lines_cleared, True)

    def _try_hold(self) -> bool:
        """Try to hold the current piece.

        Returns:
            True if hold succeeded
        """
        if self.hold_used_this_turn or not self.current_piece:
            return False

        if self.hold_piece is None:
            # First hold
            self.hold_piece = self.current_piece.type
            self._spawn_piece()
        else:
            # Swap with held piece
            temp = self.hold_piece
            self.hold_piece = self.current_piece.type
            x, y = get_spawn_position(temp)
            self.current_piece = Piece(temp, x, y, rot=0)

        # Check if the spawned piece collides (top out condition)
        if self.board.collides(self.current_piece):
            self.done = True

        self.hold_used_this_turn = True
        return True

    def compute_legal_moves(self) -> List[LegalMove]:
        """Compute all legal placement positions.

        This checks both that the piece CAN land at a position AND that it can
        REACH that position from spawn by rotating and moving horizontally.

        Returns:
            List of legal moves
        """
        if not self.current_piece:
            return []

        moves = []
        pieces_to_try = [self.current_piece.type]

        if self.hold_enabled and self.hold_piece and not self.hold_used_this_turn:
            pieces_to_try.append(self.hold_piece)

        for piece_type in pieces_to_try:
            use_hold = piece_type != self.current_piece.type

            if use_hold:
                spawn_x, spawn_y = get_spawn_position(piece_type)
                start_piece = Piece(piece_type, spawn_x, spawn_y, rot=0)
            else:
                start_piece = self.current_piece.copy()

            for target_rot in range(4):
                shape = PIECE_SHAPES[piece_type][target_rot]
                min_dx = min(dx for dx, _ in shape)
                max_dx = max(dx for dx, _ in shape)

                min_x = -min_dx
                max_x = self.board.WIDTH - 1 - max_dx

                for target_x in range(min_x, max_x + 1):
                    # Start from the piece's current/spawn state
                    test_piece = Piece(
                        piece_type, start_piece.x, start_piece.y, start_piece.rot
                    )

                    if self.board.collides(test_piece):
                        continue

                    # Rotate toward the desired orientation (clockwise steps)
                    rot_diff = (target_rot - test_piece.rot) % 4
                    rotation_succeeded = True
                    for _ in range(rot_diff):
                        if self.srs_enabled:
                            rotated = self.srs.try_rotate(
                                self.board, test_piece, clockwise=True
                            )
                        else:
                            rotated = test_piece.rotate(clockwise=True)
                            if self.board.collides(rotated):
                                rotated = None

                        if not rotated:
                            rotation_succeeded = False
                            break

                        test_piece = rotated

                    if not rotation_succeeded:
                        continue

                    # Translate horizontally to the target x
                    dx = target_x - test_piece.x
                    movement_succeeded = True
                    if dx != 0:
                        direction = 1 if dx > 0 else -1
                        for _ in range(abs(dx)):
                            moved = test_piece.move(direction, 0)
                            if self.board.collides(moved):
                                movement_succeeded = False
                                break
                            test_piece = moved

                        if not movement_succeeded:
                            continue

                    # Drop until collision
                    drop_piece = test_piece
                    while True:
                        moved_down = drop_piece.move(0, 1)
                        if self.board.collides(moved_down):
                            break
                        drop_piece = moved_down

                    moves.append(
                        LegalMove(drop_piece.x, drop_piece.rot, use_hold, drop_piece.y)
                    )

        # Remove duplicates
        unique_moves = []
        seen = set()
        for move in moves:
            key = (move.x, move.rot, move.use_hold, move.harddrop_y)
            if key not in seen:
                seen.add(key)
                unique_moves.append(move)

        return unique_moves

    def _build_observation(self) -> Observation:
        """Build the current observation.

        Returns:
            Complete observation
        """
        return Observation(
            schema_version=self.SCHEMA_VERSION,
            tick=self.tick,
            board=self.board.copy(),
            current=self.current_piece.copy() if self.current_piece else Piece("I", 0, 0),
            next_queue=self.rng.peek(self.next_queue_size) if self.rng else [],
            hold_type=self.hold_piece,
            hold_used=self.hold_used_this_turn,
            features=compute_features(self.board),
            score=self.score,
            lines_total=self.lines_total,
            top_out=self.done,
            seed=self.seed,
            legal_moves=self.compute_legal_moves(),
            srs_enabled=self.srs_enabled,
            hold_enabled=self.hold_enabled,
        )
