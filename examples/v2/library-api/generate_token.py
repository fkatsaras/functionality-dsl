"""
Generate JWT tokens for testing RBAC

Usage:
    python generate_token.py --user admin_user --roles admin
    python generate_token.py --user librarian_user --roles librarian
    python generate_token.py --user multi_role_user --roles librarian,admin

Requirements:
    pip install pyjwt
"""

import argparse
from datetime import datetime, timedelta

try:
    import jwt
except ImportError:
    print("Error: PyJWT library not installed. Install it with:")
    print("  pip install pyjwt")
    exit(1)

# Must match the secret in main.fdsl Auth block
JWT_SECRET = "test-secret-key-for-library-api-demo-only-change-in-production"
JWT_ALGORITHM = "HS256"


def generate_token(user_id: str, roles: list[str], hours: int = 24) -> str:
    """Generate a JWT token"""
    from datetime import timezone
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,           # User ID (standard JWT claim)
        "roles": roles,           # Roles list
        "exp": now + timedelta(hours=hours),
        "iat": now
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError as e:
        return {"error": f"Invalid token: {e}"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate JWT tokens for RBAC testing")
    parser.add_argument("--user", required=True, help="User ID")
    parser.add_argument("--roles", required=True, help="Comma-separated roles (e.g., 'admin' or 'librarian,admin')")
    parser.add_argument("--hours", type=int, default=24, help="Token expiration in hours (default: 24)")
    parser.add_argument("--decode", help="Decode an existing token instead of generating new one")

    args = parser.parse_args()

    if args.decode:
        # Decode mode
        print("\nDecoding token...")
        payload = decode_token(args.decode)
        print("\nToken Payload:")
        for key, value in payload.items():
            if key == "exp" or key == "iat":
                dt = datetime.fromtimestamp(value) if not isinstance(value, str) else value
                print(f"  {key}: {value} ({dt})")
            else:
                print(f"  {key}: {value}")
    else:
        # Generate mode
        roles_list = [r.strip() for r in args.roles.split(",")]

        print(f"\nGenerating JWT token...")
        print(f"  User ID: {args.user}")
        print(f"  Roles: {roles_list}")
        print(f"  Expires in: {args.hours} hours")
        print(f"  Algorithm: {JWT_ALGORITHM}")

        token = generate_token(args.user, roles_list, args.hours)

        print(f"\nGenerated Token:")
        print(f"{token}")

        print(f"\n\nTo use this token in curl:")
        print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/authors')

        print(f"\n\nTo use this token in Postman:")
        print(f"  1. Go to Authorization tab")
        print(f"  2. Select 'Bearer Token' type")
        print(f"  3. Paste token: {token}")

        print(f"\n\nTo decode this token:")
        print(f'python generate_token.py --decode "{token}"')
