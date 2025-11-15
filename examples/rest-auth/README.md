# REST Authentication Demo

**What it demonstrates:**
- All 3 authentication types for external Sources:
  - **Bearer token** (Authorization: Bearer <token>)
  - **Basic auth** (username/password)
  - **API key** (header or query parameter)
- Client authentication on Endpoints (protecting your API)
- Auth configuration at both Source and Endpoint level

**External API:** https://httpbin.org (various auth testing endpoints)

**No dummy service needed** - uses httpbin.org auth test endpoints.

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

3. **Test the endpoints:**

   **Public endpoint** (no auth required):
   ```bash
   curl http://localhost:8080/api/test/bearer
   ```

   **Protected with bearer token:**
   ```bash
   curl http://localhost:8080/api/test/basic \
     -H "Authorization: Bearer your-token-here"
   ```

   **Protected with API key:**
   ```bash
   curl http://localhost:8080/api/test/apikey \
     -H "X-API-Key: clientsecret123"
   ```

## What you'll learn

- **Source auth** = how your backend authenticates to external APIs
- **Endpoint auth** = how clients authenticate to your API
- The generated code handles all auth headers/parameters automatically
- Auth config is separate from business logic
