-- BYODB Schema Initialization for E-Commerce Example
-- This creates the tables expected by the ecommerce_byodb.fdsl configuration.
--
-- Run this after starting the PostgreSQL container:
--   docker exec -i ecommerce-byodb-db psql -U shop_admin -d ecommerce_shop < init_schema.sql

-- ============================================
-- Users Table: shop_users
-- ============================================
-- Maps to AuthDB columns:
--   id: "email"           -> email column
--   password: "password_hash" -> password_hash column
--   role: "user_role"     -> user_role column

CREATE TABLE IF NOT EXISTS shop_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_role VARCHAR(50) NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups by email
CREATE INDEX IF NOT EXISTS idx_shop_users_email ON shop_users(email);

-- ============================================
-- Sessions Table: user_sessions
-- ============================================
-- Maps to AuthDB sessions columns:
--   session_id: "session_token" -> session_token column
--   user_id: "user_email"       -> user_email column
--   roles: "user_roles"         -> user_roles column
--   expires_at: "expires_at"    -> expires_at column

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    session_token VARCHAR(64) UNIQUE NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    user_roles VARCHAR(500) NOT NULL,  -- JSON array of roles
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_email ON user_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- ============================================
-- Optional: Insert a test user
-- ============================================
-- Password: "password123" (bcrypt hash)
-- You can register users via the API instead

-- INSERT INTO shop_users (email, password_hash, user_role)
-- VALUES (
--     'test@shop.com',
--     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4VG5OCWzqKlPQR.O',
--     'customer'
-- );

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO shop_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO shop_admin;
