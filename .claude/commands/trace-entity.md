---
description: Trace entity dependencies and data flow
---

Trace an entity's dependencies and usage throughout the codebase.

Usage: /trace-entity <entity_name> [fdsl_file]

Example: /trace-entity OutgoingProcessed examples/medium/demo_loud_chat.fdsl

Output:
1. Parent entities it depends on (inheritance)
2. Child entities that use it
3. Which Source provides it (if any)
4. Which APIEndpoint exposes it (if any)
5. Full transformation chain (ancestors → entity → descendants)
6. Whether it's a terminal entity
