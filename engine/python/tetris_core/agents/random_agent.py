"""Random agent - picks legal moves uniformly at random."""

import random
from typing import Optional

from tetris_core.agent import Agent
from tetris_core.env import Observation, PlacementAction


class RandomAgent(Agent):
    """Agent that selects actions uniformly at random.

    This serves as a baseline and sanity check for the infrastructure.
    Any serious agent should significantly outperform random play.
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize random agent.

        Args:
            seed: Random seed for reproducibility (optional)
        """
        super().__init__(name="Random")
        self.rng = random.Random(seed)

    def select_action(self, obs: Observation) -> PlacementAction:
        """Select a random legal move.

        Args:
            obs: Current observation

        Returns:
            Random placement action from legal moves
        """
        if not obs.legal_moves:
            # No legal moves - shouldn't happen in normal play
            # Return a dummy action that will fail
            return PlacementAction(x=0, rot=0, use_hold=False)

        # Pick a random legal move
        move = self.rng.choice(obs.legal_moves)

        return PlacementAction(
            x=move.x,
            rot=move.rot,
            use_hold=move.use_hold
        )
