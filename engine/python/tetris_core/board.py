"""Tetris board with collision detection and line clearing."""

from typing import List
from tetris_core.piece import Piece


class Board:
    """10x20 Tetris board."""

    WIDTH = 10
    HEIGHT = 20

    def __init__(self):
        """Initialize an empty board."""
        # cells[y * WIDTH + x] represents the cell at (x, y)
        # 0 = empty, 1-7 = filled (piece type encoded)
        self.cells: List[int] = [0] * (self.WIDTH * self.HEIGHT)

    def get(self, x: int, y: int) -> int:
        """Get cell value at (x, y).

        Args:
            x: Column (0-9)
            y: Row (0-19, with 0 at top)

        Returns:
            Cell value (0 = empty, >0 = filled)
        """
        if not self.in_bounds(x, y):
            return 1  # Out of bounds treated as solid
        return self.cells[y * self.WIDTH + x]

    def set(self, x: int, y: int, value: int) -> None:
        """Set cell value at (x, y).

        Args:
            x: Column (0-9)
            y: Row (0-19)
            value: Cell value to set
        """
        if self.in_bounds(x, y):
            self.cells[y * self.WIDTH + x] = value

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within board bounds.

        Args:
            x: Column
            y: Row

        Returns:
            True if in bounds
        """
        return 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT

    def collides(self, piece: Piece) -> bool:
        """Check if a piece collides with the board or boundaries.

        Args:
            piece: The piece to check

        Returns:
            True if collision detected
        """
        for x, y in piece.get_cells():
            if not self.in_bounds(x, y) or self.get(x, y) != 0:
                return True
        return False

    def lock_piece(self, piece: Piece) -> None:
        """Lock a piece onto the board.

        Args:
            piece: The piece to lock
        """
        # Map piece type to cell value (simple encoding)
        piece_values = {"I": 1, "O": 2, "T": 3, "S": 4, "Z": 5, "J": 6, "L": 7}
        value = piece_values.get(piece.type, 1)

        for x, y in piece.get_cells():
            self.set(x, y, value)

    def clear_lines(self) -> int:
        """Clear all complete lines and return count.

        Returns:
            Number of lines cleared
        """
        lines_cleared = 0
        y = self.HEIGHT - 1  # Start from bottom

        while y >= 0:
            if self.is_line_full(y):
                self.remove_line(y)
                lines_cleared += 1
                # Don't decrement y; check the same row again
            else:
                y -= 1

        return lines_cleared

    def is_line_full(self, y: int) -> bool:
        """Check if a line is completely filled.

        Args:
            y: Row to check

        Returns:
            True if line is full
        """
        for x in range(self.WIDTH):
            if self.get(x, y) == 0:
                return False
        return True

    def remove_line(self, line_y: int) -> None:
        """Remove a line and shift everything above down.

        Args:
            line_y: Row to remove
        """
        # Shift all lines above down by one
        for y in range(line_y, 0, -1):
            for x in range(self.WIDTH):
                self.cells[y * self.WIDTH + x] = self.cells[(y - 1) * self.WIDTH + x]

        # Clear the top line
        for x in range(self.WIDTH):
            self.cells[x] = 0

    def get_column_height(self, x: int) -> int:
        """Get the height of a column (distance from bottom to highest block).

        Args:
            x: Column index

        Returns:
            Height (0 = empty column, HEIGHT = full column)
        """
        for y in range(self.HEIGHT):
            if self.get(x, y) != 0:
                return self.HEIGHT - y
        return 0

    def get_column_heights(self) -> List[int]:
        """Get heights of all columns.

        Returns:
            List of 10 heights
        """
        return [self.get_column_height(x) for x in range(self.WIDTH)]

    def count_holes_in_column(self, x: int) -> int:
        """Count holes in a column (empty cells below a filled cell).

        Args:
            x: Column index

        Returns:
            Number of holes
        """
        holes = 0
        found_block = False

        for y in range(self.HEIGHT):
            if self.get(x, y) != 0:
                found_block = True
            elif found_block:
                holes += 1

        return holes

    def get_holes_per_column(self) -> List[int]:
        """Get hole counts for all columns.

        Returns:
            List of 10 hole counts
        """
        return [self.count_holes_in_column(x) for x in range(self.WIDTH)]

    def copy(self) -> "Board":
        """Create a deep copy of the board.

        Returns:
            New board with same state
        """
        new_board = Board()
        new_board.cells = self.cells.copy()
        return new_board

    def to_list(self) -> List[int]:
        """Export board as flat list (for serialization).

        Returns:
            List of 200 cell values
        """
        return self.cells.copy()

    @classmethod
    def from_list(cls, cells: List[int]) -> "Board":
        """Create board from flat list.

        Args:
            cells: List of 200 cell values

        Returns:
            New board
        """
        if len(cells) != cls.WIDTH * cls.HEIGHT:
            raise ValueError(f"Expected {cls.WIDTH * cls.HEIGHT} cells, got {len(cells)}")
        board = cls()
        board.cells = cells.copy()
        return board
