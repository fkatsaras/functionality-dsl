# WebSocket Authentication Demo

**What it demonstrates:**
- WebSocket authentication with bearer tokens
- Source auth (backend → external WS)
- Endpoint auth (client → backend WS)
- Public vs protected WebSocket endpoints
- Auth configuration for both Source and Endpoint

**Requires dummy service:** Yes - authenticated WebSocket echo server

## How to run

1. **Start the dummy WebSocket service:**
   ```bash
   bash run.sh
   ```
   Starts authenticated WS echo server on port 8765

2. **Generate and run:**
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

3. **Test public endpoint (no auth):**
   ```bash
   websocat ws://localhost:8080/api/ws/echo/public
   ```

4. **Test protected endpoint (requires auth):**
   ```bash
   websocat ws://localhost:8080/api/ws/echo/protected \
     -H="Authorization: Bearer your-token-here"
   ```

## What you'll learn

- **Source auth**: Backend authenticates to external WS with `token: "secret123"`
- **Endpoint auth**: Clients must provide bearer token to access protected endpoints
- Same external source, different client-facing security policies
