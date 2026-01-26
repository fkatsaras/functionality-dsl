# BYODB Setup Guide for E-Commerce Example

This guide shows how to set up an external PostgreSQL database for the BYODB (Bring Your Own Database) e-commerce example.

## Prerequisites

- PostgreSQL installed locally OR Docker
- Generated code from `ecommerce_byodb.fdsl`

## Option 1: PostgreSQL via Docker (Recommended for Testing)

### Step 1: Start PostgreSQL Container

```bash
cd examples/v2/ecommerce/byodb_setup
docker compose -f docker-compose.byodb-db.yml up -d
```

This starts PostgreSQL on port 5433 (to avoid conflicts with other Postgres instances).

### Step 2: Initialize the Schema

```bash
# Wait a few seconds for Postgres to start, then run:
docker exec -i ecommerce-byodb-db psql -U shop_admin -d ecommerce_shop < init_schema.sql
```

### Step 3: Configure the Generated App

Edit `generated_byodb/.env`:
```
MY_ECOMM_DB_URL=postgresql://shop_admin:shop_secret@host.docker.internal:5433/ecommerce_shop
```

### Step 4: Run the Generated App

```bash
cd generated_byodb
docker compose up
```

### Step 5: Test the Auth Flow

```bash
# Register a user
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"login_id": "alice@shop.com", "password": "password123", "role": "customer"}'

# Login (returns session cookie)
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login_id": "alice@shop.com", "password": "password123"}' \
  -c cookies.txt

# Access protected endpoint
curl http://localhost:8080/api/cart -b cookies.txt
```

## Option 2: Local PostgreSQL Installation

### Step 1: Create Database and User

```bash
psql -U postgres
```

```sql
CREATE DATABASE ecommerce_shop;
CREATE USER shop_admin WITH PASSWORD 'shop_secret';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_shop TO shop_admin;
\c ecommerce_shop
GRANT ALL ON SCHEMA public TO shop_admin;
```

### Step 2: Initialize Schema

```bash
psql -U shop_admin -d ecommerce_shop < init_schema.sql
```

### Step 3: Configure the Generated App

Edit `generated_byodb/.env`:
```
MY_ECOMM_DB_URL=postgresql://shop_admin:shop_secret@host.docker.internal:5432/ecommerce_shop
```

## Schema Overview

The BYODB example uses custom table/column names:

### Users Table: `shop_users`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| email | VARCHAR(255) | Login identifier (mapped from `id:`) |
| password_hash | VARCHAR(255) | Bcrypt hash (mapped from `password:`) |
| user_role | VARCHAR(50) | User role (mapped from `role:`) |

### Sessions Table: `user_sessions`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| session_token | VARCHAR(64) | Session ID (mapped from `session_id:`) |
| user_email | VARCHAR(255) | User reference (mapped from `user_id:`) |
| user_roles | VARCHAR(500) | JSON array of roles (mapped from `roles:`) |
| expires_at | TIMESTAMP | Expiry time (mapped from `expires_at:`) |

## Cleanup

```bash
# Stop and remove the BYODB database
docker compose -f docker-compose.byodb-db.yml down -v
```
