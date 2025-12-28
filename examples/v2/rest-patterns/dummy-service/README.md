# REST Patterns Dummy Service

This dummy service provides all REST endpoints referenced in FDSL REST patterns (01-07).

## Endpoints

### Pattern 01: Basic CRUD - Users
- `GET /users` - List all users
- `GET /users/{id}` - Get user by ID
- `POST /users` - Create user
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

### Pattern 02: Read-only Fields - Orders
- `GET /orders` - List all orders
- `GET /orders/{id}` - Get order by ID
- `POST /orders` - Create order (auto-calculates totals)
- `PUT /orders/{id}` - Update order (recalculates totals)
- `DELETE /orders/{id}` - Delete order

### Pattern 03: Singleton Entity
- `GET /config` - Get application config (singleton)
- `GET /profile` - Get user profile (singleton)

### Pattern 04: Composite Entity - Products
- `GET /products` - List all products
- `GET /products/{id}` - Get product by ID
- `POST /products` - Create product
- `PUT /products/{id}` - Update product
- `DELETE /products/{id}` - Delete product

### Pattern 05: Filters - Books & Customers
**Books:**
- `GET /books?author={value}&year={value}&genre={value}&inStock={bool}` - List books with filters
- `GET /books/{id}` - Get book by ID
- `POST /books` - Create book
- `PUT /books/{id}` - Update book
- `DELETE /books/{id}` - Delete book

**Customers:**
- `GET /customers?country={value}&status={value}` - List customers with filters
- `GET /customers/{id}` - Get customer by ID
- `POST /customers` - Create customer
- `PUT /customers/{id}` - Update customer

### Pattern 06: Array Aggregation - Orders & OrderItems
**Orders:**
- `GET /array-orders?userId={value}&status={value}` - List orders with filters
- `GET /array-orders/{orderId}` - Get order by ID
- `POST /array-orders` - Create order
- `PUT /array-orders/{orderId}` - Update order
- `DELETE /array-orders/{orderId}` - Delete order

**Order Items:**
- `GET /order-items?orderId={value}&productId={value}` - List order items with filters
- `GET /order-items/{itemId}` - Get order item by ID
- `POST /order-items` - Create order item
- `PUT /order-items/{itemId}` - Update order item
- `DELETE /order-items/{itemId}` - Delete order item

### Pattern 07: Partial CRUD

**Audit Logs (create-only):**
- `GET /audit-logs` - List audit logs
- `GET /audit-logs/{id}` - Get audit log
- `POST /audit-logs` - Create audit log
- ❌ No update or delete (immutable logs)

**Notifications (update-only):**
- `GET /notifications` - List notifications
- `GET /notifications/{id}` - Get notification
- `PUT /notifications/{id}` - Update notification (mark as read)
- ❌ No create or delete (system-generated)

## Running

### With Docker Compose

```bash
cd examples/v2/rest-patterns/dummy-service
docker compose up --build
```

Service will be available at `http://localhost:9001`

### Standalone

```bash
cd examples/v2/rest-patterns/dummy-service
pip install -r requirements.txt
python app.py
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:9001/docs
- ReDoc: http://localhost:9001/redoc

## Sample Data

The service includes pre-populated sample data for all entities to make testing easier.
