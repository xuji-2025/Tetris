"""Runner framework for executing and evaluating agents."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import time

from tetris_core.agent import Agent
from tetris_core.env import TetrisEnv, PlacementAction


@dataclass
class EpisodeStats:
    """Statistics for a single episode."""

    seed: int
    score: int
    lines_cleared: int
    pieces_placed: int
    ticks: int
    duration_seconds: float
    final_board_state: List[int]  # Flat array of board cells
    max_height: int
    total_holes: int
    top_out: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "seed": self.seed,
            "score": self.score,
            "lines_cleared": self.lines_cleared,
            "pieces_placed": self.pieces_placed,
            "ticks": self.ticks,
            "duration_seconds": self.duration_seconds,
            "max_height": self.max_height,
            "total_holes": self.total_holes,
            "top_out": self.top_out,
        }


@dataclass
class BenchmarkResults:
    """Results from running a benchmark."""

    agent_name: str
    num_episodes: int
    episodes: List[EpisodeStats] = field(default_factory=list)

    def get_summary(self) -> dict:
        """Get summary statistics across all episodes."""
        if not self.episodes:
            return {}

        return {
            "agent_name": self.agent_name,
            "num_episodes": self.num_episodes,
            "avg_score": sum(e.score for e in self.episodes) / len(self.episodes),
            "avg_lines": sum(e.lines_cleared for e in self.episodes)
            / len(self.episodes),
            "avg_pieces": sum(e.pieces_placed for e in self.episodes)
            / len(self.episodes),
            "max_score": max(e.score for e in self.episodes),
            "max_lines": max(e.lines_cleared for e in self.episodes),
            "max_pieces": max(e.pieces_placed for e in self.episodes),
            "min_score": min(e.score for e in self.episodes),
            "min_lines": min(e.lines_cleared for e in self.episodes),
            "min_pieces": min(e.pieces_placed for e in self.episodes),
            "avg_duration": sum(e.duration_seconds for e in self.episodes)
            / len(self.episodes),
            "total_duration": sum(e.duration_seconds for e in self.episodes),
        }


class Runner:
    """Framework for running agents and collecting statistics."""

    def __init__(
        self,
        srs_enabled: bool = True,
        hold_enabled: bool = True,
        lock_delay_ticks: int = 30,
        verbose: bool = True,
    ):
        """Initialize runner.

        Args:
            srs_enabled: Enable SRS wall kicks
            hold_enabled: Enable hold functionality
            lock_delay_ticks: Lock delay in ticks
            verbose: Print progress messages
        """
        self.srs_enabled = srs_enabled
        self.hold_enabled = hold_enabled
        self.lock_delay_ticks = lock_delay_ticks
        self.verbose = verbose

    def run_episode(
        self, agent: Agent, seed: int, max_pieces: Optional[int] = None
    ) -> EpisodeStats:
        """Run a single episode with an agent.

        Args:
            agent: Agent to run
            seed: Random seed for episode
            max_pieces: Maximum pieces to place (None = no limit)

        Returns:
            Episode statistics
        """
        env = TetrisEnv(
            srs_enabled=self.srs_enabled,
            hold_enabled=self.hold_enabled,
            lock_delay_ticks=self.lock_delay_ticks,
        )

        obs = env.reset(seed)
        agent.on_episode_start(seed)

        pieces_placed = 0
        start_time = time.time()

        while not obs.top_out:
            # Agent selects action
            action = agent.select_action(obs)

            # Execute action
            result = env.step_placement(action)

            # Notify agent of result
            agent.on_step_result(result)

            obs = result.obs
            pieces_placed += 1

            # Check max pieces limit
            if max_pieces is not None and pieces_placed >= max_pieces:
                break

        duration = time.time() - start_time

        # Compute final stats
        max_height = max(obs.board.get_column_heights())
        total_holes = obs.features.get("holes", 0)

        stats = EpisodeStats(
            seed=seed,
            score=obs.score,
            lines_cleared=obs.lines_total,
            pieces_placed=pieces_placed,
            ticks=obs.tick,
            duration_seconds=duration,
            final_board_state=obs.board.to_list(),
            max_height=max_height,
            total_holes=total_holes,
            top_out=obs.top_out,
        )

        # Notify agent of episode end
        agent.on_episode_end(obs.score, obs.lines_total, pieces_placed)

        if self.verbose:
            print(
                f"Episode {seed}: {pieces_placed} pieces, "
                f"{obs.lines_total} lines, score {obs.score} "
                f"({duration:.2f}s)"
            )

        return stats

    def run_benchmark(
        self,
        agent: Agent,
        num_episodes: int,
        seeds: Optional[List[int]] = None,
        max_pieces: Optional[int] = None,
    ) -> BenchmarkResults:
        """Run a benchmark with multiple episodes.

        Args:
            agent: Agent to benchmark
            num_episodes: Number of episodes to run
            seeds: List of seeds (if None, use 0, 1, 2, ...)
            max_pieces: Maximum pieces per episode (None = no limit)

        Returns:
            Benchmark results
        """
        if seeds is None:
            seeds = list(range(num_episodes))
        elif len(seeds) < num_episodes:
            raise ValueError(
                f"Need {num_episodes} seeds, got {len(seeds)}"
            )

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Running benchmark: {agent.name}")
            print(f"Episodes: {num_episodes}")
            print(f"{'='*60}\n")

        results = BenchmarkResults(agent_name=agent.name, num_episodes=num_episodes)

        for i, seed in enumerate(seeds[:num_episodes]):
            if self.verbose:
                print(f"[{i+1}/{num_episodes}] ", end="", flush=True)

            stats = self.run_episode(agent, seed, max_pieces)
            results.episodes.append(stats)

        if self.verbose:
            summary = results.get_summary()
            print(f"\n{'='*60}")
            print(f"Benchmark complete: {agent.name}")
            print(f"{'='*60}")
            print(f"Avg score: {summary['avg_score']:.1f}")
            print(f"Avg lines: {summary['avg_lines']:.1f}")
            print(f"Avg pieces: {summary['avg_pieces']:.1f}")
            print(f"Max lines: {summary['max_lines']}")
            print(f"Total duration: {summary['total_duration']:.1f}s")
            print(f"{'='*60}\n")

        return results

    def compare_agents(
        self,
        agents: List[Agent],
        num_episodes: int,
        seeds: Optional[List[int]] = None,
        max_pieces: Optional[int] = None,
    ) -> Dict[str, BenchmarkResults]:
        """Compare multiple agents on the same seeds.

        Args:
            agents: List of agents to compare
            num_episodes: Number of episodes per agent
            seeds: List of seeds (same for all agents)
            max_pieces: Maximum pieces per episode

        Returns:
            Dictionary mapping agent names to benchmark results
        """
        if seeds is None:
            seeds = list(range(num_episodes))

        results = {}

        for agent in agents:
            benchmark = self.run_benchmark(agent, num_episodes, seeds, max_pieces)
            results[agent.name] = benchmark

        # Print comparison
        if self.verbose:
            self._print_comparison(results)

        return results

    def _print_comparison(self, results: Dict[str, BenchmarkResults]) -> None:
        """Print comparison table."""
        print(f"\n{'='*80}")
        print("AGENT COMPARISON")
        print(f"{'='*80}")
        print(
            f"{'Agent':<20} {'Avg Lines':<12} {'Avg Pieces':<12} {'Avg Score':<12} {'Max Lines':<12}"
        )
        print(f"{'-'*80}")

        for name, benchmark in results.items():
            summary = benchmark.get_summary()
            print(
                f"{name:<20} "
                f"{summary['avg_lines']:<12.1f} "
                f"{summary['avg_pieces']:<12.1f} "
                f"{summary['avg_score']:<12.1f} "
                f"{summary['max_lines']:<12}"
            )

        print(f"{'='*80}\n")
