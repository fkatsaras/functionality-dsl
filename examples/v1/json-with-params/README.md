# JSON with Path Parameters Demo

**What it demonstrates:**
- Path parameter handling (`/api/objects/{objectId}`)
- Parameter flow: Endpoint → Source
- Both list and detail views from same API
- ObjectView component for parameterized endpoints
- Table component for parameter-free endpoints

**External API:** https://api.restful-api.dev/objects (no auth required)

**No dummy service needed** - uses real public API.

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Test the endpoints:

   **List all objects:**
   ```bash
   curl http://localhost:8080/api/objects
   ```

   **Get specific object:**
   ```bash
   curl http://localhost:8080/api/objects/7
   ```

## What you'll learn

- **Parameter mapping**: `objectId: string = RealObjectDetails.objectId;`
- **Two component patterns**:
  - Table → List endpoint (no params)
  - ObjectView → Detail endpoint (with params)
- Same external API, different use cases
