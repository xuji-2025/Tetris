"""Dellacherie heuristic agent - one of the strongest handcrafted Tetris AIs.

Based on the classic Dellacherie feature set, which has been shown to clear
millions of lines consistently. This agent evaluates all legal moves using
a linear combination of engineered features.

Reference: Thiery & Scherrer (2009), "Building Controllers for Tetris"
"""

from typing import Tuple
from copy import deepcopy

from tetris_core.agent import Agent
from tetris_core.env import Observation, PlacementAction, LegalMove
from tetris_core.board import Board
from tetris_core.piece import Piece


class DellacherieAgent(Agent):
    """Agent using Dellacherie's handcrafted feature set.

    Features:
    1. Landing height: Height at which piece lands
    2. Eroded piece cells: (rows cleared) × (cells of piece removed)
    3. Row transitions: Occupied→empty or empty→occupied transitions per row
    4. Column transitions: Occupied→empty or empty→occupied transitions per column
    5. Holes: Empty cells with occupied cells above
    6. Wells: Sum of all well depths (valleys between higher columns)

    Weights are tuned values from literature.
    """

    # Optimized weights from Thiery & Scherrer (2009)
    WEIGHTS = {
        "landing_height": -4.500158825082766,
        "eroded_cells": 3.4181268101392694,
        "row_transitions": -3.2178882868487753,
        "col_transitions": -9.348695305445199,
        "holes": -7.899265427351652,
        "wells": -3.3855972247263626,
    }

    def __init__(self):
        """Initialize Dellacherie agent."""
        super().__init__(name="Dellacherie")

    def select_action(self, obs: Observation) -> PlacementAction:
        """Select best move according to Dellacherie features.

        Args:
            obs: Current observation

        Returns:
            Best placement action
        """
        if not obs.legal_moves:
            return PlacementAction(x=0, rot=0, use_hold=False)

        best_score = float("-inf")
        best_move = obs.legal_moves[0]

        for move in obs.legal_moves:
            features = self.compute_features(obs, move)
            score = sum(self.WEIGHTS[k] * features[k] for k in self.WEIGHTS)

            if score > best_score:
                best_score = score
                best_move = move

        return PlacementAction(
            x=best_move.x,
            rot=best_move.rot,
            use_hold=best_move.use_hold
        )

    def compute_features(self, obs: Observation, move: LegalMove) -> dict:
        """Compute Dellacherie features for a given move.

        Args:
            obs: Current observation
            move: Legal move to evaluate

        Returns:
            Dictionary of feature values
        """
        # Simulate placing the piece
        board = obs.board.copy()
        piece_type = obs.hold_type if move.use_hold else obs.current.type
        piece = Piece(piece_type, move.x, move.harddrop_y, move.rot)

        # Get piece cells before locking
        piece_cells = piece.get_cells()

        # Lock piece and clear lines
        board.lock_piece(piece)
        lines_cleared = board.clear_lines()

        # Compute features
        landing_height = self._compute_landing_height(piece_cells)
        eroded_cells = self._compute_eroded_cells(piece_cells, lines_cleared, board)
        row_transitions = self._compute_row_transitions(board)
        col_transitions = self._compute_col_transitions(board)
        holes = self._compute_holes(board)
        wells = self._compute_wells(board)

        return {
            "landing_height": landing_height,
            "eroded_cells": eroded_cells,
            "row_transitions": row_transitions,
            "col_transitions": col_transitions,
            "holes": holes,
            "wells": wells,
        }

    def _compute_landing_height(self, piece_cells: list) -> float:
        """Landing height: Average height of piece cells.

        Args:
            piece_cells: List of (x, y) coordinates

        Returns:
            Average y coordinate (height from bottom)
        """
        if not piece_cells:
            return 0.0
        # y=0 is top, y=19 is bottom, so height = (20 - y)
        heights = [20 - y for x, y in piece_cells]
        return sum(heights) / len(heights)

    def _compute_eroded_cells(
        self, piece_cells: list, lines_cleared: int, board: Board
    ) -> float:
        """Eroded piece cells: (rows cleared) × (cells removed from piece).

        This rewards clearing lines with the current piece.

        Args:
            piece_cells: Original piece cells before clearing
            lines_cleared: Number of lines cleared
            board: Board after clearing

        Returns:
            Product of lines cleared and piece cells eroded
        """
        if lines_cleared == 0:
            return 0.0

        # Count how many piece cells were in cleared rows
        # (This is approximate since we can't track which cells belonged to piece after clearing)
        # In practice, we estimate: if 4 cells and 1 line cleared, assume ~4 cells eroded
        return float(lines_cleared * len(piece_cells))

    def _compute_row_transitions(self, board: Board) -> int:
        """Row transitions: Occupied→empty transitions in each row.

        Args:
            board: Current board

        Returns:
            Total number of horizontal transitions
        """
        transitions = 0
        for y in range(board.HEIGHT):
            for x in range(board.WIDTH - 1):
                cell = board.get(x, y)
                next_cell = board.get(x + 1, y)
                if (cell > 0) != (next_cell > 0):
                    transitions += 1

            # Count transition from board edge to first cell
            if board.get(0, y) == 0:
                transitions += 1
            # Count transition from last cell to board edge
            if board.get(board.WIDTH - 1, y) == 0:
                transitions += 1

        return transitions

    def _compute_col_transitions(self, board: Board) -> int:
        """Column transitions: Occupied→empty transitions in each column.

        Args:
            board: Current board

        Returns:
            Total number of vertical transitions
        """
        transitions = 0
        for x in range(board.WIDTH):
            for y in range(board.HEIGHT - 1):
                cell = board.get(x, y)
                next_cell = board.get(x, y + 1)
                if (cell > 0) != (next_cell > 0):
                    transitions += 1

            # Count transition from top edge to first cell
            if board.get(x, 0) == 0:
                transitions += 1
            # Count transition from last cell to bottom edge
            if board.get(x, board.HEIGHT - 1) == 0:
                transitions += 1

        return transitions

    def _compute_holes(self, board: Board) -> int:
        """Holes: Empty cells with at least one occupied cell above.

        Args:
            board: Current board

        Returns:
            Number of holes
        """
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
        """Wells: Sum of well depths (cumulative).

        A well is a sequence of empty cells in a column with higher neighbors.
        Well depth is 1 + 2 + ... + n for a well of depth n.

        Args:
            board: Current board

        Returns:
            Sum of cumulative well depths
        """
        wells = 0

        for x in range(board.WIDTH):
            for y in range(board.HEIGHT):
                if board.get(x, y) == 0:
                    # Check if this cell is a well (higher or edge on both sides)
                    left_higher = (x == 0) or (board.get(x - 1, y) > 0)
                    right_higher = (x == board.WIDTH - 1) or (board.get(x + 1, y) > 0)

                    if left_higher and right_higher:
                        # Count depth of well starting from this cell
                        depth = 0
                        for yy in range(y, board.HEIGHT):
                            if board.get(x, yy) == 0:
                                depth += 1
                            else:
                                break

                        # Cumulative well depth: 1 + 2 + ... + depth
                        wells += (depth * (depth + 1)) // 2
                        break  # Only count once per column

        return wells
