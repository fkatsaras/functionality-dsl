# User Management Demo

**What it demonstrates:**
- Complete CRUD operations (Create, Read, Update, Delete)
- User registration and login workflows
- Request validation with range constraints
- Entity transformation for requests and responses
- Multiple mutation types (POST, PUT, PATCH, DELETE)
- ActionForm components for all operations

**Requires dummy service:** Yes - In-memory user database

## How to run

1. **Start the dummy database service:**
   ```bash
   bash run.sh
   ```
   This starts an in-memory REST API on port 9000 with user management endpoints.

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

   **Register a user:**
   ```bash
   curl -X POST http://localhost:8081/api/users/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "john_doe",
       "email": "john@example.com",
       "password": "secret123"
     }'
   ```

   **Login:**
   ```bash
   curl -X POST http://localhost:8081/api/users/login \
     -H "Content-Type: application/json" \
     -d '{"username": "john_doe", "password": "secret123"}'
   ```

   **List users:**
   ```bash
   curl http://localhost:8081/api/users
   ```

## What you'll learn

- How to build complete auth systems with FDSL
- Entity validation with constraints (`string(3..50)`, `string<email>`)
- Transformation pipelines for requests (`find()`, `trim()`, `filter()`)
- Mapping external service responses to clean API responses
