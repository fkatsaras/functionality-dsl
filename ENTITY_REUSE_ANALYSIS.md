# Entity Reuse Problem: Analysis and Solution

## Problem Summary

The flow analyzer incorrectly classifies `GetDelivery` (GET endpoint) as `READ_WRITE` because it finds write targets (CreateDeliveryDB, UpdateStatusDB, AssignDriverDB) in its dependency chain. This happens because all four sources return the same entity `DeliveryRaw`:

```fdsl
Source<REST> DeliveryByIdDB
  method: GET
  response: entity: DeliveryRaw  // ← READ operation

Source<REST> CreateDeliveryDB
  method: POST
  response: entity: DeliveryRaw  // ← WRITE operation response

Source<REST> UpdateStatusDB
  method: PUT
  response: entity: DeliveryRaw  // ← WRITE operation response

Source<REST> AssignDriverDB
  method: PUT
  response: entity: DeliveryRaw  // ← WRITE operation response
```

When analyzing `GetDelivery`'s response chain `DeliveryWithETA → DeliveryWithDistance → DeliveryRaw`, the dependency graph returns ALL sources that provide `DeliveryRaw`, including the mutation responses.

## Root Cause

### Current Behavior (dependency_graph.py:129-133)

```python
# Response: Source provides entity as response
# All methods can return response entities (GET for reads, POST/DELETE for write results)
response_schema = get_response_schema(source)
if response_schema and response_schema.get("type") == "entity":
    entity = response_schema["entity"]
    self.graph.add_edge(
        source_node,
        entity.name,
        type="provides"  # ← Same edge type for ALL methods!
    )
```

**The problem**: The dependency graph uses a single edge type `"provides"` for all response entities, regardless of whether the source is a READ (GET) or WRITE (POST/PUT/PATCH/DELETE) operation.

### Flow Analyzer Behavior (flow_analyzer.py:496-502)

```python
# Section 6: Merge response write targets
if request_entity is None and http_method not in {"GET", "HEAD", "OPTIONS"}:
    for src in response_write_targets:
        if not any(t.name == src.name for t in write_targets):
            write_targets.append(src)
```

Even though this check should prevent adding write targets to GET endpoints, the **sources are already collected in `response_write_targets`** because they're part of the response entity's dependency chain.

## Comparison with User-Management Example

### User-Management Pattern (WORKS)

```fdsl
Source<REST> CreateUser
  method: POST
  response: entity: UserSchema  // ← Returns UserSchema

Source<REST> UpdateUser
  method: PATCH
  response: entity: UserSchema  // ← Returns UserSchema

Source<REST> UpdateUserPassword
  method: PATCH
  response: entity: UserSchema  // ← Returns UserSchema
```

**Why it works**: All sources that return `UserSchema` are **mutation operations** (POST/PATCH). There's no GET endpoint that also returns `UserSchema`, so there's no ambiguity when analyzing response chains.

### Delivery-Tracking Pattern (BROKEN)

```fdsl
Source<REST> DeliveryByIdDB      // GET  → DeliveryRaw
Source<REST> CreateDeliveryDB    // POST → DeliveryRaw
Source<REST> UpdateStatusDB      // PUT  → DeliveryRaw
Source<REST> AssignDriverDB      // PUT  → DeliveryRaw
```

**Why it breaks**: The same entity `DeliveryRaw` is returned by both READ (GET) and WRITE (POST/PUT) operations, causing flow classification ambiguity.

## Solution Options

### Option 1: Separate Response Entities (Immediate Fix)

**Create distinct entities for mutation responses:**

```fdsl
// Read operation
Entity DeliveryRaw
  attributes:
    - id: string;
    - orderId: string;
    # ... (all fields)
end

Source<REST> DeliveryByIdDB
  method: GET
  response: entity: DeliveryRaw
end

// Write operation responses
Entity DeliveryCreated
  attributes:
    - id: string;
    - orderId: string;
    # ... (same fields as DeliveryRaw)
end

Entity DeliveryUpdated
  attributes:
    - id: string;
    - orderId: string;
    # ... (same fields as DeliveryRaw)
end

Source<REST> CreateDeliveryDB
  method: POST
  response: entity: DeliveryCreated
end

Source<REST> UpdateStatusDB
  method: PUT
  response: entity: DeliveryUpdated
end
```

