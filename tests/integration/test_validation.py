"""
Integration tests for FDSL validation.

Tests validation of all FDSL test files, ensuring pass tests pass and fail tests fail.
"""

import pytest
from pathlib import Path
from functionality_dsl.language import build_model


class TestValidationPassTests:
    """Test that all *-pass.fdsl files validate successfully."""

    @pytest.fixture(scope="class")
    def pass_test_files(self, tests_dir):
        """Collect all -pass.fdsl test files."""
        validation_dir = tests_dir / "validation"
        if not validation_dir.exists():
            return []
        return list(validation_dir.rglob("*-pass.fdsl"))

    def test_all_pass_files_validate(self, pass_test_files):
        """Test that all pass test files validate successfully."""
        if not pass_test_files:
            pytest.skip("No -pass.fdsl test files found")

        failures = []
        for file_path in pass_test_files:
            try:
                build_model(str(file_path))
            except Exception as e:
                failures.append((file_path.name, str(e)))

        if failures:
            error_msg = "\n".join([f"{name}: {error}" for name, error in failures])
            pytest.fail(f"The following pass tests failed validation:\n{error_msg}")

    def test_individual_pass_files(self, pass_test_files):
        """Test each pass file individually for better error reporting."""
        if not pass_test_files:
            pytest.skip("No -pass.fdsl test files found")

        for file_path in pass_test_files:
            with pytest.raises(Exception) as exc_info:
                build_model(str(file_path))
                # If we get here, the test passed (no exception raised)
                # This is what we want for -pass.fdsl files
                assert True
                raise Exception("Test passed successfully")

            # Only fail if it's NOT our success marker
            if "Test passed successfully" not in str(exc_info.value):
                pytest.fail(f"{file_path.name} should pass but failed: {exc_info.value}")


class TestValidationFailTests:
    """Test that all *-fail.fdsl files fail validation as expected."""

    @pytest.fixture(scope="class")
    def fail_test_files(self, tests_dir):
        """Collect all -fail.fdsl test files."""
        validation_dir = tests_dir / "validation"
        if not validation_dir.exists():
            return []
        return list(validation_dir.rglob("*-fail.fdsl"))

    def test_all_fail_files_reject(self, fail_test_files):
        """Test that all fail test files are rejected during validation."""
        if not fail_test_files:
            pytest.skip("No -fail.fdsl test files found")

        unexpected_passes = []
        for file_path in fail_test_files:
            try:
                build_model(str(file_path))
                # If we get here, validation passed when it should have failed
                unexpected_passes.append(file_path.name)
            except Exception:
                # Expected: validation should fail
                pass

        if unexpected_passes:
            pytest.fail(
                f"The following fail tests unexpectedly passed validation:\n"
                + "\n".join(unexpected_passes)
            )


class TestExampleValidation:
    """Test that all example FDSL files validate successfully."""

    @pytest.fixture(scope="class")
    def example_files(self, examples_dir):
        """Collect all example FDSL files."""
        if not examples_dir.exists():
            return []
        return list(examples_dir.rglob("*.fdsl"))

    def test_all_examples_validate(self, example_files):
        """Test that all examples validate successfully."""
        if not example_files:
            pytest.skip("No example files found")

        failures = []
        for file_path in example_files:
            try:
                build_model(str(file_path))
            except Exception as e:
                failures.append((str(file_path.relative_to(file_path.parent.parent)), str(e)))

        if failures:
            error_msg = "\n".join([f"{name}:\n  {error}" for name, error in failures])
            pytest.fail(f"The following examples failed validation:\n{error_msg}")


class TestSpecificValidationRules:
    """Test specific validation rules with inline FDSL."""

    def test_orphan_entity_rejected(self, write_fdsl_file):
        """Test that orphan entities are rejected."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity OrphanEntity
  attributes:
    - name: string;
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: OrphanEntity
end
"""
        file_path = write_fdsl_file(fdsl_content)

        with pytest.raises(Exception) as exc_info:
            build_model(str(file_path))

        # Verify error message mentions the orphan entity issue
        error_msg = str(exc_info.value).lower()
        assert "orphan" in error_msg or "not sourced" in error_msg or "source" in error_msg

    def test_missing_source_url_rejected(self, write_fdsl_file):
        """Test that Source<REST> without URL is rejected."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> BadSource
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)

        with pytest.raises(Exception) as exc_info:
            build_model(str(file_path))

        error_msg = str(exc_info.value).lower()
        assert "url" in error_msg

    def test_invalid_endpoint_method_rejected(self, write_fdsl_file):
        """Test that invalid HTTP method is rejected."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity Data
  attributes:
    - value: string;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: object
    entity: Data
end

Endpoint<REST> GetData
  path: "/data"
  method: INVALID
  response:
    type: object
    entity: Data
end
"""
        file_path = write_fdsl_file(fdsl_content)

        with pytest.raises(Exception):
            build_model(str(file_path))

    def test_type_array_multi_attr_rejected(self, write_fdsl_file):
        """Test that type=array with multi-attribute entity is rejected."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity MultiAttr
  attributes:
    - items: array;
    - count: integer;
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: array
    entity: MultiAttr
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: array
    entity: MultiAttr
end
"""
        file_path = write_fdsl_file(fdsl_content)

        with pytest.raises(Exception) as exc_info:
            build_model(str(file_path))

        error_msg = str(exc_info.value).lower()
        assert "array" in error_msg or "single attribute" in error_msg or "wrapper" in error_msg

    def test_valid_computed_entity_accepted(self, write_fdsl_file):
        """Test that valid computed entity is accepted."""
        fdsl_content = """
Server TestServer
  host: "localhost"
  port: 8080
end

Entity RawData
  attributes:
    - items: array;
end

Entity ComputedData(RawData)
  attributes:
    - count: integer = len(RawData.items);
end

Source<REST> DataSource
  url: "http://api.example.com/data"
  method: GET
  response:
    type: array
    entity: RawData
end

Endpoint<REST> GetData
  path: "/data"
  method: GET
  response:
    type: object
    entity: ComputedData
end
"""
        file_path = write_fdsl_file(fdsl_content)

        # Should not raise exception
        model = build_model(str(file_path))
        assert model is not None
