import asyncio
import websockets
import json

async def echo(ws):
    """Simple echo server - accepts all connections without auth."""
    try:
        async for message in ws:
            print("[ECHO]", message)
            try:
                payload = json.loads(message)
                await ws.send(json.dumps(payload))
            except Exception:
                await ws.send(message)
    except Exception as ex:
        print("[CONN] Closed:", ex)

async def main():
    async with websockets.serve(echo, "0.0.0.0", 8765):
        print("------ WS server running on ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
