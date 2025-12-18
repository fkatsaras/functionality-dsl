# Cryptocurrency Price Ticker

**What it demonstrates:**
- Real-time WebSocket feed from Binance
- LiveChart component for time-series data
- Using `now()` built-in function for timestamps
- Streaming financial data

**External API:** wss://stream.binance.com:9443 (public Binance WebSocket)

**No dummy service needed** - uses real Binance crypto price feed.

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Access the UI:
   Open http://localhost:3000 to see live Bitcoin price chart

3. Test with WebSocket client:
   ```bash
   websocat ws://localhost:8080/api/prices
   ```

## What you'll see

A live chart showing Bitcoin (BTC) price in USDT updating in real-time.

The demo:
- Receives price ticks from Binance WebSocket
- Adds timestamp using `now()` function
- Streams to LiveChart component
- Updates continuously as price changes

**Note:** This is real market data from Binance!
