"""Tests for 7-bag RNG."""

from tetris_core.rng import SevenBagRNG


def test_seven_bag_deterministic():
    """Test that same seed produces same sequence."""
    rng1 = SevenBagRNG(12345)
    rng2 = SevenBagRNG(12345)

    sequence1 = [rng1.next() for _ in range(21)]  # 3 full bags
    sequence2 = [rng2.next() for _ in range(21)]

    assert sequence1 == sequence2, "Same seed should produce identical sequences"


def test_seven_bag_contains_all_pieces():
    """Test that each bag contains all 7 pieces."""
    rng = SevenBagRNG(42)

    # Get first bag (7 pieces)
    bag = [rng.next() for _ in range(7)]

    # Check all pieces present
    assert sorted(bag) == ["I", "J", "L", "O", "S", "T", "Z"]


def test_seven_bag_peek():
    """Test peeking ahead without consuming."""
    rng = SevenBagRNG(999)

    # Peek ahead
    peeked = rng.peek(5)

    # Actual sequence should match peeked
    actual = [rng.next() for _ in range(5)]

    assert peeked == actual, "Peek should match actual sequence"


def test_seven_bag_reset():
    """Test resetting with new seed."""
    rng = SevenBagRNG(111)
    first_piece = rng.next()

    rng.reset(111)
    reset_piece = rng.next()

    assert first_piece == reset_piece, "Reset should restart sequence"
