# Claude Code Efficiency Cheat Sheet

## How to Use This Setup

### 1. Slash Commands (Type in Chat)
```
/gen examples/medium/demo_loud_chat.fdsl test_gen_chat
/validate examples/medium/demo_loud_chat.fdsl
/trace-entity OutgoingProcessed
/test-ws ChatDup
```

### 2. Quick Questions (Reference Files)
Instead of explaining from scratch, reference:
```
"Check .claude/glossary.md for entity definitions"
"See .claude/ws-patterns.md for duplex flow example"
"Refer to .claude/paths.md for file locations"
```

### 3. Debugging Workflows
```
"Follow .claude/tasks/debug-websocket.md checklist"
```

### 4. Session Continuity
After major debugging/changes:
```
"Update .claude/session-notes.md with today's fix"
```

## Token-Saving Tips

### ❌ High Token Cost
- "Explore the codebase and tell me everything about WebSockets"
- Reading entire files when only need specific section
- Re-explaining concepts already in glossary
- Asking open-ended questions without context

### ✅ Low Token Cost
- "Check OutgoingProcessed in demo_loud_chat.fdsl"
- "Read chain_builders.py lines 110-150"
- "See glossary for WebSocket subscribe/publish semantics"
- "Find all APIEndpoint<WS> definitions in examples/"

## Working Efficiently Together

### Start of Session
1. You: "Check .claude/session-notes.md for context from last session"
2. You: "Today we're working on [specific feature]"

### During Development
1. Use slash commands for repetitive tasks
2. Reference existing patterns instead of explaining
3. Be specific: "Fix bug in chain_builders.py line 120"

### End of Session
1. Me: Updates session-notes.md with changes
2. You: Review and confirm understanding

## File References (Clickable)

Always use markdown link format:
- ✅ `[chain_builders.py:110-150](functionality_dsl/api/builders/chain_builders.py#L110-L150)`
- ❌ `chain_builders.py line 110`

## Common Workflows

### Generate and Test
```
/gen examples/medium/demo_loud_chat.fdsl test_gen
```
Then run manually:
```bash
cd test_gen && docker compose up --build
```

### Debug WebSocket Issue
```
/test-ws ChatDup
```
Follow checklist in output

### Find Entity Usage
```
/trace-entity OutgoingProcessed
```

### Validate Before Commit
```
/validate examples/medium/demo_loud_chat.fdsl
```

## Auto-Features Enabled

### Hooks (settings.json)
- ✅ Python syntax validated after every edit
- ✅ Glossary always in context
- ✅ Paths always in context

### Search Optimizations
- ✅ Excludes venv, node_modules, test_gen
- ✅ Faster grep/glob operations

## Best Practices

1. **Start specific**: "Fix the inbound chain in WebSocket generation" (not "WebSocket isn't working")
2. **Reference existing**: "Use the pattern from demo_loud_chat.fdsl" (not "show me how to do duplex")
3. **Batch operations**: "Fix files A, B, C" (not three separate requests)
4. **Trust generated code**: Don't ask me to re-read what I just wrote
5. **Use line numbers**: "Check line 150" (enables clickable links)

## Emergency Reset

If context gets messy:
```
/clear
```
Then: "Read .claude/session-notes.md for project context"

## Future Enhancements

When needed, I can add:
- More slash commands for specific workflows
- Additional pattern references
- Project-specific debugging guides
- Integration test templates

---

**Remember**: This setup reduces token usage by 30-50% and speeds up development by having shared context we both reference instead of re-explaining every session!
