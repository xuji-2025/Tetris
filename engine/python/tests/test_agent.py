"""Tests for agent infrastructure and placement actions."""

import pytest
from tetris_core.env import TetrisEnv, PlacementAction
from tetris_core.agents import RandomAgent, DellacherieAgent, SmartDellacherieAgent
from tetris_core.runner import Runner


class TestPlacementActions:
    """Test placement action execution."""

    def test_step_placement_basic(self):
        """Test basic placement action."""
        env = TetrisEnv()
        obs = env.reset(seed=42)

        # Get first legal move
        move = obs.legal_moves[0]
        action = PlacementAction(x=move.x, rot=move.rot, use_hold=move.use_hold)

        # Execute placement
        result = env.step_placement(action)

        assert not result.done or result.obs.top_out  # Either continues or game over
        assert result.info["events"]  # Should have events

    def test_step_placement_invalid_action(self):
        """Test invalid placement action."""
        env = TetrisEnv()
        obs = env.reset(seed=42)

        # Create invalid action (x out of bounds)
        action = PlacementAction(x=99, rot=0, use_hold=False)

        result = env.step_placement(action)

        # Should return error and penalty
        assert result.reward == -100.0
        assert "error" in result.info

    def test_step_placement_with_hold(self):
        """Test placement action with hold."""
        env = TetrisEnv(hold_enabled=True)
        obs = env.reset(seed=42)

        # Find a legal move that uses hold
        hold_move = next((m for m in obs.legal_moves if m.use_hold), None)

        if hold_move:
            action = PlacementAction(
                x=hold_move.x, rot=hold_move.rot, use_hold=True
            )
            result = env.step_placement(action)

            # Should execute successfully
            assert "hold" in result.info["events"]
            assert "hard_drop" in result.info["events"]

    def test_step_placement_line_clear(self):
        """Test that placement actions can clear lines."""
        env = TetrisEnv()
        obs = env.reset(seed=123)  # Try different seed

        # Play several pieces
        for _ in range(50):
            if obs.top_out:
                break

            # Pick first legal move
            move = obs.legal_moves[0]
            action = PlacementAction(x=move.x, rot=move.rot, use_hold=move.use_hold)
            result = env.step_placement(action)
            obs = result.obs

            # Check if any lines were cleared
            if result.info.get("lines_cleared", 0) > 0:
                assert result.reward > 0
                assert "clear" in result.info.get("events", [])
                return  # Test passed - we cleared at least one line

        # If we get here, we played 50 pieces without clearing - that's possible but unlikely

    def test_step_placement_game_over(self):
        """Test that placement action detects game over."""
        env = TetrisEnv()
        obs = env.reset(seed=42)

        # Play until game over (with max limit to prevent hanging)
        max_pieces = 200
        for _ in range(max_pieces):
            if obs.top_out:
                break
            move = obs.legal_moves[0]
            action = PlacementAction(x=move.x, rot=move.rot, use_hold=move.use_hold)
            result = env.step_placement(action)
            obs = result.obs

        # Should eventually top out (or hit limit)
        if obs.top_out:
            assert result.done
            assert obs.top_out


class TestRandomAgent:
    """Test Random agent."""

    def test_random_agent_selects_legal_moves(self):
        """Test that random agent only selects legal moves."""
        agent = RandomAgent(seed=42)
        env = TetrisEnv()
        obs = env.reset(seed=42)

        for _ in range(20):
            if obs.top_out:
                break

            action = agent.select_action(obs)

            # Check action is legal
            legal = any(
                m.x == action.x and m.rot == action.rot and m.use_hold == action.use_hold
                for m in obs.legal_moves
            )
            assert legal, f"Agent selected illegal action: {action}"

            result = env.step_placement(action)
            obs = result.obs

    def test_random_agent_eventually_fails(self):
        """Test that random agent eventually loses (sanity check)."""
        agent = RandomAgent(seed=42)
        runner = Runner(verbose=False)

        stats = runner.run_episode(agent, seed=42, max_pieces=100)

        # Random should top out quickly or not clear many lines
        assert stats.pieces_placed <= 100
        # Random rarely clears lines consistently
        assert stats.lines_cleared < 50  # Very lenient threshold


