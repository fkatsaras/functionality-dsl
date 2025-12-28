# WebSocket Patterns - Testing Guide

## Prerequisites

Install `wscat` globally (for WebSocket testing):

```bash
npm install -g wscat
```

Or with NVM:
```bash
nvm install node
npm install -g wscat
```

Verify installation:
```bash
which wscat
wscat --version
```

## Quick Start

### Test All Patterns Automatically

```bash
cd examples/v2/ws-patterns
make test-all
```

This will:
1. Generate code for each pattern
2. Start Docker containers
3. Test with wscat
4. Report results
5. Cleanup automatically
6. **Stop on first failure**

### Test a Specific Pattern

```bash
make test-pattern EXAMPLE=01-subscribe-simple
```

### Manual Testing (Interactive)

```bash
# 1. Generate code
make gen EXAMPLE=05-bidirectional-simple OUTPUT=test

# 2. Start dummy service
cd dummy-service && docker compose -p thesis up -d && cd ..

# 3. Start generated FDSL service
cd test && docker compose -p thesis up -d && cd ..

# 4. Test with wscat
wscat -c ws://localhost:8000/ws/chatmessage

# Send messages:
> {"text":"Hello world","user":"Alice"}

# 5. Cleanup when done
bash ../../../scripts/docker_cleanup.sh
rm -rf test/
```

## Pattern Testing Details

### Pattern 1: Subscribe (Simple)
```bash
# Receives messages from external WS
wscat -c ws://localhost:8000/ws/messagefromexternal

# Should see messages every 2 seconds
```

### Pattern 2: Subscribe (Transformed)
```bash
# Receives transformed messages
wscat -c ws://localhost:8000/ws/processedmessage

# Should see uppercased text and size in KB
```

### Pattern 3: Publish (Simple)
```bash
# Send commands to external WS
echo '{"command":"test","value":123}' | wscat -c ws://localhost:8000/ws/commandtoexternal

# Should see confirmation response
```

### Pattern 4: Publish (Transformed)
```bash
# Send user commands (transformed before external WS)
echo '{"action":"reset","value":5}' | wscat -c ws://localhost:8000/ws/usercommand

# Check dummy service logs to see transformed command
```

### Pattern 5: Bidirectional (Simple)
```bash
# Chat/echo server
wscat -c ws://localhost:8000/ws/chatmessage

# Send message:
> {"text":"Hello","user":"Alice"}

# Should echo back to all connected clients
```

### Pattern 6: Bidirectional (Separate)
```bash
# Terminal 1: Subscribe to telemetry
wscat -c ws://localhost:8000/ws/processedtelemetry

# Should see temperature data every 2 seconds (with Celsius and Fahrenheit)

# Terminal 2: Publish commands
echo '{"action":"reset","value":25}' | wscat -c ws://localhost:8000/ws/devicecommand
```

## Troubleshooting

### wscat not found

```bash
# Check if installed
which wscat

# Install globally
npm install -g wscat

# Or add to PATH if using NVM
export PATH="$HOME/.nvm/versions/node/$(nvm current)/bin:$PATH"
```

### Port already in use

```bash
# Cleanup all containers
bash ../../../scripts/docker_cleanup.sh

# Check ports
docker ps -a
netstat -an | grep 8000
netstat -an | grep 9200
```

### Generation fails

```bash
# Check FDSL syntax
../../../venv_WIN/Scripts/fdsl validate <pattern>.fdsl

# View detailed errors
../../../venv_WIN/Scripts/fdsl generate <pattern>.fdsl --out test 2>&1 | less
```

### Docker network issues

```bash
# Create network if missing
docker network create thesis_fdsl_net

# Inspect network
docker network inspect thesis_fdsl_net
```

## CI/CD Integration

For automated testing in CI/CD pipelines:

```bash
#!/bin/bash
set -e

# Run all pattern tests
cd examples/v2/ws-patterns
make test-all

# Exit code 0 = all passed
# Exit code 1 = at least one failed
```

## Manual Verification Checklist

Before thesis defense, verify each pattern:

- [ ] Pattern 1: Subscribe simple - receives messages
- [ ] Pattern 2: Subscribe transformed - data is transformed correctly
- [ ] Pattern 3: Publish simple - commands sent successfully
- [ ] Pattern 4: Publish transformed - transformation applied before send
- [ ] Pattern 5: Bidirectional simple - echo works both ways
- [ ] Pattern 6: Bidirectional separate - telemetry + commands work independently

## Debugging

### View dummy service logs
```bash
docker logs dummy-ws-patterns -f
```

### View generated service logs
```bash
docker logs <generated-service-name> -f
```

### Check WebSocket connectivity
```bash
# Test dummy service directly
wscat -c ws://localhost:9200/stream

# Test FDSL service
wscat -c ws://localhost:8000/ws/<entity-name>
```

### Inspect generated code
```bash
cd generated-<pattern>/app/api/websocket/
cat routers/<entity>_ws.py
```
