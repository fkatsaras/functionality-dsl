# WebSocket Debugging Checklist

## 1. Verify Entity Chain Completeness

### Inbound Chain (Client → External)
- [ ] Chain has all transformation steps
- [ ] Wrapper entity exists for primitive values
- [ ] Terminal entity identified (sent to external)
- [ ] All parent entities included in chain

**Check generated code**:
```bash
grep -A 30 "_COMPILED_CHAIN_INBOUND" test_gen/app/services/*_service.py
```

**Expected**: Should see all entities from APIEndpoint.publish to Source.publish

---

### Outbound Chain (External → Client)
- [ ] Chain has all transformation steps
- [ ] Source.subscribe entity exists
- [ ] APIEndpoint.subscribe entity exists
- [ ] All transformations between them included

**Check generated code**:
```bash
grep -A 30 "_COMPILED_CHAIN_OUTBOUND" test_gen/app/services/*_service.py
```

---

## 2. Verify External Targets Configuration

- [ ] External WS Source defined in FDSL
- [ ] Source has `channel:` field (not `path:`)
- [ ] Source.publish schema matches terminal entity
- [ ] Source.subscribe schema matches expected response

**Check generated code**:
```bash
grep -A 10 "_EXTERNAL_TARGETS" test_gen/app/services/*_service.py
```

**Expected**: Should have URL, headers, protocol configuration

---

## 3. Check Subscribe/Publish Semantics

### APIEndpoint<WS>
- [ ] `subscribe:` schema = what clients RECEIVE (outbound from server)
- [ ] `publish:` schema = what clients SEND (inbound to server)

### Source<WS>
- [ ] `subscribe:` schema = what we RECEIVE FROM external
- [ ] `publish:` schema = what we SEND TO external

**Verify**: Trace data flow matches intended direction

---

## 4. Generated Code Validation

### Router File
- [ ] Inbound loop uses `chain_inbound`
- [ ] Outbound loop uses `chain_outbound`
- [ ] WebSocket connection handler exists
- [ ] Bus subscriptions configured correctly

**Check**:
```bash
cat test_gen/app/api/routers/<endpoint>.py
```

---

### Service File
- [ ] `_EXTERNAL_TARGETS` populated
- [ ] `_COMPILED_CHAIN_INBOUND` complete
- [ ] `_COMPILED_CHAIN_OUTBOUND` complete
- [ ] Wrapper entity has `__WRAP_PAYLOAD__` marker

**Check**:
```bash
cat test_gen/app/services/<endpoint>_service.py
```

---

## 5. Runtime Verification

### External Service
- [ ] External server is running
- [ ] Listening on correct host/port
- [ ] Accepts WebSocket connections
- [ ] Echoes/transforms messages as expected

**Test external directly**:
```bash
wscat -c ws://localhost:8765
```

---

### Backend Connection
- [ ] Backend attempts to connect to external
- [ ] No connection errors in logs
- [ ] Persistent connection maintained
- [ ] Reader task started for external source

**Check logs**:
```bash
docker compose logs -f backend | grep TARGET
```

---

### End-to-End Flow
- [ ] Client can connect to APIEndpoint
- [ ] Client messages reach inbound chain
- [ ] Inbound chain computation completes
- [ ] Messages forwarded to external service
- [ ] External responses received
- [ ] Outbound chain computation completes
- [ ] Responses sent to client

**Test manually**:
```bash
wscat -c ws://localhost:8080/api/chat
> hello
< {"text": "hello"}
```

---

## 6. Common Issues & Fixes

### Issue: Inbound chain incomplete
**Symptoms**: Chain has 1 step instead of expected 2+
**Check**: Terminal entity finding logic
**Fix**: Verify descendant entity connects to Source.publish

---

### Issue: External targets empty
**Symptoms**: `_EXTERNAL_TARGETS = []`
**Check**: Source.publish schema matches terminal entity name
**Fix**: Ensure schema entity name exact match (case-sensitive)

---

### Issue: Wrapper not auto-wrapping
**Symptoms**: Primitive values not wrapped in dictionary
**Check**: Wrapper entity has expression (should not)
**Fix**: Remove expression, make it pure schema entity

---

### Issue: Connection to external fails
**Symptoms**: "Failed to connect" errors
**Check**: External service running, URL correct
**Fix**: Start external service, verify host/port, check Docker networking

---

### Issue: Messages not reaching client
**Symptoms**: Backend logs show computation but client receives nothing
**Check**: Bus subscription, outbound loop
**Fix**: Verify bus topic matches, check WebSocket send logic

---

## Debug Commands

### Enable debug logging
Set `loglevel: debug` in Server block of FDSL file

### Trace entity computation
```bash
docker compose logs -f backend | grep COMPUTE
```

### Monitor WebSocket connections
```bash
docker compose logs -f backend | grep websockets
```

### Check bus messages
```bash
docker compose logs -f backend | grep BUS
```

### Inspect generated chain
```python
cd test_gen
python -c "from app.services.<endpoint>_service import _COMPILED_CHAIN_INBOUND; import json; print(json.dumps(_COMPILED_CHAIN_INBOUND, indent=2))"
```
