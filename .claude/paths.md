# Key File Locations

## DSL Files
- **Examples**: `examples/{simple,medium,advanced}/`
- **Grammar**: `functionality_dsl/grammar/`
  - `entity.tx` - Entity and type definitions
  - `component.tx` - UI component definitions
- **Tests**: `examples/tests/`

## Code Generation
- **Generators**: `functionality_dsl/api/generators/`
  - `rest_generator.py` - REST endpoint generation
  - `websocket_generator.py` - WebSocket endpoint generation
  - `model_generator.py` - Pydantic model generation
- **Builders**: `functionality_dsl/api/builders/`
  - `chain_builders.py` - Entity computation chains
  - `config_builders.py` - External targets, WS inputs
- **Extractors**: `functionality_dsl/api/extractors/`
  - `model_extractor.py` - Extract entities, sources, endpoints
  - `schema_extractor.py` - Extract request/response schemas
- **Templates**: `functionality_dsl/templates/backend/`
  - `router_rest.jinja` - REST router template
  - `router_ws.jinja` - WebSocket router template
  - `service_ws.jinja` - WebSocket service template

## Generated Code (in test_gen/)
- **Routers**: `app/api/routers/*.py` - One file per endpoint
- **Services**: `app/services/*_service.py` - Business logic
- **Models**: `app/domain/models.py` - Pydantic models
- **Core**: `app/core/` - Runtime utilities (safe_eval, builtins)

## Testing & Services
- **Echo server**: `examples/services/dummywss/ws_auth_echo.py`
- **Docker**: `test_gen/docker-compose.yml`
- **Base frontend**: `functionality_dsl/base/frontend/`

## Configuration
- **Main entry**: `functionality_dsl/cli.py`
- **Language**: `functionality_dsl/language.py`
- **Builtins**: `functionality_dsl/lib/builtins/`
- **Compiler**: `functionality_dsl/lib/compiler/expr_compiler.py`
