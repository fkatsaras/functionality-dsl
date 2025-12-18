# Product Catalog API (v2 Entity-Centric)

Simple product catalog with full CRUD operations using the new entity-centric syntax.

## Architecture

```
Client → FastAPI (Generated) → Dummy Product Service (Mock DB)
```

## Files

- `main.fdsl` - Entity-centric FDSL definition
- `dummy-service/` - Mock external product database API

## Generate & Run

**1. Generate the API:**
```bash
fdsl generate main.fdsl --out generated
```

**2. Start dummy service (creates network):**
```bash
cd dummy-service
docker compose up --build
```

**3. Start generated API (in another terminal):**
```bash
cd generated
docker compose -p thesis up --build
```

**4. Test the API:**
```bash
# List products
curl http://localhost:8080/api/products

# Get single product
curl http://localhost:8080/api/products/prod-1

# Create product
curl -X POST http://localhost:8080/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Mouse","price":25.99,"category":"Electronics","inStock":true}'

# Update product
curl -X PUT http://localhost:8080/api/products/prod-1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Gaming Laptop","price":1299.99,"category":"Electronics","inStock":true}'

# Delete product
curl -X DELETE http://localhost:8080/api/products/prod-1

# OpenAPI docs
open http://localhost:8080/docs
```

## What's Generated

- **Models**: `Product`, `ProductCreate`, `ProductUpdate`
- **Source Client**: HTTP client for ProductDB
- **Service**: Business logic for CRUD operations
- **Router**: 5 FastAPI endpoints (list, read, create, update, delete)
