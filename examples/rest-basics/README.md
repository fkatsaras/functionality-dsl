# REST Basics Demo

**What it demonstrates:**
- Fetching data from an external REST API
- Array response handling with wrapper entities
- Data transformation using `map()` and expressions
- Table component binding
- Safe nested object access with `get()`

**External API:** https://api.sampleapis.com/coffee/hot (no auth required)

**No dummy service needed** - uses a real public API.

## How to run

1. **Generate the backend code:**
   ```bash
   fdsl generate main.fdsl --out generated
   ```

2. **Run the generated application:**
   ```bash
   cd generated
   docker compose -p thesis up
   ```

3. **Test the endpoint:**
   ```bash
   curl http://localhost:8080/api/coffee/stats
   ```

4. **Access the UI:**
   Open http://localhost:3000 in your browser

## What you'll see

A table showing coffee drinks with:
- Image
- ID
- Name
- Title length (computed)
- Description

The data is fetched from the external API and transformed to add computed fields and handle missing images.
