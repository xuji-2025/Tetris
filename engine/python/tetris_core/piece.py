"""Tetromino piece definitions and rotation logic.

Each piece is defined by its shape in 4 rotation states.
Coordinates are relative to the piece's origin (top-left of bounding box).
"""

from typing import List, Tuple

# Type alias for piece coordinates
Coords = List[Tuple[int, int]]

# Piece shapes in 4 rotation states (0=spawn, 1=R, 2=2, 3=L)
# Format: {piece_type: [rotation_0, rotation_1, rotation_2, rotation_3]}
# Each rotation is a list of (x, y) offsets relative to piece origin
PIECE_SHAPES: dict[str, List[Coords]] = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],  # 0: horizontal
        [(2, 0), (2, 1), (2, 2), (2, 3)],  # R: vertical
        [(0, 2), (1, 2), (2, 2), (3, 2)],  # 2: horizontal (shifted)
        [(1, 0), (1, 1), (1, 2), (1, 3)],  # L: vertical (shifted)
    ],
    "O": [
        [(1, 0), (2, 0), (1, 1), (2, 1)],  # All rotations identical
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],  # 0: T-up
        [(1, 0), (1, 1), (2, 1), (1, 2)],  # R: T-right
        [(0, 1), (1, 1), (2, 1), (1, 2)],  # 2: T-down
        [(1, 0), (0, 1), (1, 1), (1, 2)],  # L: T-left
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],  # 0: horizontal
        [(1, 0), (1, 1), (2, 1), (2, 2)],  # R: vertical
        [(1, 1), (2, 1), (0, 2), (1, 2)],  # 2: horizontal (shifted)
        [(0, 0), (0, 1), (1, 1), (1, 2)],  # L: vertical (shifted)
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],  # 0: horizontal
        [(2, 0), (1, 1), (2, 1), (1, 2)],  # R: vertical
        [(0, 1), (1, 1), (1, 2), (2, 2)],  # 2: horizontal (shifted)
        [(1, 0), (0, 1), (1, 1), (0, 2)],  # L: vertical (shifted)
    ],
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],  # 0: J-up
        [(1, 0), (2, 0), (1, 1), (1, 2)],  # R: J-right
        [(0, 1), (1, 1), (2, 1), (2, 2)],  # 2: J-down
        [(1, 0), (1, 1), (0, 2), (1, 2)],  # L: J-left
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],  # 0: L-up
        [(1, 0), (1, 1), (1, 2), (2, 2)],  # R: L-right
        [(0, 1), (1, 1), (2, 1), (0, 2)],  # 2: L-down
        [(0, 0), (1, 0), (1, 1), (1, 2)],  # L: L-left
    ],
}


class Piece:
    """Represents a tetromino piece at a specific position and rotation."""

    def __init__(self, piece_type: str, x: int = 0, y: int = 0, rot: int = 0):
        """Initialize a piece.

        Args:
            piece_type: One of "I", "O", "T", "S", "Z", "J", "L"
            x: Board x-coordinate (0-9)
            y: Board y-coordinate (0-19, with 0 at top)
            rot: Rotation state (0-3)
        """
        if piece_type not in PIECE_SHAPES:
            raise ValueError(f"Invalid piece type: {piece_type}")
        self.type = piece_type
        self.x = x
        self.y = y
        self.rot = rot % 4

    def get_cells(self) -> List[Tuple[int, int]]:
        """Get absolute board coordinates of all 4 cells.

        Returns:
            List of (x, y) tuples in board coordinates
        """
        offsets = PIECE_SHAPES[self.type][self.rot]
        return [(self.x + dx, self.y + dy) for dx, dy in offsets]

    def get_bounding_box(self) -> Tuple[int, int, int, int]:
        """Get bounding box of the piece.

        Returns:
            (min_x, min_y, max_x, max_y) relative to piece origin
        """
        offsets = PIECE_SHAPES[self.type][self.rot]
        xs = [dx for dx, _ in offsets]
        ys = [dy for _, dy in offsets]
        return (min(xs), min(ys), max(xs), max(ys))

    def copy(self) -> "Piece":
        """Create a copy of this piece."""
        return Piece(self.type, self.x, self.y, self.rot)

    def move(self, dx: int, dy: int) -> "Piece":
        """Return a new piece moved by the given delta.

        Args:
            dx: Change in x
            dy: Change in y

        Returns:
            New piece at the moved position
        """
        return Piece(self.type, self.x + dx, self.y + dy, self.rot)

    def rotate(self, clockwise: bool = True) -> "Piece":
        """Return a new piece rotated.

        Args:
            clockwise: True for clockwise, False for counter-clockwise

        Returns:
            New piece with updated rotation
        """
        new_rot = (self.rot + (1 if clockwise else -1)) % 4
        return Piece(self.type, self.x, self.y, new_rot)

    def __repr__(self) -> str:
        return f"Piece({self.type}, x={self.x}, y={self.y}, rot={self.rot})"


def get_spawn_position(piece_type: str) -> Tuple[int, int]:
    """Get the standard spawn position for a piece type.

    Board coordinates: y=0 is top, y=19 is bottom.
    Pieces spawn at the top of the visible board.

    Args:
        piece_type: One of "I", "O", "T", "S", "Z", "J", "L"

    Returns:
        (x, y) spawn coordinates
    """
    # Standard spawn: horizontally centered, at top of board
    # Spawn at y=1 (near top, room for piece above skyline)
    if piece_type == "I":
        return (3, 1)  # I-piece
    elif piece_type == "O":
        return (4, 1)  # O-piece centered
    else:
        return (3, 1)  # T, S, Z, J, L
