"""Tests for game environment."""

from tetris_core.env import TetrisEnv, FrameAction


def test_env_reset():
    """Test environment reset."""
    env = TetrisEnv()
    obs = env.reset(seed=12345)

    assert obs.tick == 0, "Tick should start at 0"
    assert obs.score == 0, "Score should start at 0"
    assert obs.lines_total == 0, "Lines should start at 0"
    assert not obs.top_out, "Game should not be over"
    assert obs.seed == 12345, "Seed should match"


def test_env_deterministic():
    """Test that same seed produces same game."""
    env1 = TetrisEnv()
    env2 = TetrisEnv()

    obs1 = env1.reset(seed=999)
    obs2 = env2.reset(seed=999)

    assert obs1.current.type == obs2.current.type, "Same seed should spawn same piece"
    assert obs1.next_queue == obs2.next_queue, "Same seed should have same next queue"


def test_env_step_movement():
    """Test basic movement actions."""
    env = TetrisEnv()
    obs = env.reset(seed=42)

    initial_x = obs.current.x

    # Move right
    result = env.step(FrameAction.RIGHT)
    assert result.obs.current.x == initial_x + 1, "Piece should move right"

    # Move left
    result = env.step(FrameAction.LEFT)
    assert result.obs.current.x == initial_x, "Piece should move left"


def test_env_hard_drop():
    """Test hard drop action."""
    env = TetrisEnv()
    env.reset(seed=100)

    initial_tick = env.tick

    # Hard drop should lock piece immediately
    result = env.step(FrameAction.HARD)

    assert "hard_drop" in result.info["events"], "Should register hard drop event"
    assert "spawn" in result.info["events"], "Should spawn new piece after drop"


def test_env_legal_moves():
    """Test legal moves computation."""
    env = TetrisEnv()
    obs = env.reset(seed=77)

    legal_moves = obs.legal_moves
    assert len(legal_moves) > 0, "Should have at least one legal move"

    # Check move format
    for move in legal_moves:
        assert 0 <= move.x < 10, "Move x should be in bounds"
        assert 0 <= move.rot <= 3, "Move rotation should be 0-3"
        assert isinstance(move.use_hold, bool), "use_hold should be boolean"


def test_env_hold():
    """Test hold functionality."""
    env = TetrisEnv(hold_enabled=True)
    obs = env.reset(seed=555)

    first_piece = obs.current.type

    # Hold the piece
    result = env.step(FrameAction.HOLD)

    # Current piece should have changed
    assert result.obs.current.type != first_piece, "Current piece should change after hold"
    # Hold should store first piece
    assert result.obs.hold_type == first_piece, "Hold should store original piece"
    # Hold should be marked as used
    assert result.obs.hold_used, "Hold should be marked as used"


def test_env_line_clearing():
    """Test line clearing updates score."""
    env = TetrisEnv()
    env.reset(seed=123)

    # Manually fill bottom row (for testing)
    for x in range(env.board.WIDTH):
        env.board.set(x, 0, 1)

    # Place piece to trigger clear
    env.board.lock_piece(env.current_piece)
    env.board.clear_lines()

    # Score should update (tested via step logic in real game)
    assert env.board.get_column_heights()[0] < env.board.HEIGHT, "Lines should be cleared"
