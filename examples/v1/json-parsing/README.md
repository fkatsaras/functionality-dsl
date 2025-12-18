# JSON Parsing Demo

**What it demonstrates:**
- Nested JSON object handling
- Safe access to nested fields with `get(get(...))`
- Optional nested entity references (`object<EntityName>?`)
- Handling missing/null data gracefully

**External API:** https://api.restful-api.dev/objects (no auth required)

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
   curl http://localhost:8080/api/objects
   ```

## What you'll see

A table showing objects with nested data fields:
- ID
- Name
- Color (from nested `data.color`)
- Capacity (from nested `data.capacity`)
- Price (from nested `data.price`)
- Year (from nested `data.year`)

The demo uses `get(get(x, "data", {}), "color", "")` for safe nested access - if any level is missing, it returns the default value instead of crashing.
