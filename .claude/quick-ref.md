# Quick Reference Commands

## Code Generation

### Generate from FDSL file
```bash
./venv_WIN/Scripts/fdsl.exe generate examples/medium/demo_loud_chat.fdsl --out test_gen
```

### Validate FDSL file
```bash
./venv_WIN/Scripts/fdsl.exe validate examples/medium/demo_loud_chat.fdsl
```

### Generate with specific output
```bash
./venv_WIN/Scripts/fdsl.exe generate <file>.fdsl --out <output_dir>
```

## Running Generated Code

### Docker (recommended)
```bash
cd test_gen
docker compose up --build
```

### Manual (requires Python dependencies)
```bash
cd test_gen
python -m uvicorn app.main:app --reload --port 8080
```

## Testing

### Run echo server
```bash
cd examples/services/dummywss
python3 ws_auth_echo.py
```

### Test WebSocket with wscat
```bash
wscat -c ws://localhost:8080/api/chat
```

### Test REST endpoint
```bash
curl http://localhost:8080/api/products
```

## Code Inspection

### Check generated chains
```bash
grep -A 20 "_COMPILED_CHAIN" test_gen/app/services/*_service.py
```

### Check external targets
```bash
grep -A 10 "_EXTERNAL_TARGETS" test_gen/app/services/*_service.py
```

### Validate Python syntax
```bash
python -m py_compile test_gen/app/api/routers/*.py
```

### Find entity definition
```bash
grep -n "^Entity <name>" examples/**/*.fdsl
```

### Find all WebSocket endpoints
```bash
grep -n "APIEndpoint<WS>" examples/**/*.fdsl
```

## Development

### Watch for file changes (if using nodemon)
```bash
nodemon --watch examples --ext fdsl --exec "./venv_WIN/Scripts/fdsl.exe generate examples/medium/demo_loud_chat.fdsl --out test_gen"
```

### Run Python REPL with generated models
```bash
cd test_gen
python -c "from app.domain.models import *; import json; print(json.dumps(Product.model_json_schema(), indent=2))"
```

### Check logs in Docker
```bash
docker compose logs -f backend
```

## Common Patterns

### Find all entities in a file
```bash
grep "^Entity " examples/medium/demo_loud_chat.fdsl
```

### Find parent entities
```bash
grep "Entity .*(.*)" examples/medium/demo_loud_chat.fdsl
```

### Find WebSocket sources
```bash
grep -A 5 "Source<WS>" examples/**/*.fdsl
```

### Check subscribe/publish schemas
```bash
grep -E "(subscribe|publish):" examples/medium/demo_loud_chat.fdsl
```
