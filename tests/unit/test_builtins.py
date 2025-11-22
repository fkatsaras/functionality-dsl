"""
Unit tests for FDSL built-in functions.

Tests all the built-in functions available in FDSL expressions.
"""

import pytest
from datetime import datetime
from functionality_dsl.lib.builtins.registry import DSL_FUNCTION_REGISTRY

# Get functions from registry
map_func = DSL_FUNCTION_REGISTRY.get('map')
filter_func = DSL_FUNCTION_REGISTRY.get('filter')
sum_func = DSL_FUNCTION_REGISTRY.get('sum')
avg_func = DSL_FUNCTION_REGISTRY.get('avg')
get_func = DSL_FUNCTION_REGISTRY.get('get')
len_func = DSL_FUNCTION_REGISTRY.get('len')
type_func = DSL_FUNCTION_REGISTRY.get('toString')  # Using toString as type converter
upper_func = DSL_FUNCTION_REGISTRY.get('upper')
lower_func = DSL_FUNCTION_REGISTRY.get('lower')
split_func = DSL_FUNCTION_REGISTRY.get('split')
join_func = DSL_FUNCTION_REGISTRY.get('join')
replace_func = DSL_FUNCTION_REGISTRY.get('replace')
round_func = DSL_FUNCTION_REGISTRY.get('round')
abs_func = DSL_FUNCTION_REGISTRY.get('abs')
min_func = DSL_FUNCTION_REGISTRY.get('min')
max_func = DSL_FUNCTION_REGISTRY.get('max')
floor_func = DSL_FUNCTION_REGISTRY.get('floor')
ceil_func = DSL_FUNCTION_REGISTRY.get('ceil')
json_parse = DSL_FUNCTION_REGISTRY.get('jsonParse')
json_stringify = DSL_FUNCTION_REGISTRY.get('jsonStringify')
is_email = DSL_FUNCTION_REGISTRY.get('validate_email')
is_url = DSL_FUNCTION_REGISTRY.get('validate_url')
is_uuid = DSL_FUNCTION_REGISTRY.get('validate_uuid')


class TestCollectionFunctions:
    """Test collection manipulation functions."""

    def test_map_func(self):
        """Test map function."""
        data = [1, 2, 3, 4]
        result = map_func(data, lambda x: x * 2)
        assert result == [2, 4, 6, 8]

    def test_map_with_dict(self):
        """Test map on list of dictionaries."""
        data = [{"x": 1}, {"x": 2}, {"x": 3}]
        result = map_func(data, lambda item: item["x"] * 10)
        assert result == [10, 20, 30]

    def test_filter_func(self):
        """Test filter function."""
        data = [1, 2, 3, 4, 5, 6]
        result = filter_func(data, lambda x: x % 2 == 0)
        assert result == [2, 4, 6]

    def test_sum_func(self):
        """Test sum function."""
        assert sum_func([1, 2, 3, 4]) == 10
        assert sum_func([]) == 0
        assert sum_func([5]) == 5

    def test_avg_func(self):
        """Test average function."""
        assert avg_func([1, 2, 3, 4]) == 2.5
        assert avg_func([10]) == 10
        assert avg_func([2, 4, 6, 8]) == 5

    def test_avg_empty_list(self):
        """Test average of empty list."""
        with pytest.raises(ValueError):
            avg_func([])


class TestCoreFunctions:
    """Test core utility functions."""

    def test_get_func_existing_key(self):
        """Test get function with existing key."""
        data = {"name": "Alice", "age": 30}
        assert get_func(data, "name") == "Alice"
        assert get_func(data, "age") == 30

    def test_get_func_missing_key_with_default(self):
        """Test get function with missing key and default."""
        data = {"name": "Alice"}
        assert get_func(data, "email", "default@example.com") == "default@example.com"

    def test_get_func_missing_key_no_default(self):
        """Test get function with missing key and no default."""
        data = {"name": "Alice"}
        assert get_func(data, "email") is None

    def test_get_func_nested_access(self):
        """Test get for nested object access."""
        data = {"user": {"profile": {"name": "Bob"}}}
        assert get_func(data, "user") == {"profile": {"name": "Bob"}}

    def test_len_func(self):
        """Test length function."""
        assert len_func([1, 2, 3]) == 3
        assert len_func("hello") == 5
        assert len_func({}) == 0
        assert len_func([]) == 0

    # Note: type_func not available in registry - skipping type checking test


