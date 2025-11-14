"""Collection of Tetris AI agents."""

from tetris_core.agents.random_agent import RandomAgent
from tetris_core.agents.dellacherie import DellacherieAgent
from tetris_core.agents.smart_dellacherie import SmartDellacherieAgent

__all__ = ["RandomAgent", "DellacherieAgent", "SmartDellacherieAgent"]
