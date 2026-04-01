# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **recovered source tree** of Anthropic's Claude Code CLI, reconstructed from an npm source-map leak on 2026-03-31. The codebase is **read-only architectural reference** — there is no `package.json` and building requires the original toolchain (Bun, internal `bun:bundle` features, private dependencies).

**Important:** The underlying software is Anthropic's proprietary product. Use beyond fair use / your local law is your responsibility.

## Architecture Overview

### Runtime & UI Stack

- **Runtime:** Bun (uses `bun:bundle` for dead code elimination and feature flags)
- **Terminal UI:** React + Ink (React for CLI)
- **Entry Point:** `src/main.tsx` (~800KB bundled, Commander-based CLI)
- **Command Pattern:** Subcommands registered in `src/commands.ts`, tools in `src/tools.ts`

### Core Layers

| Layer | Key Files/Directories | Purpose |
|-------|----------------------|---------|
| **Bootstrap** | `src/bootstrap/state.ts`, `src/entrypoints/init.ts` | Global state store, telemetry init, config system |
| **CLI Core** | `src/main.tsx`, `src/commands.ts`, `src/commands/` | Argument parsing, subcommand routing, pre-action hooks |
| **State** | `src/state/`, `src/bootstrap/state.ts` | AppStateStore, session state, settings |
| **Tools** | `src/tools.ts`, `src/tools/` | Tool implementations (Bash, Read, Write, Glob, Grep, MCP, etc.) |
| **Services** | `src/services/` | API client, MCP, plugins, LSP, compact, policy limits |
| **UI Components** | `src/components/`, `src/ink/` | React + Ink terminal UI components |
| **Utils** | `src/utils/` | Settings, permissions, model selection, session storage |

### Feature Flags

Dead code elimination via `feature()` from `bun:bundle`:
- `COORDINATOR_MODE` — Multi-agent coordination
- `KAIROS` — Assistant/Agent SDK mode
- `PROACTIVE` — Proactive features
- `BRIDGE_MODE` — Bridge/repl bridge
- `VOICE_MODE` — Voice mode
- `AGENT_TRIGGERS` — Cron/remote trigger tools
- `WORKFLOW_SCRIPTS` — Workflow scripts

### Key Subsystems

**MCP (Model Context Protocol):** `src/services/mcp/`
- Config parsing, stdio/SDK transports, OAuth, XAA/IDP login

**Plugins:** `src/services/plugins/`, `src/plugins/`, `src/utils/plugins/`
- Bundled and user plugins, versioned plugin management

**Settings:** `src/utils/settings/`, `src/services/remoteManagedSettings/`
- Layered config (local, MDM, remote), validation, change detection

**Permissions:** `src/utils/permissions/`
- Permission modes, auto-mode, tool permission context

**Telemetry:** `src/services/analytics/`, `src/utils/telemetry/`
- GrowthBook, event logging, usage tracking

**Session Management:** `src/utils/sessionStorage.js`, `src/history.ts`
- Session persistence, conversation recovery, title caching

### Tool System

Tools are defined in `src/Tool.ts` and registered in `src/tools.ts`:
- Core: `BashTool`, `FileReadTool`, `FileWriteTool`, `FileEditTool`, `GlobTool`, `GrepTool`
- Notebook: `NotebookEditTool`
- Web: `WebFetchTool`, `WebSearchTool`
- Task management: `TaskCreateTool`, `TaskUpdateTool`, `TaskListTool`, etc.
- Planning: `EnterPlanModeTool`, `ExitPlanModeV2Tool`
- Worktree: `EnterWorktreeTool`, `ExitWorktreeTool`
- MCP: `ListMcpResourcesTool`, `ReadMcpResourceTool`, `McpAuthTool`
- Agent/Skill: `AgentTool`, `SkillTool`

### Command System

Commands defined in `src/commands.ts` and `src/commands/`:
- Interactive: REPL, `/compact`, `/memory`, `/config`, `/mcp`
- Git: `/diff`, `/commit`, `/commit-push-pr`, `/branch`
- Utils: `/doctor`, `/status`, `/usage`, `/cost`
- Setup: `/login`, `/logout`, `/install`, `/permissions`
- Feature gates: `/bridge`, `/voice`, `/assistant` (behind `feature()` flags)

## Settings & Configuration

Settings layering (`src/utils/settings/`):
1. MDM/policy (macOS defaults, Windows registry)
2. Remote managed settings (enterprise)
3. Local `settings.json`
4. CLI flags

Key utilities:
- `src/utils/config.js` — Global config, auto-updater, trust dialog
- `src/utils/sessionStorage.js` — Session persistence, title caching
- `src/utils/model/model.ts` — Model selection, subscription gates

## Model Selection

Model handling in `src/utils/model/`:
- Aliases (`claude-sonnet`, `claude-opus`, etc.) in `aliases.ts`
- Subscription-based gating (`src/utils/auth.ts`)
- Provider abstraction in `providers.ts`

## Development Notes

- **No local build:** This is a recovered source tree without build toolchain
- **Windows paths:** Use forward slashes; `src/utils/windowsPaths.ts` handles conversion
- **Circular dependencies:** Broken via lazy `require()` patterns (see `src/main.tsx:69-73`)
- **Early input:** `src/utils/earlyInput.ts` captures keystrokes during startup

## Documentation

Full documentation site in `docs-site/` (MkDocs Material):
- Live: https://mehmoodosman.github.io/claude-code-source-code/
- Local: `cd docs-site && python3 -m venv .venv && pip install -r requirements.txt && mkdocs serve`

See `README.md` for full architectural overview and directory structure.
