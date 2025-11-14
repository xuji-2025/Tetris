"""Protocol data classes for WebSocket communication.

Based on proto/schema/v1.json
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Literal
from enum import Enum


class MessageType(str, Enum):
    """WebSocket message types."""
    HELLO = "hello"
    RESET = "reset"
    STEP = "step"
    STEP_PLACEMENT = "step_placement"
    AI_PLAY = "ai_play"
    AI_STOP = "ai_stop"
    COMPARE_START = "compare_start"
    COMPARE_STOP = "compare_stop"
    COMPARE_SET_SPEED = "compare_set_speed"
    SUBSCRIBE = "subscribe"
    OBS = "obs"
    COMPARE_OBS = "compare_obs"
    COMPARE_COMPLETE = "compare_complete"
    ERROR = "error"


@dataclass
class HelloRequest:
    """Client hello message."""
    type: Literal["hello"] = "hello"
    version: str = "s1.0.0"


@dataclass
class HelloResponse:
    """Server hello response."""
    type: Literal["hello"] = "hello"
    version: str = "s1.0.0"
    server: str = "tetris-core-py"


@dataclass
class ResetRequest:
    """Request to reset the game."""
    seed: Optional[int] = None
    type: Literal["reset"] = "reset"


@dataclass
class StepRequest:
    """Request to step the game with an action."""
    action: str  # Frame action: LEFT, RIGHT, CW, CCW, SOFT, HARD, HOLD, NOOP
    type: Literal["step"] = "step"


@dataclass
class PlacementStepRequest:
    """Request to step the game with a placement action."""
    x: int
    rot: int
    use_hold: bool
    type: Literal["step_placement"] = "step_placement"


@dataclass
class AIPlayRequest:
    """Request to start AI agent playing."""
    agent_type: str  # "random" or "dellacherie"
    seed: Optional[int] = None
    max_pieces: Optional[int] = None
    speed: float = 1.0  # Playback speed multiplier (0.5 = half speed, 2.0 = double speed)
    type: Literal["ai_play"] = "ai_play"


@dataclass
class AIStopRequest:
    """Request to stop AI agent."""
    type: Literal["ai_stop"] = "ai_stop"


@dataclass
class CompareStartRequest:
    """Request to start agent comparison."""
    agent1: str  # Agent type (e.g., "random", "dellacherie")
    agent2: str  # Agent type
    seed: Optional[int] = None
    max_pieces: int = 1000
    speed: float = 1.0  # Playback speed multiplier
    type: Literal["compare_start"] = "compare_start"


@dataclass
class CompareStopRequest:
    """Request to stop agent comparison."""
    type: Literal["compare_stop"] = "compare_stop"


@dataclass
class CompareSetSpeedRequest:
    """Request to change comparison speed during play."""
    speed: float
    type: Literal["compare_set_speed"] = "compare_set_speed"


@dataclass
class GameState:
    """State of a single game in comparison."""
    obs: Dict[str, Any]  # Full observation
    done: bool
    pieces_played: int
    active: bool  # Still playing (not topped out yet)


@dataclass
class ComparisonStats:
    """Comparison statistics between two agents."""
    both_done: bool
    leader: Optional[str]  # "agent1", "agent2", or None if tied
    score_diff: int
    efficiency_agent1: float  # Score per line
    efficiency_agent2: float
    avg_clear_agent1: float  # Average lines cleared per clear
    avg_clear_agent2: float


@dataclass
class CompareObsResponse:
    """Observation response for comparison mode."""
    game1: GameState
    game2: GameState
    comparison: ComparisonStats
    type: Literal["compare_obs"] = "compare_obs"


@dataclass
class FinalGameStats:
    """Final statistics for one game."""
    score: int
    lines: int
    pieces: int
    topped_out: bool
    efficiency: float  # Score per line


@dataclass
class CompareCompleteResponse:
    """Final results when both agents finish."""
    winner: Optional[str]  # "agent1", "agent2", or None if tied
    game1: FinalGameStats
    game2: FinalGameStats
    type: Literal["compare_complete"] = "compare_complete"


@dataclass
class SubscribeRequest:
    """Request to subscribe to game state updates."""
    stream: bool = True
    type: Literal["subscribe"] = "subscribe"


@dataclass
class ObservationResponse:
    """Game state observation response."""
    data: Dict[str, Any]  # Observation dict from env.to_dict()
    reward: float
    done: bool
    info: Dict[str, Any]
    type: Literal["obs"] = "obs"


@dataclass
class ErrorResponse:
    """Error response."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    type: Literal["error"] = "error"


class ErrorCode:
    """Standard error codes."""
    INVALID_MESSAGE = "INVALID_MESSAGE"
    INVALID_ACTION = "INVALID_ACTION"
    GAME_NOT_INITIALIZED = "GAME_NOT_INITIALIZED"
    GAME_OVER = "GAME_OVER"
    VERSION_MISMATCH = "VERSION_MISMATCH"


def parse_message(data: Dict[str, Any]) -> Any:
    """Parse incoming WebSocket message.

    Args:
        data: JSON message dict

    Returns:
        Parsed message object

    Raises:
        ValueError: If message type is invalid
    """
    msg_type = data.get("type")

    if msg_type == MessageType.HELLO:
        return HelloRequest(**data)
    elif msg_type == MessageType.RESET:
        return ResetRequest(**data)
    elif msg_type == MessageType.STEP:
        return StepRequest(**data)
    elif msg_type == MessageType.STEP_PLACEMENT:
        return PlacementStepRequest(**data)
    elif msg_type == MessageType.AI_PLAY:
        return AIPlayRequest(**data)
    elif msg_type == MessageType.AI_STOP:
        return AIStopRequest(**data)
    elif msg_type == MessageType.COMPARE_START:
        return CompareStartRequest(**data)
    elif msg_type == MessageType.COMPARE_STOP:
        return CompareStopRequest(**data)
    elif msg_type == MessageType.COMPARE_SET_SPEED:
        return CompareSetSpeedRequest(**data)
    elif msg_type == MessageType.SUBSCRIBE:
        return SubscribeRequest(**data)
    else:
        raise ValueError(f"Unknown message type: {msg_type}")


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert dataclass to dict for JSON serialization.

    Args:
        obj: Dataclass instance

    Returns:
        Dictionary representation
    """
    return asdict(obj)
