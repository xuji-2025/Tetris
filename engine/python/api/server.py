"""FastAPI WebSocket server for TetrisCore."""

import json
import random
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from tetris_core.env import TetrisEnv, FrameAction
from api.protocol import (
    MessageType,
    HelloRequest,
    HelloResponse,
    ResetRequest,
    StepRequest,
    SubscribeRequest,
    ObservationResponse,
    ErrorResponse,
    ErrorCode,
    parse_message,
    to_dict,
)

app = FastAPI(title="TetrisCore API", version="0.1.0")

# Enable CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GameSession:
    """Manages a single game session."""

    def __init__(self):
        self.env: Optional[TetrisEnv] = None
        self.initialized = False
        self.streaming = False

    def reset(self, seed: Optional[int] = None) -> ObservationResponse:
        """Reset the game environment.

        Args:
            seed: Random seed (generates one if None)

        Returns:
            Initial observation response
        """
        if seed is None:
            seed = random.randint(0, 1_000_000)

        if self.env is None:
            self.env = TetrisEnv()

        obs = self.env.reset(seed)
        self.initialized = True

        return ObservationResponse(
            type="obs",
            data=obs.to_dict(),
            reward=0.0,
            done=False,
            info={"event": "reset", "seed": seed},
        )

    def step(self, action: str) -> ObservationResponse:
        """Execute a game step.

        Args:
            action: Frame action string

        Returns:
            Step result as observation response

        Raises:
            ValueError: If game not initialized or action invalid
        """
        if not self.initialized or self.env is None:
            raise ValueError("Game not initialized. Send reset first.")

        try:
            frame_action = FrameAction[action]
        except KeyError:
            raise ValueError(f"Invalid action: {action}")

        result = self.env.step(frame_action)

        return ObservationResponse(
            type="obs",
            data=result.obs.to_dict(),
            reward=result.reward,
            done=result.done,
            info=result.info,
        )

    def set_streaming(self, enabled: bool) -> None:
        """Enable/disable streaming mode.

        Args:
            enabled: Whether to stream observations after every step
        """
        self.streaming = enabled


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "tetris-core-api", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for game communication."""
    await websocket.accept()
    session = GameSession()

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message_dict = json.loads(data)
                message = parse_message(message_dict)

                # Handle different message types
                if isinstance(message, HelloRequest):
                    response = HelloResponse()
                    await websocket.send_text(json.dumps(to_dict(response)))

                elif isinstance(message, ResetRequest):
                    try:
                        obs_response = session.reset(message.seed)
                        await websocket.send_text(json.dumps(to_dict(obs_response)))
                    except Exception as e:
                        error = ErrorResponse(
                            type="error",
                            code=ErrorCode.INVALID_MESSAGE,
                            message=str(e),
                        )
                        await websocket.send_text(json.dumps(to_dict(error)))

                elif isinstance(message, StepRequest):
                    try:
                        obs_response = session.step(message.action)
                        await websocket.send_text(json.dumps(to_dict(obs_response)))
                    except ValueError as e:
                        error = ErrorResponse(
                            type="error",
                            code=ErrorCode.INVALID_ACTION,
                            message=str(e),
                        )
                        await websocket.send_text(json.dumps(to_dict(error)))
                    except Exception as e:
                        error = ErrorResponse(
                            type="error",
                            code=ErrorCode.GAME_NOT_INITIALIZED,
                            message=str(e),
                        )
                        await websocket.send_text(json.dumps(to_dict(error)))

                elif isinstance(message, SubscribeRequest):
                    session.set_streaming(message.stream)
                    # Send acknowledgment
                    response = {
                        "type": "subscribe_ack",
                        "streaming": session.streaming,
                    }
                    await websocket.send_text(json.dumps(response))

                else:
                    error = ErrorResponse(
                        type="error",
                        code=ErrorCode.INVALID_MESSAGE,
                        message=f"Unknown message type: {type(message)}",
                    )
                    await websocket.send_text(json.dumps(to_dict(error)))

            except json.JSONDecodeError as e:
                error = ErrorResponse(
                    type="error",
                    code=ErrorCode.INVALID_MESSAGE,
                    message=f"Invalid JSON: {str(e)}",
                )
                await websocket.send_text(json.dumps(to_dict(error)))

            except ValueError as e:
                error = ErrorResponse(
                    type="error",
                    code=ErrorCode.INVALID_MESSAGE,
                    message=str(e),
                )
                await websocket.send_text(json.dumps(to_dict(error)))

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            error = ErrorResponse(
                type="error",
                code=ErrorCode.INVALID_MESSAGE,
                message=f"Server error: {str(e)}",
            )
            await websocket.send_text(json.dumps(to_dict(error)))
        except:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
