# Large JSON Response Test

Tests FDSL handling of substantial JSON payloads with complex nested structures and data transformations.

## What This Tests

This example validates FDSL's ability to handle:

1. **Large Arrays**: Up to 10,000 user records in a single response
2. **Nested Objects**: Multi-level organizational hierarchies with departments and employees
3. **Complex Transformations**: Aggregations, filtering, sorting, and statistical computations
4. **Memory Efficiency**: Processing substantial data payloads without performance degradation
5. **Expression Evaluation**: Complex FDSL expressions over large datasets

## Endpoints

### GET `/api/users?count=N&include_metadata=true|false`
Fetches N user records (default: 1000, max: 10000) and computes:
- Total and active user counts
- Average age and salary
- Country distribution and top 5 countries
- Transformed user list with computed fields

**Test Cases:**
- Small: `count=100` (~15KB response)
- Medium: `count=1000` (~150KB response)
- Large: `count=5000` (~750KB response)
- Maximum: `count=10000` (~1.5MB response)
- With metadata: `include_metadata=true` (adds ~50% more data)

### GET `/api/analytics?days=N`
Generates analytics with daily metrics for N days (default: 30, max: 365) including:
- Daily page views, visitors, bounce rates
- Top 50 products with sales data
- Average metrics across the period
- Best/worst performing days

**Test Cases:**
- Weekly: `days=7` (~50KB response)
- Monthly: `days=30` (~200KB response)
- Quarterly: `days=90` (~600KB response)
- Yearly: `days=365` (~2.5MB response)

### GET `/api/organization`
Returns a nested organizational structure with:
- 10 main departments
- 2-4 sub-departments per department (when present)
- 5-20 employees per department
- Employee projects and salary data
- Computed summaries: budget totals, average salaries, top earners

**Response Size:** ~500KB-1MB (varies due to randomization)

### GET `/health`
Simple health check endpoint (minimal response).

## File Structure

```
large-json-test/
├── main.fdsl                  # FDSL specification
├── README.md                  # This file
├── run.sh                     # Test execution script
└── dummy-service/             # Mock data generator
    ├── app.py                 # FastAPI service
    ├── requirements.txt
    ├── Dockerfile
    └── docker-compose.yml
```

## Running the Test

### 1. Generate the FDSL code
```bash
cd examples/large-json-test
../../venv_WIN/Scripts/fdsl.exe generate main.fdsl --out generated
```

### 2. Start the generated application
```bash
cd generated
docker compose -p thesis up --build
```

Wait for the app to start (look for "Application startup complete").

### 3. Start the dummy data service (in a new terminal)
```bash
cd examples/large-json-test/dummy-service
docker compose up --build
```

### 4. Run tests (in a new terminal)
```bash
cd examples/large-json-test
bash run.sh
```

Or test manually:
```bash
# Small dataset
curl "http://localhost:8080/api/users?count=100"

# Medium dataset
curl "http://localhost:8080/api/users?count=1000"

# Large dataset with metadata
curl "http://localhost:8080/api/users?count=5000&include_metadata=true"

# Analytics - 90 days
curl "http://localhost:8080/api/analytics?days=90"

# Organization structure
curl "http://localhost:8080/api/organization"
```

### 5. Performance testing
```bash
# Measure response time for 10K users
time curl "http://localhost:8080/api/users?count=10000" -o /dev/null

# Measure response size
curl "http://localhost:8080/api/users?count=10000" | wc -c
```

## What to Look For

### Success Indicators
- ✅ All endpoints return valid JSON
- ✅ Computed fields are correct (totals, averages, sorted lists)
- ✅ No memory errors or timeouts
- ✅ Response times are reasonable (< 5 seconds for 10K records)
- ✅ Nested transformations work correctly
- ✅ Error handling validates parameter ranges

### Key FDSL Features Tested
- **Array operations**: `map`, `filter`, `fold`, `sort_by`
- **Aggregations**: `sum`, `len`, `keys`
- **Math operations**: `round`, arithmetic
- **Conditional logic**: `if-else` expressions
- **Nested access**: Object and array indexing
- **Parameter mapping**: Query params flow to sources
- **Error conditions**: Validation on count/days parameters

## Expected Response Sizes

| Endpoint | Configuration | Approximate Size |
|----------|--------------|------------------|
| `/api/users` | count=100 | ~15 KB |
| `/api/users` | count=1000 | ~150 KB |
| `/api/users` | count=5000 | ~750 KB |
| `/api/users` | count=10000 | ~1.5 MB |
| `/api/users` | count=1000, metadata=true | ~225 KB |
| `/api/analytics` | days=30 | ~200 KB |
| `/api/analytics` | days=365 | ~2.5 MB |
| `/api/organization` | (fixed) | ~500 KB - 1 MB |

## Cleanup

```bash
# Stop and remove containers
cd generated && docker compose -p thesis down
cd ../dummy-service && docker compose down

# Remove generated code
cd .. && rm -rf generated

# Or use the global cleanup script
cd ../.. && bash scripts/cleanup.sh
```

## Notes

- The dummy service generates **random data** on each request, so response content varies
- Response sizes are approximate and depend on randomization
- The organizational structure depth is limited to 2 levels to keep responses manageable
- All computations happen in-memory during entity evaluation
- Performance depends on system resources and Docker configuration
