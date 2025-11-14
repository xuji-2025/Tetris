"""FastAPI WebSocket server for TetrisCore."""

import json
import random
import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from tetris_core.env import TetrisEnv, FrameAction, PlacementAction
from tetris_core.agents import RandomAgent, DellacherieAgent, SmartDellacherieAgent
from api.protocol import (
    MessageType,
    HelloRequest,
    HelloResponse,
    ResetRequest,
    StepRequest,
    PlacementStepRequest,
    AIPlayRequest,
    AIStopRequest,
    CompareStartRequest,
    CompareStopRequest,
    CompareSetSpeedRequest,
    SubscribeRequest,
    ObservationResponse,
    ErrorResponse,
    ErrorCode,
    GameState,
    ComparisonStats,
    CompareObsResponse,
    FinalGameStats,
    CompareCompleteResponse,
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

    def __init__(self, websocket: WebSocket):
        self.env: Optional[TetrisEnv] = None
        self.initialized = False
        self.streaming = False
        self.ai_playing = False
        self.ai_task: Optional[asyncio.Task] = None
        self.comparing = False
        self.comparison_task: Optional[asyncio.Task] = None
        self.comparison_speed = 1.0  # Mutable speed for dynamic adjustment
        self.websocket = websocket

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

    def step_placement(self, x: int, rot: int, use_hold: bool) -> ObservationResponse:
        """Execute a placement action.

        Args:
            x: Target x position
            rot: Target rotation
            use_hold: Whether to use hold

        Returns:
            Step result as observation response

        Raises:
            ValueError: If game not initialized
        """
        if not self.initialized or self.env is None:
            raise ValueError("Game not initialized. Send reset first.")

        action = PlacementAction(x=x, rot=rot, use_hold=use_hold)
        result = self.env.step_placement(action)

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

    def stop_ai(self) -> None:
        """Stop AI playback."""
        self.ai_playing = False
        if self.ai_task and not self.ai_task.done():
            self.ai_task.cancel()

    def stop_comparison(self) -> None:
        """Stop agent comparison."""
        self.comparing = False
        if self.comparison_task and not self.comparison_task.done():
            self.comparison_task.cancel()

    async def run_ai_playback(
        self, agent, speed: float, max_pieces: int, seed: Optional[int] = None
    ) -> None:
        """Run AI playback in background.

        Args:
            agent: Agent instance (RandomAgent or DellacherieAgent)
            speed: Playback speed multiplier (0.5 = slower, 2 = faster)
            max_pieces: Maximum number of pieces to play
            seed: Random seed for agent callbacks
        """
        try:
            agent.on_episode_start(seed or 0)
            pieces_played = 0
            delay = 1.0 / speed  # 1x speed = 1 second per piece

            logger.info(f"[AI Playback] Starting: agent={agent.name}, speed={speed}x, max_pieces={max_pieces}")

            while self.ai_playing and not self.env.done and pieces_played < max_pieces:
                # Get current observation
                logger.info(f"[AI Loop] Piece {pieces_played}: Building observation...")
                obs = self.env._build_observation()
                logger.info(f"[AI Loop] Legal moves: {len(obs.legal_moves)}, done={self.env.done}")

                # Check if topped out BEFORE agent selection
                if not obs.legal_moves:
                    logger.info(f"[AI Loop] No legal moves - game over")
                    self.env.done = True
                    break

                # Agent selects action
                logger.info(f"[AI Loop] Agent selecting action from {len(obs.legal_moves)} moves...")
                action = agent.select_action(obs)
                logger.info(f"[AI Loop] Agent selected: x={action.x}, rot={action.rot}, hold={action.use_hold}")

                # Execute placement action
                logger.info(f"[AI Loop] Executing placement...")
                obs_response = self.step_placement(
                    action.x, action.rot, action.use_hold
                )
                logger.info(f"[AI Loop] Placement done. done={obs_response.done}")

                # Send observation to client
                logger.info(f"[AI Loop] Sending observation to client...")
                await self.websocket.send_text(json.dumps(to_dict(obs_response)))
                logger.info(f"[AI Loop] Observation sent")

                # Check if game ended
                if obs_response.done:
                    logger.info(f"[AI Loop] Game ended: pieces={pieces_played}, score={obs_response.data.get('episode', {}).get('score', 0)}")
                    break

                pieces_played += 1

                # Delay for visualization
                logger.info(f"[AI Loop] Sleeping {delay}s...")
                await asyncio.sleep(delay)

            # AI finished naturally
            self.ai_playing = False
            logger.info(f"[AI Playback] Ended: done={self.env.done}, pieces={pieces_played}")

        except asyncio.CancelledError:
            # AI was stopped by user
            logger.info(f"[AI Playback] Cancelled by user")
            self.ai_playing = False
            raise
        except Exception as e:
            # Error during AI playback
            logger.error(f"[AI Playback] Error: {e}", exc_info=True)
            self.ai_playing = False

    async def run_comparison(
        self, agent1, agent2, speed: float, max_pieces: int, seed: Optional[int] = None
    ) -> None:
        """Run agent comparison in background.

        Args:
            agent1: First agent instance
            agent2: Second agent instance
            speed: Playback speed multiplier
            max_pieces: Maximum number of pieces to play
            seed: Random seed (same for both agents)
        """
        try:
            # Generate seed if not provided
            if seed is None:
                seed = random.randint(0, 1_000_000)

            # Create two independent environments with same seed
            env1 = TetrisEnv()
            env2 = TetrisEnv()
            env1.reset(seed)
            env2.reset(seed)

            # Initialize agents
            agent1.on_episode_start(seed)
            agent2.on_episode_start(seed)

            # Track state
            pieces1 = 0
            pieces2 = 0
            active1 = True  # Agent 1 still playing
            active2 = True  # Agent 2 still playing
            lines_cleared_count1 = []  # Track each clear size for agent 1
            lines_cleared_count2 = []  # Track each clear size for agent 2

            # Set initial speed (can be changed dynamically during play)
            self.comparison_speed = speed

            logger.info(f"[Comparison] Starting: agent1={agent1.name}, agent2={agent2.name}, seed={seed}, max_pieces={max_pieces}")

            # Continue until BOTH agents finish
            while self.comparing and (active1 or active2):
                # Step agent 1 if still active
                if active1:
                    if pieces1 >= max_pieces:
                        active1 = False
                        logger.info(f"[Comparison] Agent 1 reached max pieces: {pieces1}")
                    else:
                        obs1 = env1._build_observation()
                        if not obs1.legal_moves or env1.done:
                            active1 = False
                            logger.info(f"[Comparison] Agent 1 finished: pieces={pieces1}")
                        else:
                            action1 = agent1.select_action(obs1)
                            result1 = env1.step_placement(PlacementAction(action1.x, action1.rot, action1.use_hold))

                            # Track line clears
                            if result1.info.get("lines_cleared", 0) > 0:
                                lines_cleared_count1.append(result1.info["lines_cleared"])

                            if result1.done:
                                active1 = False
                                logger.info(f"[Comparison] Agent 1 topped out: pieces={pieces1}")
                            pieces1 += 1

                # Step agent 2 if still active
                if active2:
                    if pieces2 >= max_pieces:
                        active2 = False
                        logger.info(f"[Comparison] Agent 2 reached max pieces: {pieces2}")
                    else:
                        obs2 = env2._build_observation()
                        if not obs2.legal_moves or env2.done:
                            active2 = False
                            logger.info(f"[Comparison] Agent 2 finished: pieces={pieces2}")
                        else:
                            action2 = agent2.select_action(obs2)
                            result2 = env2.step_placement(PlacementAction(action2.x, action2.rot, action2.use_hold))

                            # Track line clears
                            if result2.info.get("lines_cleared", 0) > 0:
                                lines_cleared_count2.append(result2.info["lines_cleared"])

                            if result2.done:
                                active2 = False
                                logger.info(f"[Comparison] Agent 2 topped out: pieces={pieces2}")
                            pieces2 += 1

                # Build current observations
                obs1 = env1._build_observation()
                obs2 = env2._build_observation()

                # Calculate statistics
                score1 = env1.score
                score2 = env2.score
                lines1 = env1.lines_total
                lines2 = env2.lines_total

                # Efficiency: score per line (avoid division by zero)
                eff1 = score1 / lines1 if lines1 > 0 else 0
                eff2 = score2 / lines2 if lines2 > 0 else 0

                # Average clear size
                avg_clear1 = sum(lines_cleared_count1) / len(lines_cleared_count1) if lines_cleared_count1 else 0
                avg_clear2 = sum(lines_cleared_count2) / len(lines_cleared_count2) if lines_cleared_count2 else 0

                # Determine leader
                score_diff = score2 - score1
                if score1 > score2:
                    leader = "agent1"
                    score_diff = score1 - score2
                elif score2 > score1:
                    leader = "agent2"
                else:
                    leader = None
                    score_diff = 0

                # Send comparison observation
                compare_obs = CompareObsResponse(
                    game1=GameState(
                        obs=obs1.to_dict(),
                        done=env1.done,
                        pieces_played=pieces1,
                        active=active1
                    ),
                    game2=GameState(
                        obs=obs2.to_dict(),
                        done=env2.done,
                        pieces_played=pieces2,
                        active=active2
                    ),
                    comparison=ComparisonStats(
                        both_done=(not active1 and not active2),
                        leader=leader,
                        score_diff=score_diff,
                        efficiency_agent1=round(eff1, 1),
                        efficiency_agent2=round(eff2, 1),
                        avg_clear_agent1=round(avg_clear1, 2),
                        avg_clear_agent2=round(avg_clear2, 2)
                    )
                )

                # Both done? Time to send final results
                if not active1 and not active2:
                    logger.info(f"[Comparison] Both agents finished")
                    break

                # Send periodic update (but don't break if it fails - we want to finish the game)
                try:
                    await self.websocket.send_text(json.dumps(to_dict(compare_obs)))
                except Exception as e:
                    logger.warning(f"[Comparison] Failed to send update (client may have disconnected): {e}")
                    # Continue anyway - we want to complete the comparison

                # Delay for visualization (use current speed, which can change during play)
                delay = 1.0 / self.comparison_speed
                await asyncio.sleep(delay)

            # Send final results
            eff1_final = score1 / lines1 if lines1 > 0 else 0
            eff2_final = score2 / lines2 if lines2 > 0 else 0

            if score1 > score2:
                winner = "agent1"
            elif score2 > score1:
                winner = "agent2"
            else:
                winner = None

            complete = CompareCompleteResponse(
                winner=winner,
                game1=FinalGameStats(
                    score=score1,
                    lines=lines1,
                    pieces=pieces1,
                    topped_out=env1.done,
                    efficiency=round(eff1_final, 1)
                ),
                game2=FinalGameStats(
                    score=score2,
                    lines=lines2,
                    pieces=pieces2,
                    topped_out=env2.done,
                    efficiency=round(eff2_final, 1)
                )
            )

            try:
                await self.websocket.send_text(json.dumps(to_dict(complete)))
                logger.info(f"[Comparison] Complete message sent: winner={winner}")
            except Exception as e:
                logger.warning(f"[Comparison] Failed to send complete message (client may have disconnected): {e}")

            self.comparing = False
            logger.info(f"[Comparison] Complete: winner={winner}")

        except asyncio.CancelledError:
            logger.info(f"[Comparison] Cancelled by user")
            self.comparing = False
            raise
        except Exception as e:
            logger.error(f"[Comparison] Error: {e}", exc_info=True)
            self.comparing = False
            error = ErrorResponse(
                type="error",
                code=ErrorCode.INVALID_MESSAGE,
                message=f"AI playback error: {str(e)}",
            )
            await self.websocket.send_text(json.dumps(to_dict(error)))


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
    session = GameSession(websocket)

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

                elif isinstance(message, PlacementStepRequest):
                    try:
                        obs_response = session.step_placement(
                            message.x, message.rot, message.use_hold
                        )
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

                elif isinstance(message, AIPlayRequest):
                    logger.info(f"[WS] Received AI play request: agent={message.agent_type}, speed={message.speed}")
                    try:
                        # Create agent based on type
                        if message.agent_type.lower() == "random":
                            agent = RandomAgent()
                        elif message.agent_type.lower() == "dellacherie":
                            agent = DellacherieAgent()
                        elif message.agent_type.lower() == "smartdellacherie":
                            agent = SmartDellacherieAgent()
                        else:
                            error = ErrorResponse(
                                type="error",
                                code=ErrorCode.INVALID_MESSAGE,
                                message=f"Unknown agent type: {message.agent_type}",
                            )
                            await websocket.send_text(json.dumps(to_dict(error)))
                            continue

                        # Initialize game if not started yet (takeover mode)
                        if not session.initialized:
                            logger.info(f"[WS] Initializing game for AI play")
                            obs_response = session.reset(message.seed)
                            await websocket.send_text(json.dumps(to_dict(obs_response)))

                        # Start AI playback as background task
                        logger.info(f"[WS] Starting AI playback task...")
                        session.ai_playing = True
                        max_pieces = message.max_pieces or 1000
                        session.ai_task = asyncio.create_task(
                            session.run_ai_playback(
                                agent=agent,
                                speed=message.speed,
                                max_pieces=max_pieces,
                                seed=message.seed,
                            )
                        )
                        logger.info(f"[WS] AI playback task created: {session.ai_task}")

                    except Exception as e:
                        session.ai_playing = False
                        error = ErrorResponse(
                            type="error",
                            code=ErrorCode.INVALID_MESSAGE,
                            message=f"AI play error: {str(e)}",
                        )
                        await websocket.send_text(json.dumps(to_dict(error)))

                elif isinstance(message, AIStopRequest):
                    logger.info(f"[WS] Received AI stop request")
                    session.stop_ai()
                    logger.info(f"[WS] AI stopped, ai_playing={session.ai_playing}")
                    response = {"type": "ai_stopped"}
                    await websocket.send_text(json.dumps(response))

                elif isinstance(message, CompareStartRequest):
                    logger.info(f"[WS] Received compare start request: agent1={message.agent1}, agent2={message.agent2}")
                    try:
                        # Create agents based on types
                        if message.agent1.lower() == "random":
                            agent1 = RandomAgent()
                        elif message.agent1.lower() == "dellacherie":
                            agent1 = DellacherieAgent()
                        elif message.agent1.lower() == "smartdellacherie":
                            agent1 = SmartDellacherieAgent()
                        else:
                            error = ErrorResponse(
                                type="error",
                                code=ErrorCode.INVALID_MESSAGE,
                                message=f"Unknown agent type: {message.agent1}",
                            )
                            await websocket.send_text(json.dumps(to_dict(error)))
                            continue

                        if message.agent2.lower() == "random":
                            agent2 = RandomAgent()
                        elif message.agent2.lower() == "dellacherie":
                            agent2 = DellacherieAgent()
                        elif message.agent2.lower() == "smartdellacherie":
                            agent2 = SmartDellacherieAgent()
                        else:
                            error = ErrorResponse(
                                type="error",
                                code=ErrorCode.INVALID_MESSAGE,
                                message=f"Unknown agent type: {message.agent2}",
                            )
                            await websocket.send_text(json.dumps(to_dict(error)))
                            continue

                        # Start comparison as background task
                        logger.info(f"[WS] Starting comparison task...")
                        session.comparing = True
                        session.comparison_task = asyncio.create_task(
                            session.run_comparison(
                                agent1=agent1,
                                agent2=agent2,
                                speed=message.speed,
                                max_pieces=message.max_pieces,
                                seed=message.seed,
                            )
                        )
                        logger.info(f"[WS] Comparison task created: {session.comparison_task}")

                    except Exception as e:
                        session.comparing = False
                        error = ErrorResponse(
                            type="error",
                            code=ErrorCode.INVALID_MESSAGE,
                            message=f"Comparison error: {str(e)}",
                        )
                        await websocket.send_text(json.dumps(to_dict(error)))

                elif isinstance(message, CompareStopRequest):
                    logger.info(f"[WS] Received compare stop request")
                    session.stop_comparison()
                    logger.info(f"[WS] Comparison stopped, comparing={session.comparing}")
                    response = {"type": "compare_stopped"}
                    await websocket.send_text(json.dumps(response))

                elif isinstance(message, CompareSetSpeedRequest):
                    logger.info(f"[WS] Received compare set speed request: {message.speed}")
                    session.comparison_speed = message.speed
                    logger.info(f"[WS] Comparison speed updated to {session.comparison_speed}x")
                    # No response needed - speed change takes effect immediately

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
