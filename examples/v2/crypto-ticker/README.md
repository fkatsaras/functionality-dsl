# Cryptocurrency Price Ticker (NEW SYNTAX)

**What it demonstrates:**
- Entity-centric WebSocket exposure (NEW!)
- Real-time WebSocket feed from Binance
- LiveChart component binding to entities (not endpoints)
- Using `now()` built-in function for timestamps
- Streaming financial data with entity transformations

**External API:** wss://stream.binance.com:9443 (public Binance WebSocket)

**No dummy service needed** - uses real Binance crypto price feed.

## Key Differences from Old Syntax

### Old Syntax (v1):
```fdsl
Endpoint<WS> PricesStream
  channel: "/api/prices"
  subscribe:
    type: object
    entity: Prices
end

Component<LiveChart> BitcoinPrice
  endpoint: PricesStream
  ...
end
```

### New Syntax (v2):
```fdsl
Entity Prices(BTCRaw)
  attributes:
    - t: string = formatDate(now(), "YYYY-MM-DD HH:mm:ss");
    - btc: number = BTCRaw.c;
  expose:
    websocket: "/api/prices"
end

Component<LiveChart> BitcoinPrice
  entity: Prices
  ...
end
```

**Benefits:**
- Entity owns its exposure configuration
- Direct entity-to-component binding
- Clearer data flow: `Binance WS → BTCRaw → Prices (transformed) → WebSocket → LiveChart`

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Access the UI:
   Open http://localhost:5173 to see live Bitcoin price chart

3. Test with WebSocket client:
   ```bash
   websocat ws://localhost:8080/api/prices
   ```

## What you'll see

A live chart showing Bitcoin (BTC) price in USDT updating in real-time.

The demo:
- Receives price ticks from Binance WebSocket
- Adds timestamp using `now()` function
- Streams transformed data via entity's WebSocket channel
- Updates LiveChart component continuously as price changes

**Note:** This is real market data from Binance!

## Architecture

```
External Source (Binance WS)
        ↓
    BTCRaw (raw price)
        ↓
    Prices (+ timestamp)
        ↓
  WebSocket Channel (/api/prices)
        ↓
   LiveChart Component
```
