# Live Wikipedia Edits Monitor

**Real-time streaming of Wikipedia edits** using external WebSocket feed from WikiMon.

**Demonstrates:**
- WebSocket subscribe from real external service
- Entity composition for data transformation
- Gauge component with computed values
- LiveView component for streaming data table

**Requires dummy service:** No - Uses real WikiMon WebSocket API

## Architecture

### Data Flow

**WebSocket Subscribe (Wikipedia Edits):**
```
External WikiMon WS -> WikiEdit (source:) -> EditGauge/WikiEditStream (expose:) -> Client
```

### Key v2 Syntax Features

1. **Source Binding**: `source: WikiMonEN` on WikiEdit entity
2. **Entity Composition**: EditGauge and WikiEditStream inherit from WikiEdit
3. **Computed Attributes**: `edit_size_abs = abs(WikiEdit.change_size)`
4. **WebSocket Exposure**: `expose: websocket: "/api/wiki/edits"`
5. **Direct Entity Binding**: Components bind to entities, not endpoints

## Entities

### WikiEdit (Raw)
Raw Wikipedia edit event from external WebSocket source.

**Fields:**
- `action`: Type of edit (edit, new, etc.)
- `change_size`: Number of bytes changed (can be negative)
- `page_title`: Title of the Wikipedia page edited
- `user`: Username of the editor
- `server_name`: Wikipedia server name

### EditGauge (Computed)
Exposes absolute value of edit size for gauge display.

**Computed:**
- `edit_size_abs`: Absolute value of `change_size`

### WikiEditStream (Filtered)
Filtered view of WikiEdit for the live feed table.

## Components

### LiveEditSize (Gauge)
Real-time gauge showing the absolute size of the most recent Wikipedia edit.

### WikiEditsFeed (LiveView)
Scrolling table of recent Wikipedia edits showing user, page, and action.

## Running

```bash
# Generate code
fdsl generate main.fdsl --out generated

# Start the server
cd generated
docker compose -p thesis up
```

Open http://localhost:3000 to see live Wikipedia edits streaming in real-time!

## Notes

- This example connects to the real WikiMon WebSocket API
- No dummy service required
- The feed shows edits happening in real-time on English Wikipedia
- Edit sizes can be positive (additions) or negative (deletions)
