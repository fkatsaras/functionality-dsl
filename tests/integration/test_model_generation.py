"""
Integration tests for Pydantic model generation.

Tests that FDSL entity specifications are correctly transformed into
valid Pydantic models with proper field types, constraints, and schemas.
"""

import pytest
from pathlib import Path
import re

from functionality_dsl.language import build_model_str
from functionality_dsl.api.generators.core.model_generator import generate_domain_models
from functionality_dsl.api.extractors import get_entities


class TestBasicModelGeneration:
    """Test basic Pydantic model generation from entities."""

    def test_simple_entity_generates_model(self, temp_output_dir):
        """Test that a simple entity generates a valid Pydantic model."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> TestAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity SimpleData
          source: TestAPI
          attributes:
            - id: integer;
            - name: string;
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        # Generate models
        generate_domain_models(model, templates_dir, temp_output_dir)

        # Check that models.py was created
        models_file = temp_output_dir / "app" / "domain" / "models.py"
        assert models_file.exists(), "models.py should be generated"

        # Read generated code
        generated_code = models_file.read_text()

        # Verify model class exists
        assert "class SimpleData(BaseModel):" in generated_code

        # Verify fields
        assert "id: int" in generated_code
        assert "name: str" in generated_code
        assert "value: float" in generated_code

    def test_readonly_fields_excluded_from_create_schema(self, temp_output_dir):
        """Test that @readonly fields are excluded from Create schemas."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> TestAPI
          url: "http://test/data"
          operations: [read, create]
        end

        Entity User
          source: TestAPI
          attributes:
            - id: integer @readonly;
            - email: string;
            - created_at: string<datetime> @readonly;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Main model should have all fields
        assert "class User(BaseModel):" in generated_code
        assert "id: int" in generated_code
        assert "email: str" in generated_code
        assert "created_at:" in generated_code

        # Create schema should exclude readonly fields
        assert "class UserCreate(BaseModel):" in generated_code
        # Should only have email, not id or created_at
        # Check that UserCreate doesn't have id or created_at
        user_create_section = self._extract_class_section(generated_code, "UserCreate")
        assert "id:" not in user_create_section
        assert "created_at:" not in user_create_section
        assert "email:" in user_create_section

    def test_optional_fields_in_schemas(self, temp_output_dir):
        """Test that @optional fields are properly handled."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> TestAPI
          url: "http://test/data"
          operations: [read, create, update]
        end

        Entity Profile
          source: TestAPI
          attributes:
            - id: integer @readonly;
            - username: string;
            - bio: string @optional;
            - avatar_url: string<uri> @optional;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check that optional fields are wrapped in Optional[]
        assert "Optional[str]" in generated_code or "str | None" in generated_code

    def test_nullable_fields(self, temp_output_dir):
        """Test that nullable fields (?) are properly typed."""
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
            - value: string?;
            - count: integer?;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Nullable fields should allow None
        assert "Optional[str]" in generated_code or "str | None" in generated_code

    def _extract_class_section(self, code, class_name):
        """Extract the content of a specific class from generated code."""
        pattern = rf'class {class_name}\([^)]+\):.*?(?=\nclass |\Z)'
        match = re.search(pattern, code, re.DOTALL)
        return match.group(0) if match else ""


class TestComplexTypeGeneration:
    """Test generation of complex types (arrays, objects, nested schemas)."""

    def test_array_type_generation(self, temp_output_dir):
        """Test that array types are properly generated."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - id: integer;
            - name: string;
        end

        Entity Tag
          attributes:
            - label: string;
        end

        Source<REST> ContainerAPI
          url: "http://test/containers"
          operations: [read]
        end

        Entity Container
          source: ContainerAPI
          attributes:
            - id: integer;
            - items: array<Item>;
            - tags: array<Tag>;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check List type imports
        assert "from typing import" in generated_code
        assert "List" in generated_code or "list" in generated_code

        # Check array field types
        assert "List[Item]" in generated_code or "list[Item]" in generated_code
        assert "List[Tag]" in generated_code or "list[Tag]" in generated_code

    def test_object_type_generation(self, temp_output_dir):
        """Test that object types are properly generated."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Address
          attributes:
            - street: string;
            - city: string;
            - zip: string;
        end

        Source<REST> PersonAPI
          url: "http://test/people"
          operations: [read]
        end

        Entity Person
          source: PersonAPI
          attributes:
            - id: integer;
            - name: string;
            - address: object<Address>;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Address should be defined before Person
        address_pos = generated_code.find("class Address")
        person_pos = generated_code.find("class Person")
        assert address_pos < person_pos, "Nested entity should be defined first"

        # Check object field type
        assert "address: Address" in generated_code

    def test_nested_arrays_and_objects(self, temp_output_dir):
        """Test complex nested structures."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Tag
          attributes:
            - id: integer;
            - label: string;
        end

        Entity Product
          attributes:
            - id: integer;
            - name: string;
            - tags: array<Tag>;
        end

        Source<REST> OrderAPI
          url: "http://test/orders"
          operations: [read]
        end

        Entity Order
          source: OrderAPI
          attributes:
            - id: integer;
            - products: array<Product>;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check proper ordering: Tag -> Product -> Order
        tag_pos = generated_code.find("class Tag")
        product_pos = generated_code.find("class Product")
        order_pos = generated_code.find("class Order")

        assert tag_pos < product_pos < order_pos, "Entities should be ordered by dependency"


