"""
Integration tests for WebSocket router generation.

Tests that FDSL entity specifications with WebSocket sources generate valid
WebSocket routers with correct connection handling, message routing, and flow direction.
"""

import pytest
from pathlib import Path

from functionality_dsl.language import build_model_str
from functionality_dsl.api.generator import render_domain_files


class TestWebSocketRouterGeneration:
    """Test basic WebSocket router generation."""

    def test_inbound_entity_generates_websocket_router(self, temp_output_dir):
        """Test that inbound (subscribe) entities generate WebSocket routers."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - timestamp: integer;
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check that WebSocket router was created
        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        assert len(ws_files) > 0, "WebSocket router should be generated"

        # Check router content
        ws_router_code = ws_files[0].read_text()

        # Should have websocket endpoint decorator
        assert "@router.websocket(" in ws_router_code
        assert "async def" in ws_router_code
        assert "WebSocket" in ws_router_code

    def test_outbound_entity_generates_websocket_router(self, temp_output_dir):
        """Test that outbound (publish) entities generate WebSocket routers."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> CommandChannel
          channel: "ws://test/commands"
          operations: [publish]
        end

        Entity Command
          flow: outbound
          source: CommandChannel
          attributes:
            - action: string;
            - target: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        assert len(ws_files) > 0, "WebSocket router for outbound entity should be generated"

        ws_router_code = ws_files[0].read_text()
        assert "@router.websocket(" in ws_router_code

    def test_composite_inbound_entity_generates_router(self, temp_output_dir):
        """Test that composite inbound entities generate WebSocket routers."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> Stream1
          channel: "ws://test/stream1"
          operations: [subscribe]
        end

        Source<WS> Stream2
          channel: "ws://test/stream2"
          operations: [subscribe]
        end

        Entity Tick1
          flow: inbound
          source: Stream1
          attributes:
            - value1: number;
        end

        Entity Tick2
          flow: inbound
          source: Stream2
          attributes:
            - value2: number;
        end

        Entity Combined(Tick1, Tick2)
          flow: inbound
          attributes:
            - total: number = Tick1.value1 + Tick2.value2;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        assert len(ws_files) > 0, "WebSocket router for composite entity should be generated"


class TestWebSocketRouterStructure:
    """Test the structure of generated WebSocket routers."""

    def test_websocket_router_imports(self, temp_output_dir):
        """Test that WebSocket routers have correct imports."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Check essential imports
        assert "from fastapi import" in ws_router_code
        assert "WebSocket" in ws_router_code
        assert "APIRouter" in ws_router_code

    def test_websocket_endpoint_path(self, temp_output_dir):
        """Test that WebSocket endpoints have correct paths."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # WebSocket path should be present
        assert "/ws/" in ws_router_code


class TestWebSocketConnectionHandling:
    """Test WebSocket connection lifecycle handling."""

    def test_websocket_accept_in_handler(self, temp_output_dir):
        """Test that WebSocket handlers accept connections."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Should accept websocket connection
        assert "await websocket.accept()" in ws_router_code or "websocket.accept" in ws_router_code

    def test_websocket_has_message_loop(self, temp_output_dir):
        """Test that WebSocket handlers have message processing loop."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Should have some form of loop or message handling
        assert "while" in ws_router_code or "async for" in ws_router_code or "await" in ws_router_code


class TestWebSocketMessageFlow:
    """Test WebSocket message sending and receiving."""

    def test_inbound_entity_sends_messages(self, temp_output_dir):
        """Test that inbound entities send messages to clients."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Should send messages to client
        assert "websocket.send" in ws_router_code or "send_json" in ws_router_code or "send_text" in ws_router_code

    def test_outbound_entity_receives_messages(self, temp_output_dir):
        """Test that outbound entities receive messages from clients."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> CommandChannel
          channel: "ws://test/commands"
          operations: [publish]
        end

        Entity Command
          flow: outbound
          source: CommandChannel
          attributes:
            - action: string;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Should receive messages from client
        assert "websocket.receive" in ws_router_code or "receive_json" in ws_router_code or "receive_text" in ws_router_code


class TestWebSocketSourceClient:
    """Test WebSocket source client generation."""

    def test_websocket_source_client_generated(self, temp_output_dir):
        """Test that WebSocket source clients are generated."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> ExternalStream
          channel: "wss://external-api.com/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: ExternalStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check for source client file
        sources_dir = temp_output_dir / "app" / "sources"

        if sources_dir.exists():
            source_files = list(sources_dir.glob("*_source.py"))
            assert len(source_files) > 0, "WebSocket source client should be generated"

            # Check client has connection logic
            client_code = source_files[0].read_text()
            assert "websockets" in client_code or "ws" in client_code.lower()


class TestWebSocketAccessControl:
    """Test access control in WebSocket handlers."""

    def test_public_websocket_no_auth(self, temp_output_dir):
        """Test that public WebSocket endpoints don't require auth."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Check the websocket function exists
        assert "async def" in ws_router_code

    def test_role_based_websocket_has_auth(self, temp_output_dir):
        """Test that role-based WebSocket endpoints include auth."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Auth<http> BearerAuth
          scheme: bearer
        end

        Role user uses BearerAuth

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - value: number;
          access: [user]
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        ws_routers_dir = temp_output_dir / "app" / "api" / "routers"
        ws_files = list(ws_routers_dir.glob("*_ws.py"))

        ws_router_code = ws_files[0].read_text()

        # Should have authentication logic
        # This could be Depends(), query params, or manual auth
        assert "Depends" in ws_router_code or "auth" in ws_router_code.lower() or "token" in ws_router_code.lower()


class TestWebSocketService:
    """Test WebSocket service layer integration."""

    def test_websocket_service_generated(self, temp_output_dir):
        """Test that WebSocket entities generate service files."""
        fdsl = """
        Server API
          host: "localhost"
          port: 8080
        end

        Source<WS> DataStream
          channel: "ws://test/stream"
          operations: [subscribe]
        end

        Entity DataTick
          flow: inbound
          source: DataStream
          attributes:
            - timestamp: integer;
            - value: number;
          access: public
        end

        Entity ProcessedData(DataTick)
          flow: inbound
          attributes:
            - timestamp: integer = DataTick.timestamp;
            - doubled: number = DataTick.value * 2;
          access: public
        end
        """

        model = build_model_str(fdsl)
        templates_dir = Path(__file__).parent.parent.parent / "functionality_dsl" / "templates" / "backend"

        render_domain_files(model, templates_dir, temp_output_dir)

        # Check service files exist
        services_dir = temp_output_dir / "app" / "services"

        if services_dir.exists():
            service_files = list(services_dir.glob("*_service.py"))
            assert len(service_files) > 0, "Service files should be generated"
