"""SRS (Super Rotation System) wall kicks and game rules.

SRS defines how pieces rotate and what wall kick offsets to try
when a rotation would otherwise collide.
"""

from typing import Optional
from tetris_core.piece import Piece
from tetris_core.board import Board

# SRS wall kick data: offset tests for each rotation transition
# Format: (from_rot, to_rot) -> list of (dx, dy) offsets to try
# Reference: https://tetris.wiki/Super_Rotation_System

# Wall kick data for J, L, S, T, Z pieces
WALL_KICKS_JLSTZ = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],  # 0->R
    (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],      # R->0
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],      # R->2
    (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],  # 2->R
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],     # 2->L
    (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],   # L->2
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],   # L->0
    (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],     # 0->L
}

# Wall kick data for I piece (different from JLSTZ)
WALL_KICKS_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],   # 0->R
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],   # R->0
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],   # R->2
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],   # 2->R
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],   # 2->L
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],   # L->2
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],   # L->0
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],   # 0->L
}

# O piece doesn't kick (rotations are identical)
WALL_KICKS_O = {}


class SRSRules:
    """Super Rotation System rules implementation."""

    def __init__(self, enabled: bool = True):
        """Initialize SRS rules.

        Args:
            enabled: Whether SRS kicks are enabled
        """
        self.enabled = enabled

    def try_rotate(
        self, board: Board, piece: Piece, clockwise: bool = True
    ) -> Optional[Piece]:
        """Attempt to rotate a piece with wall kicks.

        Args:
            board: Current board state
            piece: Piece to rotate
            clockwise: Rotation direction

        Returns:
            Rotated piece if successful, None if rotation impossible
        """
        # Basic rotation
        rotated = piece.rotate(clockwise)

        # Try without kicks first
        if not board.collides(rotated):
            return rotated

        # If SRS disabled, rotation fails
        if not self.enabled:
            return None

        # Try wall kicks
        kick_table = self._get_kick_table(piece.type)
        from_rot = piece.rot
        to_rot = rotated.rot
        key = (from_rot, to_rot)

        if key not in kick_table:
            return None

        # Try each kick offset
        for dx, dy in kick_table[key]:
            test_piece = Piece(rotated.type, rotated.x + dx, rotated.y + dy, rotated.rot)
            if not board.collides(test_piece):
                return test_piece

        return None

    def _get_kick_table(self, piece_type: str) -> dict:
        """Get the appropriate kick table for a piece type.

        Args:
            piece_type: Piece type

        Returns:
            Wall kick offset dictionary
        """
        if piece_type == "I":
            return WALL_KICKS_I
        elif piece_type == "O":
            return WALL_KICKS_O
        else:
            return WALL_KICKS_JLSTZ


class LockDelay:
    """Lock delay timer for piece placement."""

    def __init__(self, delay_ticks: int = 30):
        """Initialize lock delay.

        Args:
            delay_ticks: Number of ticks before piece locks (default 30 = 0.5s at 60Hz)
        """
        self.delay_ticks = delay_ticks
        self.ticks_on_ground = 0
        self.active = False

    def reset(self) -> None:
        """Reset the lock timer."""
        self.ticks_on_ground = 0
        self.active = False

    def start(self) -> None:
        """Start the lock timer."""
        self.active = True
        self.ticks_on_ground = 0

    def tick(self) -> bool:
        """Advance the timer by one tick.

        Returns:
            True if piece should lock
        """
        if not self.active:
            return False

        self.ticks_on_ground += 1
        return self.ticks_on_ground >= self.delay_ticks

    def is_on_ground(self, board: Board, piece: Piece) -> bool:
        """Check if piece is on the ground (would collide if moved down).

        Args:
            board: Current board
            piece: Current piece

        Returns:
            True if on ground
        """
        moved_down = piece.move(0, 1)  # Move DOWN (increasing y)
        return board.collides(moved_down)


def calculate_score(lines_cleared: int, level: int = 1) -> int:
    """Calculate score from lines cleared (original Nintendo scoring).

    Args:
        lines_cleared: Number of lines cleared simultaneously
        level: Current level multiplier

    Returns:
        Score points
    """
    score_table = {
        0: 0,
        1: 40,    # Single
        2: 100,   # Double
        3: 300,   # Triple
        4: 1200,  # Tetris
    }
    return score_table.get(lines_cleared, 0) * level