class TestStringFunctions:
    """Test string manipulation functions."""

    def test_upper_func(self):
        """Test uppercase function."""
        assert upper_func("hello") == "HELLO"
        assert upper_func("Hello World") == "HELLO WORLD"

    def test_lower_func(self):
        """Test lowercase function."""
        assert lower_func("HELLO") == "hello"
        assert lower_func("Hello World") == "hello world"

    def test_split_func(self):
        """Test split function."""
        assert split_func("a,b,c", ",") == ["a", "b", "c"]
        assert split_func("hello world", " ") == ["hello", "world"]
        assert split_func("hello world test", " ") == ["hello", "world", "test"]

    def test_join_func(self):
        """Test join function."""
        assert join_func(["a", "b", "c"], ",") == "a,b,c"
        assert join_func(["hello", "world"], " ") == "hello world"

    def test_replace_func(self):
        """Test replace function."""
        assert replace_func("hello world", "world", "Python") == "hello Python"
        assert replace_func("aaa", "a", "b") == "bbb"


class TestMathFunctions:
    """Test mathematical functions."""

    def test_round_func(self):
        """Test round function."""
        assert round_func(3.14159, 2) == 3.14
        assert round_func(2.5) == 2
        assert round_func(2.7) == 3

    def test_abs_func(self):
        """Test absolute value function."""
        assert abs_func(-5) == 5
        assert abs_func(5) == 5
        assert abs_func(-3.14) == 3.14

    def test_min_func(self):
        """Test minimum function."""
        assert min_func([1, 2, 3, 4]) == 1
        assert min_func([5]) == 5
        assert min_func([-1, -5, -3]) == -5

    def test_max_func(self):
        """Test maximum function."""
        assert max_func([1, 2, 3, 4]) == 4
        assert max_func([5]) == 5
        assert max_func([-1, -5, -3]) == -1

    def test_floor_func(self):
        """Test floor function."""
        assert floor_func(3.7) == 3
        assert floor_func(3.1) == 3
        assert floor_func(-2.5) == -3

    def test_ceil_func(self):
        """Test ceiling function."""
        assert ceil_func(3.1) == 4
        assert ceil_func(3.9) == 4
        assert ceil_func(-2.5) == -2


class TestJSONFunctions:
    """Test JSON parsing and stringification."""

    def test_json_parse(self):
        """Test JSON parsing."""
        result = json_parse('{"name": "Alice", "age": 30}')
        assert result == {"name": "Alice", "age": 30}

    def test_json_parse_array(self):
        """Test JSON parsing of array."""
        result = json_parse('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_stringify(self):
        """Test JSON stringification."""
        data = {"name": "Alice", "age": 30}
        result = json_stringify(data)
        assert "Alice" in result
        assert "30" in result or "age" in result

    def test_json_stringify_array(self):
        """Test JSON stringification of array."""
        data = [1, 2, 3]
        result = json_stringify(data)
        assert "[1" in result or "[1," in result


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_is_email_valid(self):
        """Test email validation with valid emails."""
        assert is_email("test@example.com") is True
        assert is_email("user.name@domain.co.uk") is True

    def test_is_email_invalid(self):
        """Test email validation with invalid emails."""
        assert is_email("notanemail") is False
        assert is_email("@example.com") is False
        assert is_email("test@") is False

    def test_is_url_valid(self):
        """Test URL validation with valid URLs."""
        assert is_url("http://example.com") is True
        assert is_url("https://www.example.com/path") is True

    def test_is_url_invalid(self):
        """Test URL validation with invalid URLs."""
        assert is_url("notaurl") is False
        assert is_url("ftp://example.com") is False

    def test_is_uuid_valid(self):
        """Test UUID validation with valid UUIDs."""
        assert is_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert is_uuid("6ba7b810-9dad-11d1-80b4-00c04fd430c8") is True

    def test_is_uuid_invalid(self):
        """Test UUID validation with invalid UUIDs."""
        assert is_uuid("not-a-uuid") is False
        assert is_uuid("123-456-789") is False
        assert is_uuid("") is False


class TestFunctionChaining:
    """Test chaining multiple functions together."""

    def test_chain_map_and_filter(self):
        """Test chaining map and filter."""
        data = [1, 2, 3, 4, 5, 6]
        doubled = map_func(data, lambda x: x * 2)
        evens = filter_func(doubled, lambda x: x > 5)
        assert evens == [6, 8, 10, 12]

    def test_chain_map_and_sum(self):
        """Test chaining map and sum."""
        data = [{"price": 10}, {"price": 20}, {"price": 30}]
        prices = map_func(data, lambda x: x["price"])
        total = sum_func(prices)
        assert total == 60

    def test_chain_string_operations(self):
        """Test chaining string operations."""
        text = "  HELLO WORLD  "
        result = lower_func(text.strip())
        assert result == "hello world"
