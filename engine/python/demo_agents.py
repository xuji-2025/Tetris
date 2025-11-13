#!/usr/bin/env python3
"""Demo script to run and compare Tetris agents."""

import sys
from tetris_core.agents import RandomAgent, DellacherieAgent
from tetris_core.runner import Runner


def main():
    """Run agent demos."""
    print("TetrisCore Agent Demo")
    print("=" * 60)

    # Create agents
    random_agent = RandomAgent(seed=42)
    dellacherie_agent = DellacherieAgent()

    # Create runner
    runner = Runner(verbose=True)

    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        # Compare agents
        print("\nComparing Random vs Dellacherie...")
        runner.compare_agents(
            agents=[random_agent, dellacherie_agent],
            num_episodes=5,
            max_pieces=100,  # Limit to 100 pieces for demo
        )
    elif len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        # Benchmark Dellacherie
        print("\nBenchmarking Dellacherie agent...")
        results = runner.run_benchmark(
            agent=dellacherie_agent,
            num_episodes=10,
            max_pieces=500,  # 500 pieces per episode
        )
        summary = results.get_summary()
        print(f"\nDellacherie Summary (10 episodes, 500 pieces each):")
        print(f"  Avg lines cleared: {summary['avg_lines']:.1f}")
        print(f"  Max lines cleared: {summary['max_lines']}")
        print(f"  Avg score: {summary['avg_score']:.1f}")
    else:
        # Single episode demo
        print("\n1. Running Random agent (1 episode, 50 pieces)...")
        runner.run_episode(random_agent, seed=42, max_pieces=50)

        print("\n2. Running Dellacherie agent (1 episode, 100 pieces)...")
        runner.run_episode(dellacherie_agent, seed=42, max_pieces=100)

        print("\nTry these commands:")
        print("  python demo_agents.py compare    - Compare agents")
        print("  python demo_agents.py benchmark  - Benchmark Dellacherie")


if __name__ == "__main__":
    main()
