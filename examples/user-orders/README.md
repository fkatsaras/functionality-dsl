# User Orders - Multi-Service Architecture Demo

**What it demonstrates:**
- Multi-microservice architecture pattern
- Parameter passing between endpoints and sources
- Query parameter filtering in entities
- ObjectView component with nested field access
- PageView component with path + query parameters
- Complete CRUD for order management
- Statistical aggregations (`sum()`, `avg()`, `len()`)

**Requires dummy services:** Yes - Two microservices (user-service + order-service)

## How to run

1. **Start both dummy services:**
   ```bash
   bash run.sh
   ```
   This starts:
   - User Service (port 8001) - manages user data
   - Order Service (port 8002) - manages order data

2. **In a new terminal, generate the backend code:**
   ```bash
   fdsl generate main.fdsl --out generated
   ```

3. **Run the generated application:**
   ```bash
   cd generated
   docker compose -p thesis up
   ```

4. **Test the endpoints:**

   **List all orders:**
   ```bash
   curl http://localhost:8000/api/orders
   ```

   **Get user orders with filters:**
   ```bash
   curl "http://localhost:8000/api/users/user-001/orders?status=pending&page=1"
   ```

   **Create order:**
   ```bash
   curl -X POST http://localhost:8000/api/orders \
     -H "Content-Type: application/json" \
     -d '{
       "userId": "user-001",
       "items": [{"productId": "p1", "name": "Widget", "price": 29.99, "quantity": 2}]
     }'
   ```

## What you'll learn

- **Microservice communication**: FDSL as API gateway/aggregator
- **Parameter flow**: Endpoint params → Source params with expressions
- **Filtering in entities**: Using `filter()` with endpoint parameters
- **Component binding patterns**:
  - Table → parameter-free endpoints
  - ObjectView → path parameters only
  - PageView → path + query parameters
- **Computed summaries**: Aggregate order statistics from filtered data
