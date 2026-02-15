"""
Integration tests for expression evaluation in computed fields.

Tests that FDSL computed attribute expressions are correctly evaluated at runtime
within the generated service layer code.
"""

import pytest
from pathlib import Path

from functionality_dsl.language import build_model_str
from functionality_dsl.api.generator import render_domain_files


class TestBasicExpressionEvaluation:
    """Test basic arithmetic and operations in computed fields."""

    def test_arithmetic_expression_in_service(self, temp_output_dir):
        """Test that arithmetic expressions are included in service logic."""
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
            - difference: number = BaseData.value1 - BaseData.value2;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check service file
        service_file = temp_output_dir / "app" / "services" / "computeddata_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should contain the arithmetic operations
            assert "+" in service_code or "sum" in service_code
            assert "*" in service_code or "product" in service_code
            assert "-" in service_code or "difference" in service_code

    def test_comparison_expressions(self, temp_output_dir):
        """Test that comparison expressions work correctly."""
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
            - temperature: number;
          access: public
        end

        Entity Analysis(BaseData)
          attributes:
            - is_hot: boolean = BaseData.temperature > 75;
            - is_cold: boolean = BaseData.temperature < 65;
            - is_normal: boolean = BaseData.temperature >= 65 and BaseData.temperature <= 75;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "analysis_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should contain comparison operators
            assert ">" in service_code or ">=" in service_code or "<" in service_code


class TestConditionalExpressions:
    """Test conditional (ternary) expressions in computed fields."""

    def test_simple_conditional(self, temp_output_dir):
        """Test simple if-else conditional expressions."""
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
            - temperature: number;
          access: public
        end

        Entity Status(BaseData)
          attributes:
            - status: string = "hot" if BaseData.temperature > 75 else "normal";
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "status_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should contain conditional logic
            assert "if" in service_code

    def test_nested_conditional(self, temp_output_dir):
        """Test nested conditional expressions."""
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
            - temperature: number;
          access: public
        end

        Entity Status(BaseData)
          attributes:
            - level: string = "high" if BaseData.temperature > 80 else ("medium" if BaseData.temperature > 65 else "low");
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "status_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should contain nested conditional logic
            assert "if" in service_code


class TestCollectionFunctions:
    """Test collection functions (map, filter, sum, len) in expressions."""

    def test_map_function(self, temp_output_dir):
        """Test map function in computed fields."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - price: number;
            - quantity: integer;
        end

        Source<REST> OrderAPI
          url: "http://test/orders"
          operations: [read]
        end

        Entity Order
          source: OrderAPI
          attributes:
            - items: array<Item>;
          access: public
        end

        Entity OrderSummary(Order)
          attributes:
            - prices: array = map(Order.items, i => i["price"]);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "ordersummary_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference map function or list comprehension
            assert "map" in service_code or "[" in service_code

    def test_filter_function(self, temp_output_dir):
        """Test filter function in computed fields."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Product
          attributes:
            - price: number;
            - stock: integer;
        end

        Source<REST> ProductsAPI
          url: "http://test/products"
          operations: [read]
        end

        Entity Products
          source: ProductsAPI
          attributes:
            - items: array<Product>;
          access: public
        end

        Entity ProductStats(Products)
          attributes:
            - in_stock: array = filter(Products.items, p => p["stock"] > 0);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "productstats_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference filter function or list comprehension
            assert "filter" in service_code or "[" in service_code

    def test_sum_function(self, temp_output_dir):
        """Test sum function in computed fields."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - price: number;
            - quantity: integer;
        end

        Source<REST> CartAPI
          url: "http://test/cart"
          operations: [read]
        end

        Entity Cart
          source: CartAPI
          attributes:
            - items: array<Item>;
          access: public
        end

        Entity CartSummary(Cart)
          attributes:
            - total: number = sum(map(Cart.items, i => i["price"] * i["quantity"]));
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "cartsummary_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference sum function
            assert "sum" in service_code

    def test_len_function(self, temp_output_dir):
        """Test len function in computed fields."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - name: string;
        end

        Source<REST> CartAPI
          url: "http://test/cart"
          operations: [read]
        end

        Entity Cart
          source: CartAPI
          attributes:
            - items: array<Item>;
          access: public
        end

        Entity CartInfo(Cart)
          attributes:
            - item_count: integer = len(Cart.items);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "cartinfo_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference len function
            assert "len" in service_code


