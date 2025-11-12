"""7-bag random number generator for Tetris pieces.

The 7-bag system ensures fair piece distribution by shuffling all 7 pieces
into a bag, dealing them out, then reshuffling for the next bag.
"""

import random
from typing import List


class SevenBagRNG:
    """Deterministic 7-bag piece generator."""

    PIECES = ["I", "O", "T", "S", "Z", "J", "L"]

    def __init__(self, seed: int):
        """Initialize with a seed for deterministic replay.

        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        self.rng = random.Random(seed)
        self.bag: List[str] = []
        self._refill_bag()

    def _refill_bag(self) -> None:
        """Shuffle all 7 pieces into the bag."""
        self.bag = self.PIECES.copy()
        self.rng.shuffle(self.bag)

    def next(self) -> str:
        """Get the next piece from the bag.

        Returns:
            Piece type string ("I", "O", "T", "S", "Z", "J", "L")
        """
        if not self.bag:
            self._refill_bag()
        return self.bag.pop()

    def peek(self, count: int) -> List[str]:
        """Peek at the next N pieces without consuming them.

        Args:
            count: Number of pieces to peek ahead

        Returns:
            List of piece types
        """
        result = []
        temp_bag = self.bag.copy()
        temp_rng = random.Random()
        temp_rng.setstate(self.rng.getstate())

        for _ in range(count):
            if not temp_bag:
                temp_bag = self.PIECES.copy()
                temp_rng.shuffle(temp_bag)
            result.append(temp_bag.pop())

        return result

    def reset(self, seed: int) -> None:
        """Reset the RNG with a new seed.

        Args:
            seed: New random seed
        """
        self.seed = seed
        self.rng = random.Random(seed)
        self.bag = []
        self._refill_bag()
