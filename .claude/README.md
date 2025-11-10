# Claude Code Configuration for FDSL Project

This directory contains Claude Code configuration to improve development efficiency.

## Structure

```
.claude/
├── commands/           # Slash commands for common tasks
│   ├── gen.md         # Generate code from FDSL
│   ├── validate.md    # Validate FDSL syntax
│   ├── trace-entity.md # Trace entity dependencies
│   └── test-ws.md     # Test WebSocket endpoints
├── context/           # Reference documentation
│   └── ws-patterns.md # Common WebSocket patterns
├── tasks/             # Task checklists and workflows
│   └── debug-websocket.md # WebSocket debugging guide
├── glossary.md        # Project terminology
├── paths.md           # Key file locations
├── quick-ref.md       # Common commands reference
├── session-notes.md   # Session history and decisions
├── settings.json      # Claude Code settings
└── README.md          # This file
```

## Slash Commands

Type these in chat to execute common workflows:

- `/gen <fdsl_file> [output_dir]` - Generate code from FDSL file
- `/validate <fdsl_file>` - Validate FDSL syntax and semantics
- `/trace-entity <entity_name> [fdsl_file]` - Trace entity dependencies
- `/test-ws <endpoint_name> [fdsl_file]` - Test WebSocket endpoint

## Quick Reference Files

**Always available in context**:
- `glossary.md` - Project terminology and definitions
- `paths.md` - Key file locations in the codebase

**Reference when needed**:
- `quick-ref.md` - Common bash commands
- `ws-patterns.md` - WebSocket implementation patterns
- `session-notes.md` - Historical decisions and session summaries

## Debugging Workflows

See `tasks/debug-websocket.md` for comprehensive WebSocket debugging checklist.

## Settings

The `settings.json` file configures:
- **Hooks**: Auto-validate Python syntax after edits
- **Context**: Always include glossary and paths
- **Search**: Exclude generated code and virtual environments
- **Preferences**: Code style and file reference format

## Benefits

- **Token efficiency**: Reference docs instead of re-explaining
- **Faster workflows**: Slash commands for common tasks
- **Consistent terminology**: Shared glossary
- **Session continuity**: Historical notes prevent re-explaining decisions
- **Quick debugging**: Checklists and common patterns

## Maintenance

Update `session-notes.md` after significant changes or debugging sessions.
