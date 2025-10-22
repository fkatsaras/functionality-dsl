import asyncio
import websockets
import base64
import json

BASIC_USER = "user"
BASIC_PASS = "pass"
BEARER_TOKEN = "secret123"

async def process_request(connection, request):
    # In websockets >= 10.0, we receive connection and request objects
    # Access headers via request.headers
    auth_header = request.headers.get("Authorization")
    
    expected_basic = "Basic " + base64.b64encode(f"{BASIC_USER}:{BASIC_PASS}".encode()).decode()
    
    if auth_header == expected_basic:
        print("[AUTH] Basic OK")
        return None  # continue handshake
    elif auth_header == f"Bearer {BEARER_TOKEN}":
        print("[AUTH] Bearer OK")
        return None
    else:
        print("[AUTH] Failed:", auth_header)
        # Return proper response tuple
        return (401, [("Content-Type", "text/plain")], b"Unauthorized")

async def echo(ws):
    try:
        async for message in ws:
            print("[ECHO]", message)
            try:
                payload = json.loads(message)
                await ws.send(json.dumps({"echo": payload}))
            except Exception:
                await ws.send(message)
    except Exception as ex:
        print("[CONN] Closed:", ex)

async def main():
    async with websockets.serve(
        echo, "localhost", 8765, process_request=process_request
    ):
        print("------ WS server running on ws://localhost:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
