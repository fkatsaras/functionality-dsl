---
description: Test WebSocket endpoint end-to-end
---

Test a WebSocket endpoint with the echo server.

Usage: /test-ws <endpoint_name> [fdsl_file]

Example: /test-ws ChatDup examples/medium/demo_loud_chat.fdsl

Steps:
1. Verify echo server is available (examples/services/dummywss/ws_auth_echo.py)
2. Check generated backend code exists
3. Verify entity chains are complete
4. Show external targets configuration
5. Provide test commands for manual verification
