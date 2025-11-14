"""SmartDellacherieAgent - Optimized for scoring efficiency via multi-line clears.

This agent extends the classic Dellacherie heuristic with additional features
that encourage Tetris (4-line) setups and multi-line clears for higher scores.

Key differences from DellacherieAgent:
- Rewards maintaining a clean well for I-pieces (Tetris setup)
- Prioritizes multi-line clears over single-line clears
- Uses next queue to time big clears when I-piece is available
- More risk-tolerant (accepts higher stacks for bigger payoffs)
"""

from typing import Tuple
from copy import deepcopy

from tetris_core.agent import Agent
from tetris_core.env import Observation, PlacementAction, LegalMove
from tetris_core.board import Board
from tetris_core.piece import Piece


class SmartDellacherieAgent(Agent):
    """Agent optimized for scoring efficiency via multi-line clears.

    Extends classic Dellacherie features with:
    1. Tetris readiness: Rewards clean wells suitable for I-piece
    2. Multi-line potential: Rewards setups with multiple near-full rows
    3. I-piece timing: Uses next queue to decide when to cash in
    4. Well quality: Prefers single clean well over scattered holes
    """

    # Optimized weights for scoring efficiency
    # Base weights from Dellacherie, adjusted for multi-line clears
    WEIGHTS = {
        # Original Dellacherie features (adjusted)
        "landing_height": -3.5,  # Less penalty (accept higher stacks)
        "eroded_cells": 5.0,  # Higher reward (prioritize clears)
        "row_transitions": -2.5,  # Slightly less penalty (ok with setup)
        "col_transitions": -8.0,  # Still important (avoid fragmentation)
        "holes": -10.0,  # Higher penalty (holes are worse for Tetrises)
        "wells": -1.0,  # Much less penalty (we WANT a good well)
        # New features for efficiency
        "tetris_ready": 8.0,  # Strong reward for Tetris setup
        "multi_line_potential": 3.0,  # Reward multiple near-full rows
        "well_quality": 5.0,  # Reward single clean well
        "i_piece_available": 2.0,  # Bonus when I-piece in next queue
    }

    def __init__(self):
        """Initialize SmartDellacherie agent."""
        super().__init__(name="SmartDellacherie")

    def select_action(self, obs: Observation) -> PlacementAction:
        """Select best move for scoring efficiency.

        Args:
            obs: Current observation

        Returns:
            Best placement action
        """
        if not obs.legal_moves:
            return PlacementAction(x=0, rot=0, use_hold=False)

        best_score = float("-inf")
        best_move = obs.legal_moves[0]

        # Check if I-piece is available in next queue
        i_piece_available = "I" in obs.next_queue

        for move in obs.legal_moves:
            features = self.compute_features(obs, move, i_piece_available)
            score = sum(self.WEIGHTS[k] * features[k] for k in self.WEIGHTS)

            if score > best_score:
                best_score = score
                best_move = move

        return PlacementAction(
            x=best_move.x,
            rot=best_move.rot,
            use_hold=best_move.use_hold
        )

    def compute_features(self, obs: Observation, move: LegalMove, i_piece_available: bool) -> dict:
        """Compute enhanced features for a given move.

        Args:
            obs: Current observation
            move: Legal move to evaluate
            i_piece_available: Whether I-piece is in next queue

        Returns:
            Dictionary of feature values
        """
        # Simulate placing the piece
        board = obs.board.copy()
        piece_type = obs.hold.type if move.use_hold else obs.current.type
        piece = Piece(piece_type, move.x, move.harddrop_y, move.rot)

        # Get piece cells before locking
        piece_cells = piece.get_cells()

        # Lock piece and clear lines
        board.lock_piece(piece)
        lines_cleared = board.clear_lines()

        # Compute original Dellacherie features
        landing_height = self._compute_landing_height(piece_cells)
        eroded_cells = self._compute_eroded_cells(piece_cells, lines_cleared, board)
        row_transitions = self._compute_row_transitions(board)
        col_transitions = self._compute_col_transitions(board)
        holes = self._compute_holes(board)
        wells = self._compute_wells(board)

        # Compute new efficiency features
        tetris_ready = self._compute_tetris_ready(board)
        multi_line_potential = self._compute_multi_line_potential(board)
        well_quality = self._compute_well_quality(board)
        i_available = 1.0 if i_piece_available else 0.0

        return {
            "landing_height": landing_height,
            "eroded_cells": eroded_cells,
            "row_transitions": row_transitions,
            "col_transitions": col_transitions,
            "holes": holes,
            "wells": wells,
            "tetris_ready": tetris_ready,
            "multi_line_potential": multi_line_potential,
            "well_quality": well_quality,
            "i_piece_available": i_available,
        }

    # ===== Original Dellacherie Features =====

    def _compute_landing_height(self, piece_cells: list) -> float:
        """Landing height: Average height of piece cells."""
        if not piece_cells:
            return 0.0
        heights = [20 - y for x, y in piece_cells]
        return sum(heights) / len(heights)

    def _compute_eroded_cells(
        self, piece_cells: list, lines_cleared: int, board: Board
    ) -> float:
        """Eroded piece cells: (rows cleared) × (cells removed from piece)."""
        if lines_cleared == 0:
            return 0.0
        # Bonus for multi-line clears
        multiplier = 1.0
        if lines_cleared == 4:  # Tetris!
            multiplier = 3.0
        elif lines_cleared == 3:
            multiplier = 2.0
        elif lines_cleared == 2:
            multiplier = 1.5
        return float(lines_cleared * len(piece_cells) * multiplier)

    def _compute_row_transitions(self, board: Board) -> int:
        """Row transitions: Occupied→empty transitions in each row."""
        transitions = 0
        for y in range(board.HEIGHT):
            for x in range(board.WIDTH - 1):
                cell = board.get(x, y)
                next_cell = board.get(x + 1, y)
                if (cell > 0) != (next_cell > 0):
                    transitions += 1
            if board.get(0, y) == 0:
                transitions += 1
            if board.get(board.WIDTH - 1, y) == 0:
                transitions += 1
        return transitions

    def _compute_col_transitions(self, board: Board) -> int:
        """Column transitions: Occupied→empty transitions in each column."""
        transitions = 0
        for x in range(board.WIDTH):
            for y in range(board.HEIGHT - 1):
                cell = board.get(x, y)
                next_cell = board.get(x, y + 1)
                if (cell > 0) != (next_cell > 0):
                    transitions += 1
            if board.get(x, 0) == 0:
                transitions += 1
            if board.get(x, board.HEIGHT - 1) == 0:
                transitions += 1
        return transitions

    def _compute_holes(self, board: Board) -> int:
        """Holes: Empty cells with at least one occupied cell above."""
        holes = 0
        for x in range(board.WIDTH):
            found_block = False
            for y in range(board.HEIGHT):
                if board.get(x, y) > 0:
                    found_block = True
                elif found_block and board.get(x, y) == 0:
                    holes += 1
        return holes

    def _compute_wells(self, board: Board) -> int:
        """Wells: Sum of well depths (cumulative)."""
        wells = 0
        for x in range(board.WIDTH):
            for y in range(board.HEIGHT):
                if board.get(x, y) == 0:
                    left_higher = (x == 0) or (board.get(x - 1, y) > 0)
                    right_higher = (x == board.WIDTH - 1) or (board.get(x + 1, y) > 0)

                    if left_higher and right_higher:
                        depth = 0
                        for yy in range(y, board.HEIGHT):
                            if board.get(x, yy) == 0:
                                depth += 1
                            else:
                                break
                        wells += (depth * (depth + 1)) // 2
                        break
        return wells

    # ===== New Efficiency Features =====

    def _compute_tetris_ready(self, board: Board) -> float:
        """Tetris readiness: Reward for having a clean well suitable for I-piece.

        Looks for a single column that is:
        - Empty for at least 4 consecutive rows
        - Preferably on the edge or with one neighbor
        - Has full/near-full rows on other columns

        Returns:
            Score for Tetris readiness (0-10)
        """
        max_readiness = 0.0

        for x in range(board.WIDTH):
            # Find the deepest well in this column
            well_depth = 0
            well_start_y = -1

            for y in range(board.HEIGHT):
                if board.get(x, y) == 0:
                    if well_start_y == -1:
                        well_start_y = y
                    well_depth += 1
                else:
                    break

            if well_depth >= 4:
                # Check if adjacent columns are fuller (good Tetris setup)
                left_height = self._get_column_height(board, x - 1) if x > 0 else 20
                right_height = self._get_column_height(board, x + 1) if x < board.WIDTH - 1 else 20

                # Reward deeper wells and edge positions
                readiness = well_depth / 4.0  # Base score from depth

                # Bonus for edge position (easier to manage)
                if x == 0 or x == board.WIDTH - 1:
                    readiness += 2.0

                # Bonus if neighbors are tall (good setup)
                avg_neighbor_height = (left_height + right_height) / 2
                if avg_neighbor_height >= well_depth + 3:
                    readiness += 3.0

                max_readiness = max(max_readiness, readiness)

        return max_readiness

    def _compute_multi_line_potential(self, board: Board) -> float:
        """Multi-line potential: Reward for multiple near-full rows.

        Counts rows that are ≥70% full (7+ cells occupied).
        More near-full rows = higher potential for multi-line clear.

        Returns:
            Number of near-full rows
        """
        near_full_rows = 0

        for y in range(board.HEIGHT):
            filled_cells = sum(1 for x in range(board.WIDTH) if board.get(x, y) > 0)
            if filled_cells >= 7:  # 70% full
                near_full_rows += 1

        return float(near_full_rows)

    def _compute_well_quality(self, board: Board) -> float:
        """Well quality: Reward single clean well over scattered holes.

        A quality well is:
        - Deep (4+ rows)
        - Clean (no holes in the column)
        - Has at most one well on the board

        Returns:
            Score for well quality (0-10)
        """
        wells_found = []

        for x in range(board.WIDTH):
            # Check if this column has a deep well
            well_depth = 0
            has_holes = False

            for y in range(board.HEIGHT):
                if board.get(x, y) == 0:
                    well_depth += 1
                    # Check if there's a hole (filled cell below)
                    for yy in range(y + 1, board.HEIGHT):
                        if board.get(x, yy) > 0:
                            has_holes = True
                            break
                else:
                    break

            if well_depth >= 4 and not has_holes:
                wells_found.append((x, well_depth))

        # Reward exactly 1 clean deep well
        if len(wells_found) == 1:
            return float(min(wells_found[0][1], 10))  # Cap at 10
        elif len(wells_found) == 0:
            return 0.0
        else:
            # Penalty for multiple wells (scattered setup)
            return -5.0

    def _get_column_height(self, board: Board, x: int) -> int:
        """Get the height of a column (how many rows from bottom to top block).

        Args:
            board: Current board
            x: Column index

        Returns:
            Height of the column (0-20)
        """
        if x < 0 or x >= board.WIDTH:
            return 0

        for y in range(board.HEIGHT):
            if board.get(x, y) > 0:
                return board.HEIGHT - y

        return 0
