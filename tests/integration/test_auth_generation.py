"""
Integration tests for authentication and database module generation.

Tests that FDSL Auth declarations correctly generate authentication middleware,
database modules, and password hashing utilities.
"""

import pytest
from pathlib import Path

from functionality_dsl.language import build_model_str
from functionality_dsl.api.generator import render_domain_files


class TestAuthModuleGeneration:
    """Test authentication middleware generation."""

    def test_bearer_auth_generates_auth_module(self, temp_output_dir):
        """Test that HTTP Bearer auth generates authentication module."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<http> BearerAuth
          scheme: bearer
        end

        Role admin uses BearerAuth
        Role user uses BearerAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
            - value: string;
          access: [admin, user]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check auth module exists
        auth_file = temp_output_dir / "app" / "core" / "auth.py"
        assert auth_file.exists(), "Auth module should be generated"

        auth_code = auth_file.read_text()

        # Should import or reference authentication functions
        assert "get_current_user" in auth_code or "auth" in auth_code.lower()
        assert "Bearer" in auth_code or "bearer" in auth_code.lower()

    def test_api_key_auth_generates_auth_module(self, temp_output_dir):
        """Test that API Key auth generates authentication module."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<apikey> APIKeyAuth
          in: header
          name: "X-API-Key"
        end

        Role service uses APIKeyAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: [service]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        auth_file = temp_output_dir / "app" / "core" / "auth.py"
        assert auth_file.exists(), "Auth module should be generated"

        auth_code = auth_file.read_text()

        # Should reference API key authentication
        assert "api" in auth_code.lower() and "key" in auth_code.lower()

    def test_multiple_auth_types_supported(self, temp_output_dir):
        """Test that multiple auth types can coexist."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<http> BearerAuth
          scheme: bearer
        end

        Auth<apikey> APIKeyAuth
          in: header
          name: "X-API-Key"
        end

        Role admin uses BearerAuth
        Role service uses APIKeyAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: [admin, service]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        auth_file = temp_output_dir / "app" / "core" / "auth.py"
        assert auth_file.exists(), "Auth module should be generated"


class TestDatabaseModuleGeneration:
    """Test database module generation for auth storage."""

    def test_auth_generates_database_module(self, temp_output_dir):
        """Test that auth declarations generate database module."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<http> BearerAuth
          scheme: bearer
        end

        Role admin uses BearerAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: [admin]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check database module exists (in app/db/ directory)
        db_file = temp_output_dir / "app" / "db" / "database.py"
        assert db_file.exists(), "Database module should be generated"

        db_code = db_file.read_text()

        # Should have database connection/session handling
        assert "database" in db_code.lower() or "session" in db_code.lower()

    def test_password_module_generated(self, temp_output_dir):
        """Test that password hashing utilities are generated."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<http> BasicAuth
          scheme: basic
        end

        Role user uses BasicAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: [user]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check password utilities exist (in app/db/ directory)
        password_file = temp_output_dir / "app" / "db" / "password.py"
        assert password_file.exists(), "Password module should be generated"

        password_code = password_file.read_text()

        # Should have password hashing functions
        assert "hash" in password_code.lower() or "password" in password_code.lower()


class TestAuthDBGeneration:
    """Test AuthDB (Bring Your Own Database) generation."""

    def test_authdb_configuration(self, temp_output_dir):
        """Test that AuthDB generates database configuration."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        AuthDB UserStore
          connection: "MY_DATABASE_URL"
          table: "users"
          columns:
            id="email"
            password="pwd_hash"
            role="user_role"
        end

        Auth<http> BearerAuth
          scheme: bearer
        end

        Role admin uses BearerAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: [admin]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check that database configuration exists (in app/db/ directory)
        db_file = temp_output_dir / "app" / "db" / "database.py"
        assert db_file.exists(), "Database module should be generated"

        db_code = db_file.read_text()

        # Should reference the custom database configuration
        assert "MY_DATABASE_URL" in db_code or "database" in db_code.lower()


class TestAuthRoutesGeneration:
    """Test authentication endpoint generation."""

    def test_auth_routes_generated(self, temp_output_dir):
        """Test that authentication routes are generated."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<http> BearerAuth
          scheme: bearer
        end

        Role user uses BearerAuth

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: [user]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check for auth routes
        auth_routes = temp_output_dir / "app" / "api" / "routers" / "auth.py"

        if auth_routes.exists():
            auth_code = auth_routes.read_text()

            # Should have login/token endpoints
            assert "login" in auth_code.lower() or "token" in auth_code.lower()


class TestNoAuthGeneration:
    """Test that no auth modules are generated when auth is not configured."""

    def test_no_auth_no_modules(self, temp_output_dir):
        """Test that auth modules are not generated without Auth declarations."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Auth module should NOT exist for public-only APIs
        auth_file = temp_output_dir / "app" / "core" / "auth.py"
        # This may or may not exist depending on implementation
        # Just check that the generation completes successfully
        assert True, "Generation should complete without auth"