**Then merge them in transformation entities:**

```fdsl
Entity DeliveryWithDistance(DeliveryRaw, DeliveryCreated, DeliveryUpdated)
  attributes:
    - id: string = get(DeliveryRaw, "id", "") or get(DeliveryCreated, "id", "") or get(DeliveryUpdated, "id", "");
    # ... (access any parent)
end
```

**Pros:**
- Immediate fix, works with current codebase
- Follows user-management pattern
- Makes data flow explicit and unambiguous

**Cons:**
- Verbose and repetitive
- Requires duplicating schema definitions
- Awkward multi-parent inheritance with conditional logic

### Option 2: Distinguish Edge Types by HTTP Method (Better)

**Modify dependency_graph.py to create different edge types:**

```python
# Response: Source provides entity as response
response_schema = get_response_schema(source)
if response_schema and response_schema.get("type") == "entity":
    entity = response_schema["entity"]
    method = getattr(source, "method", "GET").upper()

    # Different edge types for READ vs WRITE response
    if method in {"GET", "HEAD", "OPTIONS"}:
        edge_type = "provides"  # READ: source provides data
    else:
        edge_type = "mutation_response"  # WRITE: source returns mutation result

    self.graph.add_edge(
        source_node,
        entity.name,
        type=edge_type
    )
```

**Update get_source_dependencies to filter by edge type:**

```python
def get_source_dependencies(self, entity_name: str, endpoint: str = None) -> Dict[str, List]:
    # ...
    for predecessor in graph.predecessors(node):
        if graph.nodes[predecessor].get("type") == "source":
            edge_data = graph.get_edge_data(predecessor, node)
            edge_type = edge_data.get("type") if edge_data else None

            # Only include "provides" edges (READ operations)
            if edge_type == "provides":
                # ... collect source
```

**Update flow_analyzer to properly separate reads and writes:**

```python
# Get sources that PROVIDE data (READ)
response_sources = []
for ent_name in response_chain:
    deps = dep_graph.get_source_dependencies(ent_name, endpoint)
    for src in deps["read_sources"]:
        if src.method.upper() in {"GET", "HEAD", "OPTIONS"}:
            response_sources.append(src)

# Get sources that CONSUME data (WRITE) - only for mutation responses
response_write_targets = []
for ent_name in response_chain:
    deps = dep_graph.get_source_dependencies(ent_name, endpoint)
    for src in deps["read_sources"]:
        if src.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            response_write_targets.append(src)
```

**Pros:**
- Allows entity reuse across READ and WRITE operations
- More natural and less verbose
- Semantically correct: distinguishes data sources from mutation results
- Aligns with REST semantics

**Cons:**
- Requires changes to dependency graph and flow analyzer
- Need to ensure all edge type checks are updated

### Option 3: Add Semantic Validation Rule (Conservative)

**Prohibit reusing response entities across READ and WRITE sources:**

Add validation in `functionality_dsl/validation/semantic_validator.py`:

```python
def validate_entity_response_usage(self):
    """
    Validate that response entities are not reused across READ and WRITE sources.

    This prevents flow classification ambiguity where GET endpoints incorrectly
    inherit write targets from mutation operations that return the same entity.
    """
    from textx import get_children_of_type
    from collections import defaultdict

    # Map entity -> list of (source, method)
    entity_usage = defaultdict(list)

    for source in get_children_of_type("SourceREST", self.model):
        response_schema = get_response_schema(source)
        if response_schema and response_schema.get("type") == "entity":
            entity = response_schema["entity"]
            method = getattr(source, "method", "GET").upper()
            entity_usage[entity.name].append((source.name, method))

    # Check for mixed usage
    for entity_name, usages in entity_usage.items():
        read_sources = [s for s, m in usages if m in {"GET", "HEAD", "OPTIONS"}]
        write_sources = [s for s, m in usages if m in {"POST", "PUT", "PATCH", "DELETE"}]

        if read_sources and write_sources:
            self.errors.append(
                f"Entity '{entity_name}' is used as response entity in both "
                f"READ sources {read_sources} and WRITE sources {write_sources}. "
                f"This creates flow classification ambiguity. "
                f"Use separate entities for READ and WRITE operation responses."
            )
```

