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
    SUBSCRIBE = "subscribe"
    OBS = "obs"
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
