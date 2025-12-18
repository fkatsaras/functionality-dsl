# WebSocket Duplex Chat Demo

**What it demonstrates:**
- Bidirectional WebSocket communication
- External WebSocket source integration
- Inbound and outbound transformation chains
- Primitive value wrapping (string → entity)
- Text transformation (`upper()`, `lower()`)
- WebSocket message routing

**Requires dummy service:** Yes - Python WebSocket echo server

## How to run

1. **Start the dummy WebSocket echo service:**
   ```bash
   bash run.sh
   ```
   This starts a WebSocket server on port 8765 that echoes back what you send.

2. **In a new terminal, generate the backend code:**
   ```bash
   fdsl generate main.fdsl --out generated
   ```

3. **Run the generated application:**
   ```bash
   cd generated
   docker compose -p thesis up
   ```

4. **Test with a WebSocket client:**

   You can use `websocat` or any WS client:
   ```bash
   # Install websocat if needed: cargo install websocat
   websocat ws://localhost:8080/api/chat
   ```

   Type a message like "hello" and you'll see it transformed:
   - Your input: `"hello"`
   - Sent to external (uppercase): `{"text": "HELLO"}`
   - External echoes back: `{"text": "HELLO"}`
   - You receive (lowercase): `{"text": "hello"}`

## What you'll learn

- **Outbound chain**: `OutgoingWrapper` → `OutgoingProcessed` → External WS
- **Inbound chain**: External WS → `EchoWrapper` → `EchoProcessed` → Client
- How primitive string values get wrapped automatically
- WebSocket bidirectional message flow in FDSL
