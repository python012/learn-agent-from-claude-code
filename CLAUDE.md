# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an **AI Agent learning repository** with two main components:
1. **Recovered source tree** of Anthropic's Claude Code CLI (`src/`) — read-only architectural reference, no `package.json`, cannot be built locally
2. **Runnable example projects** (`examples/`) — TypeScript and Python SimpleAgent implementations with full build/test support

**Important:** The `src/` directory contains Anthropic's proprietary product (reconstructed from npm source-map leak). Use beyond fair use / your local law is your responsibility. See `AGENTS.md` for detailed code style guidelines extracted from the source.

## Build / Test Commands

### `src/` — Read-only reference (no build possible)

No package.json. Original toolchain (Bun, `bun:bundle`) is required but not available.

### `examples/simple-agent/` — TypeScript SimpleAgent

```bash
npm install                   # Install dependencies
npm run build                 # Build with tsup
npm test                      # Run tests (vitest watch mode)
npm run test:run              # Run tests once
npm run example:basic         # Run basic usage example
npm run example:repl          # Interactive REPL
npm run example:custom-tool   # Custom tool demo
npm run example:multi-agent   # Multi-agent collaboration demo
```

Requires `OPENAI_API_KEY` env var for examples that call the LLM.

### `examples/simple-agent-python/` — Python SimpleAgent

```bash
pip install -r requirements.txt           # Core deps (openai, pydantic)
pip install -r requirements-dev.txt       # Dev deps (pytest, pytest-asyncio)
pytest                                    # Run tests
pytest tests/test_agent.py                # Run single test file
python examples/basic_usage.py            # Basic usage
python examples/multi_agent_collaboration.py  # Multi-agent demo
python examples/mcp_integration.py        # MCP integration demo
```

Requires `OPENAI_API_KEY` env var for LLM examples.

### Documentation site (`docs-site/`)

```bash
pip install mkdocs mkdocs-material && mkdocs serve
```

## Architecture Overview

### `src/` — Claude Code CLI Source (Read-Only Reference)

**Runtime & UI Stack:** Bun + React/Ink (React for CLI). Entry point: `src/main.tsx` (~800KB bundled, Commander-based CLI).

**Core Layers:**

| Layer | Key Files | Purpose |
|-------|-----------|---------|
| Bootstrap | `src/bootstrap/state.ts`, `src/entrypoints/init.ts` | Global state store, telemetry, config |
| CLI Core | `src/main.tsx`, `src/commands.ts`, `src/commands/` | Arg parsing, subcommand routing |
| State | `src/state/`, `src/bootstrap/state.ts` | AppStateStore, session state |
| Tools | `src/tools.ts`, `src/tools/` | Tool implementations (Bash, Read, Write, Glob, Grep, MCP, etc.) |
| Services | `src/services/` | API client, MCP, plugins, LSP, compact, policy |
| UI | `src/components/`, `src/ink/` | React + Ink terminal UI |
| Utils | `src/utils/` | Settings, permissions, model selection, session storage |

**Feature flags** via `feature()` from `bun:bundle`: `COORDINATOR_MODE`, `KAIROS`, `PROACTIVE`, `BRIDGE_MODE`, `VOICE_MODE`, `AGENT_TRIGGERS`, `WORKFLOW_SCRIPTS`

**Tool system** — tools defined in `src/Tool.ts`, registered in `src/tools.ts`. Uses `buildTool()` helper with `ToolDef` type. Each tool implements `validateInput()`, `checkPermissions()`, `renderToolUseMessage()`.

**Key patterns:**
- Circular dependencies broken via lazy `require()` (see `src/main.tsx:69-73`)
- Settings layering: MDM/policy → remote managed → local `settings.json` → CLI flags
- Permissions: `PermissionMode` type (`'default'`, `'auto'`, `'bypass'`), `ToolPermissionContext` for checks
- FS abstraction: `getFsImplementation()` for cross-platform ops, `src/utils/windowsPaths.ts` for Windows paths

### `examples/` — Runnable Agent Examples

Both SimpleAgent implementations follow the same architecture (mirroring Claude Code's patterns):

| Module | TypeScript | Python |
|--------|-----------|--------|
| Agent core | `simple-agent/src/agent/Agent.ts` | `simple-agent-python/src/agent/agent.py` |
| LLM client | `simple-agent/src/agent/LLMClient.ts` | `simple-agent-python/src/agent/llm_client.py` |
| Tool base | `simple-agent/src/tools/Tool.ts` | `simple-agent-python/src/tools/base.py` |
| State store | `simple-agent/src/state/StateStore.ts` | `simple-agent-python/src/state/store.py` |
| Permissions | `simple-agent/src/permissions/PermissionChecker.ts` | `simple-agent-python/src/permissions/checker.py` |
| Session storage | `simple-agent/src/state/SessionStorage.ts` | `simple-agent-python/src/state/session.py` |

Advanced examples: `examples/simple-agent/examples/multi-agent.ts`, `examples/simple-agent-python/examples/multi_agent_collaboration.py`, `examples/simple-agent-python/examples/mcp_integration.py`

## Code Style (for `examples/` contributions)

See `AGENTS.md` for full guidelines extracted from Claude Code source. Key rules:
- TypeScript strict mode, `zod` for runtime validation
- Single quotes, semicolons required, trailing commas in multi-line
- PascalCase for files/classes/types, camelCase for functions/variables, UPPER_SNAKE_CASE for constants
- `import type {}` for type-only imports
- `.js` extensions on local imports (Bun requirement)

## Learning Resources

Tutorial series in `docs-site/agent-learning-guide/` (9 parts, Chinese):
- Start: `docs-site/agent-learning-guide/00-learning-roadmap.md`
- Index: `docs-site/agent-learning-guide/README.md`
- Live site: https://python012.github.io/learn-agent-from-claude-code/
