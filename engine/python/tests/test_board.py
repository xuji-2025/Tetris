"""Tests for board functionality."""

from tetris_core.board import Board
from tetris_core.piece import Piece


def test_board_initialization():
    """Test board starts empty."""
    board = Board()
    assert all(cell == 0 for cell in board.cells), "Board should start empty"


def test_collision_detection():
    """Test collision with boundaries and blocks."""
    board = Board()

    # Piece at valid position
    piece = Piece("T", x=4, y=18, rot=0)
    assert not board.collides(piece), "Valid position should not collide"

    # Piece out of bounds (left)
    piece = Piece("T", x=-1, y=10, rot=0)
    assert board.collides(piece), "Out of bounds should collide"

    # Piece out of bounds (right)
    piece = Piece("T", x=9, y=10, rot=0)
    assert board.collides(piece), "Out of bounds should collide"

    # Piece below board
    piece = Piece("T", x=4, y=-1, rot=0)
    assert board.collides(piece), "Below board should collide"


def test_lock_piece():
    """Test locking a piece onto the board."""
    board = Board()
    piece = Piece("I", x=3, y=0, rot=0)

    board.lock_piece(piece)

    # Check that cells are filled
    for x, y in piece.get_cells():
        assert board.get(x, y) != 0, f"Cell ({x}, {y}) should be filled"


def test_line_clearing():
    """Test clearing complete lines."""
    board = Board()

    # Fill bottom row
    for x in range(board.WIDTH):
        board.set(x, 0, 1)

    lines_cleared = board.clear_lines()
    assert lines_cleared == 1, "Should clear one line"

    # Check that line is cleared
    for x in range(board.WIDTH):
        assert board.get(x, 0) == 0, f"Cell ({x}, 0) should be empty after clear"


def test_multiple_line_clearing():
    """Test clearing multiple lines."""
    board = Board()

    # Fill bottom 3 rows
    for y in range(3):
        for x in range(board.WIDTH):
            board.set(x, y, 1)

    lines_cleared = board.clear_lines()
    assert lines_cleared == 3, "Should clear three lines"


def test_column_heights():
    """Test calculating column heights."""
    board = Board()

    # Place blocks in column 5 at different heights
    board.set(5, 18, 1)
    board.set(5, 17, 1)
    board.set(5, 15, 1)  # Gap at 16

    heights = board.get_column_heights()
    assert heights[5] == 5, "Column 5 should have height 5 (from y=15 to bottom)"


def test_holes_detection():
    """Test detecting holes in columns."""
    board = Board()

    # Create a hole in column 3
    board.set(3, 10, 1)  # Block above
    # y=9 is empty (hole)
    board.set(3, 8, 1)   # Block below

    holes = board.count_holes_in_column(3)
    assert holes >= 1, "Should detect at least one hole in column 3"
