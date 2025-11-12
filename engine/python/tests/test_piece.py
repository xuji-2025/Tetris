"""Tests for piece functionality."""

from tetris_core.piece import Piece, PIECE_SHAPES, get_spawn_position


def test_piece_creation():
    """Test creating a piece."""
    piece = Piece("T", x=4, y=18, rot=0)
    assert piece.type == "T"
    assert piece.x == 4
    assert piece.y == 18
    assert piece.rot == 0


def test_piece_get_cells():
    """Test getting absolute cell coordinates."""
    piece = Piece("O", x=4, y=10, rot=0)
    cells = piece.get_cells()

    assert len(cells) == 4, "O-piece should have 4 cells"
    assert all(isinstance(c, tuple) and len(c) == 2 for c in cells)


def test_piece_rotation():
    """Test piece rotation."""
    piece = Piece("T", x=4, y=10, rot=0)

    # Rotate clockwise
    rotated_cw = piece.rotate(clockwise=True)
    assert rotated_cw.rot == 1, "Should rotate to state 1"

    # Rotate counter-clockwise
    rotated_ccw = piece.rotate(clockwise=False)
    assert rotated_ccw.rot == 3, "Should rotate to state 3"


def test_piece_move():
    """Test piece movement."""
    piece = Piece("I", x=3, y=10, rot=0)

    moved_right = piece.move(1, 0)
    assert moved_right.x == 4, "Should move right"

    moved_down = piece.move(0, -1)
    assert moved_down.y == 9, "Should move down"


def test_all_piece_shapes_defined():
    """Test that all 7 piece types have shapes."""
    expected_pieces = ["I", "O", "T", "S", "Z", "J", "L"]

    for piece_type in expected_pieces:
        assert piece_type in PIECE_SHAPES, f"Missing shape for {piece_type}"
        assert len(PIECE_SHAPES[piece_type]) == 4, f"{piece_type} should have 4 rotations"
        for rot in PIECE_SHAPES[piece_type]:
            assert len(rot) == 4, f"{piece_type} rotation should have 4 cells"


def test_spawn_positions():
    """Test spawn positions are defined."""
    for piece_type in ["I", "O", "T", "S", "Z", "J", "L"]:
        x, y = get_spawn_position(piece_type)
        assert 0 <= x < 10, f"Spawn x for {piece_type} should be in bounds"
        assert 0 <= y < 20, f"Spawn y for {piece_type} should be in bounds"
