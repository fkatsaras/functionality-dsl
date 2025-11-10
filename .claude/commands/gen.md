---
description: Generate code from FDSL file
---

Generate FastAPI backend from the FDSL file.

Usage: /gen <fdsl_file> [output_dir]

Example: /gen examples/medium/demo_loud_chat.fdsl test_gen_chat

Steps:
1. Generate code using fdsl CLI
2. Validate the generated Python code compiles
3. Report any issues found
4. Show key generated files (routers, services)
