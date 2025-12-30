"""
Test script for RBAC functionality in Library API

This script generates JWT tokens with different roles and makes requests
to test the permission system.

Usage:
    python test_rbac.py

Requirements:
    pip install pyjwt requests
"""

import os
import jwt
import requests
from datetime import datetime, timedelta
from typing import List

# Configuration
API_BASE_URL = "http://localhost:8000"
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-here")  # Get from env or use default
JWT_ALGORITHM = "HS256"


def generate_token(user_id: str, roles: List[str]) -> str:
    """
    Generate a JWT token with user_id and roles.

    Args:
        user_id: The user's unique identifier
        roles: List of roles (e.g., ["librarian", "admin"])

    Returns:
        JWT token string
    """
    payload = {
        "sub": user_id,  # Standard JWT claim for user ID
        "roles": roles,   # Custom claim for roles
        "exp": datetime.utcnow() + timedelta(hours=1),  # Token expires in 1 hour
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def make_request(method: str, endpoint: str, token: str = None, data: dict = None):
    """
    Make an API request with optional JWT token.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint (e.g., "/api/authors")
        token: JWT token string (optional)
        data: Request body data (optional)

    Returns:
        Response object
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unsupported method: {method}")

    return response


def test_public_access():
    """Test operations that should be public (no auth required)"""
    print("\n" + "="*60)
    print("TEST 1: Public Access (no token)")
    print("="*60)

    # List and read operations without permissions should be public
    response = make_request("GET", "/api/authors")
    print(f"GET /api/authors (no auth): {response.status_code}")
    if response.status_code == 200:
        print(f"  ✓ Public access allowed")
    else:
        print(f"  ✗ Expected 200, got {response.status_code}")


def test_librarian_access():
    """Test operations that require 'librarian' role"""
    print("\n" + "="*60)
    print("TEST 2: Librarian Access")
    print("="*60)

    # Generate token for librarian
    token = generate_token("librarian_user_123", ["librarian"])
    print(f"Generated token for librarian: {token[:50]}...")

    # Librarian should be able to create authors
    author_data = {
        "name": "Test Author",
        "bio": "Test bio",
        "nationality": "USA",
        "birthYear": 1980
    }

    response = make_request("POST", "/api/authors", token, author_data)
    print(f"POST /api/authors (librarian): {response.status_code}")
    if response.status_code == 201:
        print(f"  ✓ Librarian can create authors")
        author_id = response.json().get("id")

        # Librarian should be able to update authors
        update_data = {"bio": "Updated bio"}
        response = make_request("PUT", f"/api/authors/{author_id}", token, update_data)
        print(f"PUT /api/authors/{author_id} (librarian): {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ Librarian can update authors")

        # Librarian should NOT be able to delete authors (admin only)
        response = make_request("DELETE", f"/api/authors/{author_id}", token)
        print(f"DELETE /api/authors/{author_id} (librarian): {response.status_code}")
        if response.status_code == 403:
            print(f"  ✓ Librarian correctly denied delete permission")
        else:
            print(f"  ✗ Expected 403, got {response.status_code}")
    else:
        print(f"  ✗ Expected 201, got {response.status_code}")


def test_admin_access():
    """Test operations that require 'admin' role"""
    print("\n" + "="*60)
    print("TEST 3: Admin Access")
    print("="*60)

    # Generate token for admin
    token = generate_token("admin_user_456", ["admin"])
    print(f"Generated token for admin: {token[:50]}...")

    # Admin should be able to create authors
    author_data = {
        "name": "Admin Test Author",
        "bio": "Test bio",
        "nationality": "UK"
    }

    response = make_request("POST", "/api/authors", token, author_data)
    print(f"POST /api/authors (admin): {response.status_code}")
    if response.status_code == 201:
        print(f"  ✓ Admin can create authors")
        author_id = response.json().get("id")

        # Admin should be able to delete authors
        response = make_request("DELETE", f"/api/authors/{author_id}", token)
        print(f"DELETE /api/authors/{author_id} (admin): {response.status_code}")
        if response.status_code in [200, 204]:
            print(f"  ✓ Admin can delete authors")
        else:
            print(f"  ✗ Expected 200/204, got {response.status_code}")
    else:
        print(f"  ✗ Expected 201, got {response.status_code}")


def test_unauthorized_access():
    """Test that operations without proper roles are denied"""
    print("\n" + "="*60)
    print("TEST 4: Unauthorized Access")
    print("="*60)

    # Generate token with invalid role
    token = generate_token("regular_user_789", ["reader"])
    print(f"Generated token with 'reader' role (not declared): {token[:50]}...")

    # Should be denied for create operation
    author_data = {
        "name": "Unauthorized Author",
        "bio": "Should not be created"
    }

    response = make_request("POST", "/api/authors", token, author_data)
    print(f"POST /api/authors (reader role): {response.status_code}")
    if response.status_code == 403:
        print(f"  ✓ Unauthorized role correctly denied")
    else:
        print(f"  ✗ Expected 403, got {response.status_code}")


def test_member_permissions():
    """Test Member entity permissions (all operations restricted)"""
    print("\n" + "="*60)
    print("TEST 5: Member Entity Permissions")
    print("="*60)

    # Try to list members without auth (should fail - requires librarian/admin)
    response = make_request("GET", "/api/members")
    print(f"GET /api/members (no auth): {response.status_code}")
    if response.status_code == 403:
        print(f"  ✓ Public access correctly denied for members list")
    else:
        print(f"  ✗ Expected 403, got {response.status_code}")

    # Try with librarian token (should succeed)
    token = generate_token("librarian_user_123", ["librarian"])
    response = make_request("GET", "/api/members", token)
    print(f"GET /api/members (librarian): {response.status_code}")
    if response.status_code == 200:
        print(f"  ✓ Librarian can list members")
    else:
        print(f"  ✗ Expected 200, got {response.status_code}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("RBAC Testing Suite for Library API")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"JWT Algorithm: {JWT_ALGORITHM}")
    print("\nNOTE: Make sure the API server is running first!")
    print("      docker compose up -d")

    try:
        # Run all tests
        test_public_access()
        test_librarian_access()
        test_admin_access()
        test_unauthorized_access()
        test_member_permissions()

        print("\n" + "="*60)
        print("Testing Complete!")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to API server")
        print("  Make sure the server is running: docker compose up -d")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