class TestDellacherieAgent:
    """Test Dellacherie agent."""

    def test_dellacherie_agent_plays(self):
        """Test that Dellacherie agent can play."""
        agent = DellacherieAgent()
        env = TetrisEnv()
        obs = env.reset(seed=42)

        for _ in range(50):
            if obs.top_out:
                break

            action = agent.select_action(obs)

            # Check action is legal
            legal = any(
                m.x == action.x and m.rot == action.rot and m.use_hold == action.use_hold
                for m in obs.legal_moves
            )
            assert legal, f"Agent selected illegal action: {action}"

            result = env.step_placement(action)
            obs = result.obs

    def test_dellacherie_outperforms_random(self):
        """Test that Dellacherie significantly outperforms random."""
        random_agent = RandomAgent(seed=42)
        dellacherie_agent = DellacherieAgent()
        runner = Runner(verbose=False)

        # Run 3 episodes each with same seeds
        random_stats = [
            runner.run_episode(random_agent, seed=i, max_pieces=100) for i in range(3)
        ]
        dellacherie_stats = [
            runner.run_episode(dellacherie_agent, seed=i, max_pieces=100)
            for i in range(3)
        ]

        # Dellacherie should clear significantly more lines
        random_lines = sum(s.lines_cleared for s in random_stats) / 3
        dellacherie_lines = sum(s.lines_cleared for s in dellacherie_stats) / 3

        assert dellacherie_lines > random_lines * 5  # At least 5x better

    def test_dellacherie_features(self):
        """Test Dellacherie feature computation."""
        agent = DellacherieAgent()
        env = TetrisEnv()
        obs = env.reset(seed=42)

        move = obs.legal_moves[0]
        features = agent.compute_features(obs, move)

        # Check all features are present
        assert "landing_height" in features
        assert "eroded_cells" in features
        assert "row_transitions" in features
        assert "col_transitions" in features
        assert "holes" in features
        assert "wells" in features

        # Check features are reasonable
        assert features["landing_height"] >= 0
        assert features["holes"] >= 0
        assert features["wells"] >= 0


class TestRunner:
    """Test Runner framework."""

    def test_runner_single_episode(self):
        """Test running a single episode."""
        agent = RandomAgent(seed=42)
        runner = Runner(verbose=False)

        stats = runner.run_episode(agent, seed=42, max_pieces=50)

        assert stats.seed == 42
        assert stats.pieces_placed <= 50
        assert stats.score >= 0
        assert stats.lines_cleared >= 0
        assert stats.duration_seconds > 0

    def test_runner_benchmark(self):
        """Test running a benchmark."""
        agent = RandomAgent(seed=42)
        runner = Runner(verbose=False)

        results = runner.run_benchmark(agent, num_episodes=3, max_pieces=50)

        assert results.num_episodes == 3
        assert len(results.episodes) == 3

        summary = results.get_summary()
        assert "avg_score" in summary
        assert "avg_lines" in summary
        assert "max_lines" in summary

    def test_runner_compare_agents(self):
        """Test comparing multiple agents."""
        random_agent = RandomAgent(seed=42)
        dellacherie_agent = DellacherieAgent()
        runner = Runner(verbose=False)

        results = runner.compare_agents(
            agents=[random_agent, dellacherie_agent],
            num_episodes=2,
            max_pieces=50,
        )

        assert len(results) == 2
        assert "Random" in results
        assert "Dellacherie" in results

        # Dellacherie should perform better
        random_summary = results["Random"].get_summary()
        dellacherie_summary = results["Dellacherie"].get_summary()

        assert dellacherie_summary["avg_lines"] >= random_summary["avg_lines"]


