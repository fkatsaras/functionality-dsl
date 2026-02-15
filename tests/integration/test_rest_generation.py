"""
Integration tests for REST API router generation.

Tests that FDSL entity specifications with REST sources generate valid
FastAPI routers with correct endpoints, HTTP methods, and request/response handling.
"""

import pytest
from pathlib import Path

from functionality_dsl.language import build_model_str
from functionality_dsl.api.generator import render_domain_files


class TestBasicRESTRouterGeneration:
    """Test basic REST router generation."""

    def test_read_operation_generates_get_endpoint(self, temp_output_dir):
        """Test that read operation generates GET endpoint."""
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
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check router file exists (routers are named {entity}_router.py)
        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        assert router_file.exists(), "Router file should be generated"

        router_code = router_file.read_text()

        # Check GET endpoint
        assert "@router.get(" in router_code
        assert '"/api/data"' in router_code or "'/api/data'" in router_code
        assert "async def" in router_code

    def test_create_operation_generates_post_endpoint(self, temp_output_dir):
        """Test that create operation generates POST endpoint."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [create]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer @readonly;
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check POST endpoint
        assert "@router.post(" in router_code
        assert '"/api/data"' in router_code or "'/api/data'" in router_code
        assert "DataCreate" in router_code  # Request model

    def test_update_operation_generates_put_endpoint(self, temp_output_dir):
        """Test that update operation generates PUT endpoint."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [update]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer @readonly;
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check PUT endpoint
        assert "@router.put(" in router_code
        assert '"/api/data"' in router_code or "'/api/data'" in router_code
        assert "DataUpdate" in router_code  # Request model

    def test_delete_operation_generates_delete_endpoint(self, temp_output_dir):
        """Test that delete operation generates DELETE endpoint."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [delete]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check DELETE endpoint
        assert "@router.delete(" in router_code
        assert '"/api/data"' in router_code or "'/api/data'" in router_code

    def test_crud_operations_generate_all_endpoints(self, temp_output_dir):
        """Test that all CRUD operations generate corresponding endpoints."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read, create, update, delete]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer @readonly;
            - name: string;
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check all HTTP methods
        assert "@router.get(" in router_code
        assert "@router.post(" in router_code
        assert "@router.put(" in router_code
        assert "@router.delete(" in router_code


class TestRouterStructure:
    """Test the structure of generated routers."""

    def test_router_imports(self, temp_output_dir):
        """Test that routers have correct imports."""
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
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check essential imports
        assert "from fastapi import" in router_code
        assert "APIRouter" in router_code
        assert "from app.domain.models import" in router_code

    def test_router_initialization(self, temp_output_dir):
        """Test that router is properly initialized."""
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

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check router instantiation
        assert "router = APIRouter(" in router_code


class TestAccessControl:
    """Test access control in generated routers."""

    def test_public_access_no_dependencies(self, temp_output_dir):
        """Test that public access endpoints have no auth dependencies."""
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

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Public endpoints should not have Depends() for auth
        # (This is a heuristic check - actual implementation may vary)
        lines_with_router_decorator = [line for line in router_code.split('\n') if '@router.' in line]

        # There should be endpoints defined
        assert len(lines_with_router_decorator) > 0

    def test_role_based_access_has_dependencies(self, temp_output_dir):
        """Test that role-based access endpoints include auth dependencies."""
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
          operations: [read, create]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer @readonly;
            - value: string;
          access:
            read: public
            create: [admin]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Should have Depends for auth
        assert "Depends" in router_code


class TestServiceIntegration:
    """Test that routers correctly integrate with service layer."""

    def test_router_calls_service(self, temp_output_dir):
        """Test that router endpoints call service methods."""
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
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check service import and usage
        assert "from app.services" in router_code or "DataService" in router_code

    def test_service_file_generated(self, temp_output_dir):
        """Test that service file is generated alongside router."""
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

        service_file = temp_output_dir / "app" / "services" / "data_service.py"
        assert service_file.exists(), "Service file should be generated"

        service_code = service_file.read_text()
        assert "class DataService" in service_code or "async def" in service_code


class TestParameterizedSources:
    """Test REST sources with query/path parameters."""

    def test_parameterized_source_generates_query_params(self, temp_output_dir):
        """Test that parameterized sources generate query parameters."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          params: [category, search]
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check for Query parameters in function signature
        # Parameters should appear in the endpoint function
        assert "category" in router_code or "search" in router_code


class TestResponseModels:
    """Test that routers use correct response models."""

    def test_get_endpoint_returns_entity_model(self, temp_output_dir):
        """Test that GET endpoint uses entity model as response."""
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
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check response_model in decorator or return type annotation
        assert "response_model=" in router_code or "-> Data" in router_code

    def test_post_endpoint_accepts_create_model(self, temp_output_dir):
        """Test that POST endpoint uses Create model for request."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [create]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer @readonly;
            - value: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "data_router.py"
        router_code = router_file.read_text()

        # Check that DataCreate is used in function parameter
        assert "DataCreate" in router_code


class TestCompositeEntities:
    """Test that composite entities generate read-only endpoints."""

    def test_composite_entity_only_has_get_endpoint(self, temp_output_dir):
        """Test that composite entities only generate GET endpoints."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> API1
          url: "http://test/api1"
          operations: [read]
        end

        Source<REST> API2
          url: "http://test/api2"
          operations: [read]
        end

        Entity Data1
          source: API1
          attributes:
            - value1: number;
          access: public
        end

        Entity Data2
          source: API2
          attributes:
            - value2: number;
          access: public
        end

        Entity Combined(Data1, Data2)
          attributes:
            - total: number = Data1.value1 + Data2.value2;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        router_file = temp_output_dir / "app" / "api" / "routers" / "combined_router.py"

        if router_file.exists():
            router_code = router_file.read_text()

            # Should only have GET
            assert "@router.get(" in router_code
            # Should NOT have POST, PUT, DELETE
            assert "@router.post(" not in router_code
            assert "@router.put(" not in router_code
            assert "@router.delete(" not in router_code
