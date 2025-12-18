# REST Mutations Demo

**What it demonstrates:**
- POST endpoint with request body
- Entity chaining (multiple transformation layers)
- Data normalization with `lower()` function
- Mutation workflows (client → server → external API)

**External API:** https://httpbin.org/anything (echo service, no auth required)

**No dummy service needed** - uses httpbin.org echo service.

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
   curl -X POST http://localhost:8080/api/users \
     -H "Content-Type: application/json" \
     -d '{"id": 1, "name": "John", "job": "Developer"}'
   ```

4. **Access the UI:**
   Open http://localhost:3000 - you'll see an ActionForm component

## What you'll see

The demo shows multiple layers of entity transformation:
- `User` (request schema)
- `UserNormalized1` → normalizes name and job to lowercase
- `UserNormalized2` → combines with parent
- `UserNormalized3` → final transformation

This demonstrates how FDSL handles complex data transformation chains for mutations.