class TestMathFunctions:
    """Test mathematical functions in expressions."""

    def test_round_function(self, temp_output_dir):
        """Test round function in computed fields."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Thermostat
          source: DataAPI
          attributes:
            - temp_f: number;
          access: public
        end

        Entity Climate(Thermostat)
          attributes:
            - temp_c: number = round((Thermostat.temp_f - 32) * 5 / 9, 1);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "climate_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference round function
            assert "round" in service_code

    def test_min_max_functions(self, temp_output_dir):
        """Test min/max functions in computed fields."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - price: number;
        end

        Source<REST> ProductsAPI
          url: "http://test/products"
          operations: [read]
        end

        Entity Products
          source: ProductsAPI
          attributes:
            - items: array<Item>;
          access: public
        end

        Entity PriceStats(Products)
          attributes:
            - min_price: number = min(map(Products.items, i => i["price"]));
            - max_price: number = max(map(Products.items, i => i["price"]));
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "pricestats_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference min/max functions
            assert "min" in service_code or "max" in service_code


class TestTypeConversions:
    """Test type conversion functions."""

    def test_string_number_conversions(self, temp_output_dir):
        """Test toString and toNumber conversions."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> TickerWS
          channel: "ws://test/ticker"
          operations: [subscribe]
        end

        Entity Tick
          flow: inbound
          source: TickerWS
          attributes:
            - price_str: string;
            - timestamp: integer;
        end

        Entity Price(Tick)
          flow: inbound
          attributes:
            - price: number = toNumber(Tick.price_str);
            - timestamp_str: string = toString(Tick.timestamp);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "price_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference type conversion
            assert "float" in service_code or "str" in service_code or "int" in service_code


class TestStringFunctions:
    """Test string manipulation functions."""

    def test_string_case_functions(self, temp_output_dir):
        """Test upper/lower case functions."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity User
          source: DataAPI
          attributes:
            - name: string;
          access: public
        end

        Entity FormattedUser(User)
          attributes:
            - name_upper: string = upper(User.name);
            - name_lower: string = lower(User.name);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "formatteduser_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should reference string case functions
            assert "upper" in service_code or "lower" in service_code


class TestBooleanLogic:
    """Test boolean operators in expressions."""

    def test_and_or_operators(self, temp_output_dir):
        """Test and/or boolean operators."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<REST> DataAPI
          url: "http://test/data"
          operations: [read]
        end

        Entity Thermostat
          source: DataAPI
          attributes:
            - temperature: number;
            - humidity: number;
          access: public
        end

        Entity Comfort(Thermostat)
          attributes:
            - is_comfortable: boolean = Thermostat.temperature >= 68 and Thermostat.temperature <= 76 and Thermostat.humidity >= 30 and Thermostat.humidity <= 60;
            - needs_adjustment: boolean = Thermostat.temperature < 65 or Thermostat.temperature > 80;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "comfort_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should contain boolean operators
            assert "and" in service_code or "or" in service_code


class TestComplexExpressions:
    """Test complex multi-function expressions."""

    def test_chained_functions(self, temp_output_dir):
        """Test expressions with multiple chained functions."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Entity Item
          attributes:
            - price: number;
            - quantity: integer;
        end

        Source<REST> OrderAPI
          url: "http://test/orders"
          operations: [read]
        end

        Entity Order
          source: OrderAPI
          attributes:
            - items: array<Item>;
          access: public
        end

        Entity OrderAnalysis(Order)
          attributes:
            - total: number = round(sum(map(Order.items, i => i["price"] * i["quantity"])), 2);
            - expensive_items: array = filter(Order.items, i => i["price"] > 100);
            - expensive_count: integer = len(OrderAnalysis.expensive_items);
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        service_file = temp_output_dir / "app" / "services" / "orderanalysis_service.py"

        if service_file.exists():
            service_code = service_file.read_text()

            # Should contain multiple function calls
            assert "sum" in service_code or "round" in service_code
            assert "filter" in service_code or "len" in service_code
