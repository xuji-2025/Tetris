"""Simple WebSocket test client for manual testing.

Usage:
    uv run python tests/test_client.py
"""

import asyncio
import json
import os

import pytest
import websockets


RUN_WS_TESTS = os.getenv("RUN_WS_TESTS") == "1"


@pytest.mark.asyncio
async def test_game_session():
    """Test a complete game session."""
    if not RUN_WS_TESTS:
        pytest.skip("WebSocket integration test requires RUN_WS_TESTS=1 and backend server.")

    uri = "ws://localhost:8000/ws"

    print("Connecting to WebSocket server...")
    async with websockets.connect(uri) as websocket:
        print("✓ Connected!")

        # 1. Send hello
        print("\n1. Sending hello...")
        hello = {"type": "hello", "version": "s1.0.0"}
        await websocket.send(json.dumps(hello))
        response = await websocket.recv()
        data = json.loads(response)
        print(f"   Server: {data}")

        # 2. Reset game
        print("\n2. Resetting game with seed 42...")
        reset = {"type": "reset", "seed": 42}
        await websocket.send(json.dumps(reset))
        response = await websocket.recv()
        data = json.loads(response)
        print(f"   Game reset. Current piece: {data['data']['current']['type']}")
        print(f"   Next queue: {data['data']['next_queue']}")
        print(f"   Legal moves: {len(data['data']['legal_moves'])} positions")

        # 3. Take some actions
        print("\n3. Playing some moves...")
        actions = ["RIGHT", "RIGHT", "CW", "SOFT", "SOFT", "SOFT", "HARD"]

        for action in actions:
            step = {"type": "step", "action": action}
            await websocket.send(json.dumps(step))
            response = await websocket.recv()
            data = json.loads(response)

            events = data["info"].get("events", [])
            print(f"   {action:5} → events: {events}, score: {data['data']['episode']['score']}")

            if data["done"]:
                print("   Game over!")
                break

        # 4. Test invalid action
        print("\n4. Testing invalid action...")
        invalid = {"type": "step", "action": "INVALID"}
        await websocket.send(json.dumps(invalid))
        response = await websocket.recv()
        data = json.loads(response)
        if data.get("type") == "error":
            print(f"   ✓ Got expected error: {data['message']}")

        # 5. Reset again
        print("\n5. Resetting with new seed...")
        reset = {"type": "reset", "seed": 999}
        await websocket.send(json.dumps(reset))
        response = await websocket.recv()
        data = json.loads(response)
        print(f"   New game. Current piece: {data['data']['current']['type']}")

        print("\n✓ All tests passed!")


@pytest.mark.asyncio
async def test_multiple_games():
    """Test playing multiple short games."""
    if not RUN_WS_TESTS:
        pytest.skip("WebSocket integration test requires RUN_WS_TESTS=1 and backend server.")

    uri = "ws://localhost:8000/ws"

    print("Testing multiple games...")
    async with websockets.connect(uri) as websocket:
        # Hello
        await websocket.send(json.dumps({"type": "hello", "version": "s1.0.0"}))
        await websocket.recv()

        for seed in [100, 200, 300]:
            print(f"\n--- Game with seed {seed} ---")

            # Reset
            await websocket.send(json.dumps({"type": "reset", "seed": seed}))
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Started. Piece: {data['data']['current']['type']}")

            # Play a few moves
            for _ in range(5):
                await websocket.send(json.dumps({"type": "step", "action": "SOFT"}))
                await websocket.recv()

            # Hard drop
            await websocket.send(json.dumps({"type": "step", "action": "HARD"}))
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Finished. Score: {data['data']['episode']['score']}")

    print("\n✓ Multiple games test passed!")


async def interactive_mode():
    """Interactive mode - control game via keyboard."""
    uri = "ws://localhost:8000/ws"

    print("Interactive mode - control Tetris via keyboard")
    print("Commands: left, right, cw, ccw, soft, hard, hold, reset, quit")
    print()

    async with websockets.connect(uri) as websocket:
        # Hello
        await websocket.send(json.dumps({"type": "hello", "version": "s1.0.0"}))
        await websocket.recv()

        # Reset
        await websocket.send(json.dumps({"type": "reset", "seed": 42}))
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Game started! Piece: {data['data']['current']['type']}\n")

        while True:
            cmd = input("> ").strip().lower()

            if cmd == "quit":
                break
            elif cmd == "reset":
                await websocket.send(json.dumps({"type": "reset"}))
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Reset! Piece: {data['data']['current']['type']}")
            elif cmd in ["left", "right", "cw", "ccw", "soft", "hard", "hold"]:
                action = cmd.upper()
                await websocket.send(json.dumps({"type": "step", "action": action}))
                response = await websocket.recv()
                data = json.loads(response)

                obs = data["data"]
                print(f"Piece: {obs['current']['type']} at ({obs['current']['x']}, {obs['current']['y']}) rot={obs['current']['rot']}")
                print(f"Score: {obs['episode']['score']}, Lines: {obs['episode']['lines_total']}")
                print(f"Events: {data['info'].get('events', [])}")

                if data["done"]:
                    print("GAME OVER!")
            else:
                print("Unknown command")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "test"

    if mode == "interactive":
        asyncio.run(interactive_mode())
    elif mode == "multiple":
        asyncio.run(test_multiple_games())
    else:
        asyncio.run(test_game_session())