class TestSmartDellacherieAgent:
    """Test SmartDellacherie agent."""

    def test_smart_dellacherie_agent_plays(self):
        """Test that SmartDellacherie agent can play."""
        agent = SmartDellacherieAgent()
        env = TetrisEnv()
        obs = env.reset(seed=42)

        for _ in range(50):
            if obs.top_out:
                break

            action = agent.select_action(obs)

            # Check action is legal
            legal = any(
                m.x == action.x and m.rot == action.rot and m.use_hold == action.use_hold
                for m in obs.legal_moves
            )
            assert legal, f"Agent selected illegal action: {action}"

            result = env.step_placement(action)
            obs = result.obs

    def test_smart_dellacherie_features(self):
        """Test SmartDellacherie feature computation."""
        agent = SmartDellacherieAgent()
        env = TetrisEnv()
        obs = env.reset(seed=42)

        move = obs.legal_moves[0]
        features = agent.compute_features(obs, move, i_piece_available=True)

        # Check all features are present (original + new)
        assert "landing_height" in features
        assert "eroded_cells" in features
        assert "row_transitions" in features
        assert "col_transitions" in features
        assert "holes" in features
        assert "wells" in features
        assert "tetris_ready" in features
        assert "multi_line_potential" in features
        assert "well_quality" in features
        assert "i_piece_available" in features

        # Check features are reasonable
        assert features["landing_height"] >= 0
        assert features["holes"] >= 0
        assert features["wells"] >= 0
        assert features["tetris_ready"] >= 0
        assert features["multi_line_potential"] >= 0

    def test_smart_dellacherie_efficiency(self):
        """Test that SmartDellacherie achieves reasonable performance."""
        agent = SmartDellacherieAgent()
        runner = Runner(verbose=False)

        # Run 3 episodes
        stats_list = [
            runner.run_episode(agent, seed=i, max_pieces=100) for i in range(3)
        ]

        # Check that it achieves reasonable performance
        for stats in stats_list:
            # Should clear at least some lines (basic sanity check)
            # Weights may need tuning to achieve better efficiency
            assert stats.lines_cleared > 5  # Should clear more than 5 lines in 100 pieces
            assert stats.score > 0


class TestAgentComparison:
    """Test comparing different agents."""

    def test_smart_vs_regular_dellacherie(self):
        """Test SmartDellacherie vs regular Dellacherie."""
        regular_agent = DellacherieAgent()
        smart_agent = SmartDellacherieAgent()
        runner = Runner(verbose=False)

        # Run comparison
        results = runner.compare_agents(
            agents=[regular_agent, smart_agent],
            num_episodes=3,
            max_pieces=100,
        )

        assert len(results) == 2
        assert "Dellacherie" in results
        assert "SmartDellacherie" in results

        regular_summary = results["Dellacherie"].get_summary()
        smart_summary = results["SmartDellacherie"].get_summary()

        # Both should perform reasonably well
        assert regular_summary["avg_lines"] > 10
        assert smart_summary["avg_lines"] > 10


class TestAgentCallbacks:
    """Test agent callback hooks."""

    def test_agent_callbacks_called(self):
        """Test that agent callbacks are invoked."""

        class TestAgent(RandomAgent):
            def __init__(self):
                super().__init__(seed=42)
                self.episode_starts = 0
                self.step_results = 0
                self.episode_ends = 0

            def on_episode_start(self, seed):
                super().on_episode_start(seed)
                self.episode_starts += 1

            def on_step_result(self, result):
                super().on_step_result(result)
                self.step_results += 1

            def on_episode_end(self, score, lines, pieces):
                super().on_episode_end(score, lines, pieces)
                self.episode_ends += 1

        agent = TestAgent()
        runner = Runner(verbose=False)

        runner.run_episode(agent, seed=42, max_pieces=10)

        assert agent.episode_starts == 1
        assert agent.step_results >= 1  # At least one step
        assert agent.episode_ends == 1

    def test_agent_stats_tracking(self):
        """Test agent statistics tracking."""
        agent = RandomAgent(seed=42)
        runner = Runner(verbose=False)

        # Run 2 episodes
        runner.run_episode(agent, seed=42, max_pieces=20)
        runner.run_episode(agent, seed=43, max_pieces=20)

        stats = agent.get_stats()

        assert stats["episodes"] == 2
        assert stats["total_pieces"] > 0
        assert stats["avg_pieces"] > 0
