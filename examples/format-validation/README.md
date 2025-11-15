# Format Validation Demo

**What it demonstrates:**
- OpenAPI format specifications for strings:
  - `string<email>` - Email validation
  - `string<uri>` - URL validation
  - `string<uuid_str>` - UUID format
  - `string<date>` - RFC 3339 date
  - `string<time>` - Time-only format
  - `string<hostname>` - DNS hostname
  - `string<ipv4>` - IPv4 address
  - `string<byte>` - Base64 data
  - `string<password>` - Password field
- Numeric formats: `integer<int32>`, `integer<int64>`, `number<float>`, `number<double>`
- Range constraints: `string(3..30)`, `integer(18..120)`
- Generated Pydantic validation

**No dummy service needed** - demonstrates request validation.

## How to run

1. Generate and run:
   ```bash
   fdsl generate main.fdsl --out generated
   cd generated && docker compose -p thesis up
   ```

2. Test valid request:
   ```bash
   curl -X POST http://localhost:8090/api/users/register \
     -H "Content-Type: application/json" \
     -d '{
       "userId": "550e8400-e29b-41d4-a716-446655440000",
       "email": "user@example.com",
       "website": "https://example.com",
       "hostname": "api.example.com",
       "ipAddress": "192.168.1.1",
       "birthDate": "1990-01-15",
       "registeredAt": "2025-11-15T10:30:00Z",
       "username": "johndoe",
       "passwordHash": "secret123"
     }'
   ```

3. Test invalid request (should fail validation):
   ```bash
   curl -X POST http://localhost:8090/api/users/register \
     -H "Content-Type: application/json" \
     -d '{
       "userId": "invalid-uuid",
       "email": "not-an-email",
       "username": "ab"
     }'
   ```

## What you'll learn

All format specifications compile to Pydantic field validators. Invalid data returns 422 Unprocessable Entity with detailed error messages.
