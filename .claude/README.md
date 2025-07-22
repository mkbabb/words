# Claude Code Hooks

Auto-format, type-check, and monitor server health.

## Structure
```
hooks/
├── main-hook.sh          # Orchestrator
├── backend/              # Python: Ruff + MyPy
├── frontend/             # TypeScript/Vue: Prettier + vue-tsc
└── shared/               # Server health + error analysis
```

## Events
- **PreToolUse**: Health checks
- **PostToolUse**: Format, lint, type-check
- **UserPromptSubmit**: Startup health check

## Activation
Set `CLAUDE_HOOKS_CONFIG=.claude/hooks.json` or configure Claude Code to use `hooks.json`.

## Test
```bash
TOOL_NAME=Edit FILE_PATH=/backend/src/file.py bash .claude/hooks/main-hook.sh
```

## Requirements
- Backend: UV, Python 3.12+
- Frontend: Node.js, npm
- Servers: `./dev.sh`