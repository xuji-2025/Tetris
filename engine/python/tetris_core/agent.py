"""Base class and interfaces for Tetris AI agents."""

from abc import ABC, abstractmethod
from typing import Optional

from tetris_core.env import Observation, PlacementAction, StepResult


class Agent(ABC):
    """Abstract base class for Tetris agents.

    All AI agents (heuristic, RL, MCTS, etc.) should inherit from this class
    and implement the select_action method.
    """

    def __init__(self, name: str):
        """Initialize agent with a name.

        Args:
            name: Human-readable name for this agent
        """
        self.name = name
        self.episode_count = 0
        self.total_score = 0
        self.total_lines = 0
        self.total_pieces = 0

    @abstractmethod
    def select_action(self, obs: Observation) -> PlacementAction:
        """Select a placement action given the current observation.

        This is the core decision-making method that agents must implement.

        Args:
            obs: Current game observation with board state, current piece,
                 legal moves, features, etc.

        Returns:
            Placement action specifying target position (x, rot, use_hold)
        """
        pass

    def on_episode_start(self, seed: int) -> None:
        """Called when a new episode starts.

        Agents can use this to reset episode-specific state, initialize
        exploration parameters, etc.

        Args:
            seed: Random seed for this episode
        """
        self.episode_count += 1

    def on_step_result(self, result: StepResult) -> None:
        """Called after each step with the result.

        RL agents can use this to store transitions in replay buffers,
        update statistics, perform online learning, etc.

        Args:
            result: Step result containing observation, reward, done, info
        """
        pass

    def on_episode_end(self, final_score: int, final_lines: int, pieces_placed: int) -> None:
        """Called when episode ends.

        Agents can use this to update statistics, save checkpoints,
        log metrics, etc.

        Args:
            final_score: Total score for this episode
            final_lines: Total lines cleared
            pieces_placed: Total pieces placed before game over
        """
        self.total_score += final_score
        self.total_lines += final_lines
        self.total_pieces += pieces_placed

    def get_stats(self) -> dict:
        """Get agent statistics.

        Returns:
            Dictionary with agent statistics
        """
        avg_score = self.total_score / max(1, self.episode_count)
        avg_lines = self.total_lines / max(1, self.episode_count)
        avg_pieces = self.total_pieces / max(1, self.episode_count)

        return {
            "name": self.name,
            "episodes": self.episode_count,
            "total_score": self.total_score,
            "total_lines": self.total_lines,
            "total_pieces": self.total_pieces,
            "avg_score": avg_score,
            "avg_lines": avg_lines,
            "avg_pieces": avg_pieces,
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.episode_count = 0
        self.total_score = 0
        self.total_lines = 0
        self.total_pieces = 0

    def __str__(self) -> str:
        return f"{self.name} (episodes={self.episode_count})"

    def __repr__(self) -> str:
        return f"Agent(name='{self.name}', episodes={self.episode_count})"
