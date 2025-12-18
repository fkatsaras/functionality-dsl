# Live Wikipedia Edits Stream

**What it demonstrates:**
- Real-time WebSocket feed from external source
- Publishing (server → clients) only (no subscribe)
- Gauge component for live metrics
- LiveView component for streaming data
- Working with real-world WebSocket APIs

**External API:** wss://wikimon.hatnote.com/en/ (public Wikipedia edit stream)

**No dummy service needed** - uses real Wikipedia edit feed.

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Access the UI:
   Open http://localhost:3000 to see live Wikipedia edits streaming

3. Test with WebSocket client:
   ```bash
   websocat ws://localhost:8080/api/wiki/edits/feed
   ```

## What you'll see

Real-time Wikipedia edits showing:
- User who made the edit
- Page title being edited
- Action type (edit, new, etc.)
- Edit size (bytes changed)

The Gauge component shows the edit size with updates in real-time as edits happen across Wikipedia.

**Note:** This is a true live feed - you're seeing actual edits happening on Wikipedia right now!
