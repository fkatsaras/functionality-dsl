---
description: Validate FDSL file syntax and semantics
---

Validate the FDSL file for syntax and semantic errors.

Usage: /validate <fdsl_file>

Example: /validate examples/medium/demo_loud_chat.fdsl

Checks:
1. Grammar/syntax using the TextX parser
2. Entity references exist
3. Type consistency
4. Parameter name matching
5. WebSocket subscribe/publish schema consistency
6. Unused entities (optional warning)
