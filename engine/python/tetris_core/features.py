"""Classic engineered features for Tetris board evaluation.

These features are commonly used in heuristic-based and RL agents.
"""

from typing import Dict
from tetris_core.board import Board


def compute_features(board: Board) -> Dict[str, int]:
    """Compute all engineered features for the current board state.

    Args:
        board: Current board

    Returns:
        Dictionary of feature values
    """
    heights = board.get_column_heights()

    return {
        "agg_height": aggregate_height(heights),
        "bumpiness": bumpiness(heights),
        "well_max": max_well_depth(heights),
        "holes": total_holes(board),
        "row_trans": row_transitions(board),
        "col_trans": column_transitions(board),
    }


def aggregate_height(heights: list[int]) -> int:
    """Sum of all column heights.

    Args:
        heights: List of column heights

    Returns:
        Total aggregate height
    """
    return sum(heights)


def bumpiness(heights: list[int]) -> int:
    """Sum of absolute height differences between adjacent columns.

    Args:
        heights: List of column heights

    Returns:
        Total bumpiness
    """
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


def max_well_depth(heights: list[int]) -> int:
    """Maximum well depth (a well is a column lower than both neighbors).

    Args:
        heights: List of column heights

    Returns:
        Depth of deepest well
    """
    max_depth = 0

    # Check left edge
    if len(heights) > 1 and heights[0] < heights[1]:
        max_depth = max(max_depth, heights[1] - heights[0])

    # Check middle columns
    for i in range(1, len(heights) - 1):
        left = heights[i - 1]
        mid = heights[i]
        right = heights[i + 1]
        if mid < left and mid < right:
            depth = min(left, right) - mid
            max_depth = max(max_depth, depth)

    # Check right edge
    if len(heights) > 1 and heights[-1] < heights[-2]:
        max_depth = max(max_depth, heights[-2] - heights[-1])

    return max_depth


def total_holes(board: Board) -> int:
    """Total number of holes (empty cells with filled cells above).

    Args:
        board: Current board

    Returns:
        Total hole count
    """
    return sum(board.get_holes_per_column())


def row_transitions(board: Board) -> int:
    """Count transitions from filled to empty (or vice versa) in rows.

    Args:
        board: Current board

    Returns:
        Total row transitions
    """
    transitions = 0

    for y in range(board.HEIGHT):
        for x in range(board.WIDTH - 1):
            current = board.get(x, y)
            next_cell = board.get(x + 1, y)
            if (current == 0) != (next_cell == 0):
                transitions += 1

        # Count edge transitions (board edges are considered filled)
        if board.get(0, y) == 0:
            transitions += 1
        if board.get(board.WIDTH - 1, y) == 0:
            transitions += 1

    return transitions


def column_transitions(board: Board) -> int:
    """Count transitions from filled to empty (or vice versa) in columns.

    Args:
        board: Current board

    Returns:
        Total column transitions
    """
    transitions = 0

    for x in range(board.WIDTH):
        for y in range(board.HEIGHT - 1):
            current = board.get(x, y)
            next_cell = board.get(x, y + 1)
            if (current == 0) != (next_cell == 0):
                transitions += 1

        # Count top edge transition (top is considered empty)
        if board.get(x, 0) != 0:
            transitions += 1

        # Count bottom edge transition (bottom is considered filled)
        if board.get(x, board.HEIGHT - 1) == 0:
            transitions += 1

    return transitions


def compute_feature_deltas(old_features: Dict[str, int], new_features: Dict[str, int]) -> Dict[str, int]:
    """Compute the change in features between two states.

    Args:
        old_features: Features before action
        new_features: Features after action

    Returns:
        Dictionary of feature deltas
    """
    return {key: new_features[key] - old_features.get(key, 0) for key in new_features}
