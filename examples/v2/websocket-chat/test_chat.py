#!/usr/bin/env python3
"""
Test script for WebSocket chat.
Sends test messages to the echo service to verify the flow.
"""
import asyncio
import websockets
import json

async def test_echo():
    """Send test messages to echo service."""
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        # Send a few test messages
        test_messages = [
            {"text": "Hello from test script!"},
            {"text": "Testing the echo service"},
            {"text": "UPPERCASE MESSAGE"},
        ]

        for msg in test_messages:
            print(f"Sending: {msg}")
            await websocket.send(json.dumps(msg))

            # Wait for echo response
            response = await websocket.recv()
            print(f"Received: {response}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    print("Testing WebSocket echo service...")
    asyncio.run(test_echo())
