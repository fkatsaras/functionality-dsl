# Weather Comparison Demo

**What it demonstrates:**
- Fetching from two different external APIs
- Combining data using `zip()` function
- Complex transformations with `map()`
- Ternary expressions in attributes
- Boolean logic for computed conditions
- LineChart component for visualization

**External API:** https://api.open-meteo.com (no auth required)

**No dummy service needed** - uses real weather API.

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Test the endpoints:
   ```bash
   curl http://localhost:8080/api/weather/compare
   curl http://localhost:8080/api/weather/stats
   ```

## What you'll see

**Table view:** Hourly comparison between Thessaloniki and London showing:
- Time
- Temperature in both cities
- Humidity in both cities
- Temperature delta
- Which city is hotter
- Whether temperature gap is significant (>= 5°C)
- Comfort index for each city

**Line chart:** Temperature trends over time for both cities

The demo uses `zip()` to combine arrays from two cities and `map()` to compute derived fields for each hour.

**Note:** Uses real hourly forecast data!