**Pros:**
- Prevents the problem at validation time
- Clear error message guides users
- Enforces best practice

**Cons:**
- Prohibits entity reuse (forces Option 1 pattern)
- Less flexible
- May be overly restrictive for some valid use cases

## Recommendation

**Implement Option 2** (Distinguish Edge Types by HTTP Method) as the primary solution, with **Option 3** (Semantic Validation) as an optional safety check.

**Rationale:**
1. **Option 2 is semantically correct**: READ and WRITE operations are fundamentally different, and the dependency graph should reflect this
2. **Allows natural entity reuse**: Users can define `DeliveryRaw` once and use it everywhere
3. **Aligns with REST semantics**: GET provides data, POST/PUT/PATCH return mutation results
4. **Makes flow analysis clearer**: Explicit distinction between data sources and mutation responses
5. **Option 3 adds safety**: Can be enabled as a linting rule to warn users about potential ambiguity

### Implementation Plan

1. **Update dependency_graph.py** (lines 121-133):
   - Add edge type distinction: `"provides"` vs `"mutation_response"`
   - Filter by method when creating edges

2. **Update get_source_dependencies** (lines 632-672):
   - Only collect sources with `"provides"` edges
   - Ignore `"mutation_response"` edges for read operations

3. **Update flow_analyzer.py** (lines 200-250):
   - Separate response_sources (provides) from response_write_targets (mutation_response)
   - Remove section 6 merge logic (lines 496-502) - no longer needed

4. **Add semantic validation** (optional):
   - Warn when entity is reused across READ and WRITE
   - Make it a warning, not an error, since Option 2 handles it correctly

5. **Update tests**:
   - Add test for entity reuse across READ/WRITE
   - Verify GET endpoints don't get write targets
   - Verify POST endpoints still get correct write targets

6. **Update documentation**:
   - Document that entity reuse is supported
   - Explain the semantic difference between data sources and mutation responses
   - Update CLAUDE.md with best practices

## Test Cases to Add

```fdsl
// Test 1: Entity reused across GET and POST (should work with Option 2)
Entity Product
  attributes:
    - id: string;
    - name: string;
end

Source<REST> GetProduct
  method: GET
  response: entity: Product
end

Source<REST> CreateProduct
  method: POST
  response: entity: Product
end

Endpoint<REST> GetProductEndpoint
  method: GET
  response: entity: Product
end

Endpoint<REST> CreateProductEndpoint
  method: POST
  response: entity: Product
end

// Expected: GetProductEndpoint is READ, CreateProductEndpoint is WRITE
// GetProductEndpoint should NOT have CreateProduct in write_targets

// Test 2: Multiple mutations returning same entity (should work)
Source<REST> UpdateProduct
  method: PUT
  response: entity: Product
end

Source<REST> PatchProduct
  method: PATCH
  response: entity: Product
end

// Expected: All mutations share entity, no ambiguity since all are writes
```

## Backward Compatibility

Option 2 is **backward compatible**:
- Existing FDSL files continue to work
- User-management example already follows this pattern (no READ/WRITE mixing)
- Delivery-tracking example will work once regenerated

Option 3 (validation) would **break backward compatibility** if made an error, but is fine as a warning.

## Next Steps

1. Implement Option 2 changes in dependency_graph.py
2. Update flow_analyzer.py to use new edge types
3. Test with delivery-tracking example
4. Add comprehensive test cases
5. Consider adding Option 3 as a linting warning
6. Update documentation
