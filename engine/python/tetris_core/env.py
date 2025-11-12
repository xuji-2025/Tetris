"""Tetris environment with gym-like interface.

Provides reset() and step() methods for both human play and RL training.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from tetris_core.board import Board
from tetris_core.piece import Piece, get_spawn_position
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

            for rot in range(4):
                for x in range(self.board.WIDTH):
                    # Start at top of board and drop down
                    test_piece = Piece(piece_type, x, 0, rot)

                    # Skip if immediately collides at spawn
                    if self.board.collides(test_piece):
                        continue

                    # Find the hard drop position (move down until collision)
                    while test_piece.y < self.board.HEIGHT and not self.board.collides(test_piece.move(0, 1)):
                        test_piece = test_piece.move(0, 1)

                    # test_piece is now at the last valid position
                    if not self.board.collides(test_piece):
                        moves.append(LegalMove(x, rot, use_hold, test_piece.y))

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
