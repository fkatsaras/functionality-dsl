# Integer Comparison Demo

**What it demonstrates:**
- Fetching from two independent external APIs
- Combining data from multiple sources
- Comparison operators: `==`, `>`, `<`
- Arithmetic operations
- Boolean expressions in entities

**External APIs:** https://www.randomnumberapi.com (no auth required)

**No dummy service needed** - uses real random number API.

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Test the endpoint:
   ```bash
   curl http://localhost:8080/api/compare
   ```

Each request fetches two random numbers and compares them in a table with columns:
- `a_val` - First random number
- `b_val` - Second random number
- `delta` - Difference (a - b)
- `is_equal` - Whether they're equal
- `a_greater` - Whether a > b
- `b_greater` - Whether b > a

Demonstrates combining multiple sources and computing derived values.