class TestTypeConstraints:
    """Test generation of field constraints and validators."""

    def test_integer_constraints(self, temp_output_dir):
        """Test integer range constraints."""
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
            - positive: integer(1..);
            - limited: integer(0..100);
            - age: integer(0..150);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check for Field constraints
        assert "Field(" in generated_code
        assert "ge=" in generated_code  # greater than or equal
        assert "le=" in generated_code  # less than or equal

    def test_string_format_constraints(self, temp_output_dir):
        """Test string format validators (email, uri, datetime)."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> ContactAPI
          url: "http://test/contacts"
          operations: [read]
        end

        Entity Contact
          source: ContactAPI
          attributes:
            - id: integer;
            - email: string<email>;
            - website: string<uri>;
            - created: string<datetime>;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check for Pydantic types
        assert "EmailStr" in generated_code or "email" in generated_code.lower()
        assert "HttpUrl" in generated_code or "AnyUrl" in generated_code or "uri" in generated_code.lower()

    def test_number_precision(self, temp_output_dir):
        """Test number type precision (float vs int)."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> MeasurementAPI
          url: "http://test/measurements"
          operations: [read]
        end

        Entity Measurement
          source: MeasurementAPI
          attributes:
            - id: integer;
            - value: number;
            - count: integer;
            - ratio: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check type mapping
        assert "int" in generated_code
        assert "float" in generated_code


class TestComputedFields:
    """Test handling of computed attributes in models."""

    def test_computed_fields_in_composite_entity(self, temp_output_dir):
        """Test that computed fields are present in composite entities."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity BaseData
          source: DataAPI
          attributes:
            - value1: number;
            - value2: number;
          access: public
        end

        Entity ComputedData(BaseData)
          attributes:
            - sum: number = BaseData.value1 + BaseData.value2;
            - product: number = BaseData.value1 * BaseData.value2;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Composite entity should have computed fields
        assert "class ComputedData(BaseModel):" in generated_code
        assert "sum:" in generated_code
        assert "product:" in generated_code

    def _extract_class_section(self, code, class_name):
        """Extract the content of a specific class from generated code."""
        pattern = rf'class {class_name}\([^)]+\):.*?(?=\nclass |\Z)'
        match = re.search(pattern, code, re.DOTALL)
        return match.group(0) if match else ""


class TestSchemaGeneration:
    """Test Create/Update schema generation."""

    def test_create_and_update_schemas_generated(self, temp_output_dir):
        """Test that Create and Update schemas are generated for entities with sources."""
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

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check all three schemas exist
        assert "class Data(BaseModel):" in generated_code
        assert "class DataCreate(BaseModel):" in generated_code
        assert "class DataUpdate(BaseModel):" in generated_code

    def test_schema_only_entity_no_create_update(self, temp_output_dir):
        """Test that schema-only entities don't generate Create/Update schemas."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity NestedType
          attributes:
            - field1: string;
            - field2: integer;
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - id: integer;
            - nested: object<NestedType>;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # NestedType should be generated as a schema-only entity
        assert "class NestedType(BaseModel):" in generated_code
        assert "class NestedTypeCreate" not in generated_code
        assert "class NestedTypeUpdate" not in generated_code

        # Data should be generated (Create/Update depend on full pipeline)
        assert "class Data(BaseModel):" in generated_code


class TestModelImports:
    """Test that generated models have correct imports."""

    def test_pydantic_imports(self, temp_output_dir):
        """Test that Pydantic imports are correctly generated."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Data
          attributes:
            - id: integer;
            - value: string;
        end

        Source<REST> ContainerAPI
          url: "http://test/containers"
          operations: [read]
        end

        Entity Container
          source: ContainerAPI
          attributes:
            - items: array<Data>;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check for essential imports
        assert "from pydantic import" in generated_code
        assert "BaseModel" in generated_code

    def test_typing_imports_for_complex_types(self, temp_output_dir):
        """Test that typing imports are added for complex types."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - value: string;
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Data
          source: DataAPI
          attributes:
            - items: array<Item>;
            - optional_value: string?;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        generate_domain_models(model, templates_dir, temp_output_dir)

        models_file = temp_output_dir / "app" / "domain" / "models.py"
        generated_code = models_file.read_text()

        # Check for typing imports
        assert "from typing import" in generated_code
        # Should have List and Optional (or their equivalents)
        assert any(x in generated_code for x in ["List", "list", "Optional"])
