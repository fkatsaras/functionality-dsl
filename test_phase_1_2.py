#!/usr/bin/env python3
"""
Test script for Phase 1 & 2 of FDSL redesign.
Tests grammar, validation, exposure map, and CRUD helpers.
"""

from functionality_dsl.language import build_model
from functionality_dsl.api.exposure_map import build_exposure_map
from functionality_dsl.api.crud_helpers import (
    get_operation_http_method,
    get_operation_path_suffix,
    get_operation_status_code,
    derive_request_schema_name,
    get_writable_attributes,
)

def test_basic_syntax():
    """Test that new syntax parses correctly."""
    print("=" * 60)
    print("TEST 1: Basic Syntax Parsing")
    print("=" * 60)

    m = build_model('./test_new_syntax.fdsl')

    assert len(m.entities) == 1, f"Expected 1 entity, got {len(m.entities)}"
    assert len(m.externalrest) == 1, f"Expected 1 source, got {len(m.externalrest)}"

    entity = m.entities[0]
    assert entity.name == "User"
    assert entity.expose is not None, "Entity should have expose block"
    assert entity.source is not None, "Entity should have source binding"

    source = m.externalrest[0]
    assert source.name == "UserDB"
    assert hasattr(source, "base_url") and source.base_url is not None
    assert hasattr(source, "crud") and source.crud is not None

    print("[OK] Entities parsed correctly")
    print("[OK] Sources parsed correctly")
    print("[OK] Expose blocks parsed correctly")
    print()

def test_exposure_map():
    """Test exposure map builder."""
    print("=" * 60)
    print("TEST 2: Exposure Map Building")
    print("=" * 60)

    m = build_model('./test_new_syntax.fdsl')
    exp_map = build_exposure_map(m)

    assert "User" in exp_map, "User should be in exposure map"

    user_config = exp_map["User"]
    assert user_config["rest_path"] == "/api/users"
    assert set(user_config["operations"]) == {"list", "read", "create"}
    assert user_config["id_field"] == "id"
    assert user_config["source"].name == "UserDB"

    print(f"✓ Exposed entities: {list(exp_map.keys())}")
    print(f"✓ User REST path: {user_config['rest_path']}")
    print(f"✓ User operations: {user_config['operations']}")
    print(f"✓ User id_field: {user_config['id_field']}")
    print()

def test_crud_helpers():
    """Test CRUD helper functions."""
    print("=" * 60)
    print("TEST 3: CRUD Convention Helpers")
    print("=" * 60)

    # Test operation mappings
    assert get_operation_http_method("list") == "GET"
    assert get_operation_http_method("create") == "POST"
    assert get_operation_http_method("update") == "PUT"
    assert get_operation_http_method("delete") == "DELETE"

    assert get_operation_path_suffix("list", "id") == ""
    assert get_operation_path_suffix("read", "id") == "/{id}"
    assert get_operation_path_suffix("create", "id") == ""
    assert get_operation_path_suffix("update", "id") == "/{id}"

    assert get_operation_status_code("create") == 201
    assert get_operation_status_code("delete") == 204
    assert get_operation_status_code("read") == 200

    assert derive_request_schema_name("User", "create") == "UserCreate"
    assert derive_request_schema_name("User", "update") == "UserUpdate"
    assert derive_request_schema_name("User", "patch") == "UserPatch"

    print("✓ HTTP method mappings correct")
    print("✓ Path suffix mappings correct")
    print("✓ Status code mappings correct")
    print("✓ Schema name derivation correct")
    print()

def test_writable_attributes():
    """Test writable attributes filtering."""
    print("=" * 60)
    print("TEST 4: Writable Attributes Filtering")
    print("=" * 60)

    m = build_model('./test_new_syntax.fdsl')
    entity = m.entities[0]

    # All attributes are writable (no readonly fields, no computed attrs)
    writable = get_writable_attributes(entity, readonly_fields=[])
    writable_names = [a.name for a in writable]

    assert "id" in writable_names
    assert "email" in writable_names
    assert "name" in writable_names

    # Test with readonly fields
    writable = get_writable_attributes(entity, readonly_fields=["id"])
    writable_names = [a.name for a in writable]

    assert "id" not in writable_names
    assert "email" in writable_names
    assert "name" in writable_names

    print(f"✓ Writable attributes (no readonly): {[a.name for a in get_writable_attributes(entity)]}")
    print(f"✓ Writable attributes (id readonly): {[a.name for a in get_writable_attributes(entity, ['id'])]}")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FDSL REDESIGN - PHASE 1 & 2 TEST SUITE")
    print("=" * 60)
    print()

    try:
        test_basic_syntax()
        test_exposure_map()
        test_crud_helpers()
        test_writable_attributes()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print()
        print("Summary:")
        print("- Grammar updated with ExposeBlock and CrudBlock")
        print("- Validation added for exposure blocks and CRUD configs")
        print("- Exposure map builder working correctly")
        print("- CRUD convention helpers implemented")
        print()
        print("Next steps: OpenAPI generation, Router generation, Service generation")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        raise
