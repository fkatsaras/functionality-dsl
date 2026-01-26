# FDSL vs Python/FastAPI Comparison

| Metric | FDSL | Python/FastAPI |
|--------|------|----------------|
| **Total Lines** | 191 | 271 |
| **Models/Schemas** | 0 (auto-generated) | 95 lines |
| **HTTP Clients** | 0 (auto-generated) | 30 lines |
| **Transform Logic** | 35 lines (expressions) | 75 lines |
| **API Routes** | 0 (auto-generated) | 55 lines |
| **UI Components** | 48 lines | N/A |
| **Files** | 1 | 1+ |

## Code Breakdown

### FDSL (191 lines)
- Server config: 6 lines
- Sources: 12 lines
- Base entities: 30 lines
- Computed entities: 55 lines
- Multi-source composites: 22 lines
- UI components: 48 lines
- Comments/whitespace: 18 lines

### Python/FastAPI (271 lines)
- Imports & setup: 16 lines
- Pydantic models: 95 lines
- HTTP clients: 30 lines
- Transform functions: 75 lines
- API endpoints: 55 lines

## Key Differences

| Aspect | FDSL | Python |
|--------|------|--------|
| Schema definition | Inline with entity | Separate Pydantic classes |
| Nested access | `obj["field"]` | `obj.field` (typed) |
| Transforms | `= expression` | Function body |
| Multi-source | `Entity(A, B)` | Manual orchestration |
| Conditionals | `x if cond else y` | `if/elif/else` blocks |
| Array ops | `map(arr, x => ...)` | List comprehension |

## Equivalent Functionality

Both implementations provide:
- 3 base entities (RawProduct, RawCart, RawUser)
- 3 computed entities (Product, Cart, User)
- 2 multi-source composites (Dashboard, Analytics)
- 8 REST endpoints total

FDSL additionally generates:
- 5 UI components (2 BarCharts, 1 PieChart, 2 Gauges)
- OpenAPI documentation
- Svelte frontend code
