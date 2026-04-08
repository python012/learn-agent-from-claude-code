# AGENTS.md — Agentic Coding Guidelines

## Repository Overview

This is a **recovered source tree** of Anthropic's Claude Code CLI (reconstructed from npm source-map leak, 2026-03-31). The codebase is **read-only architectural reference** — there is no `package.json` and building requires the original toolchain (Bun, internal `bun:bundle` features, private dependencies).

**Important:** The underlying software is Anthropic's proprietary product. Use beyond fair use / your local law is your responsibility.

---

## Build / Lint / Test Commands

### Build System
- **Runtime:** Bun (uses `bun:bundle` for dead code elimination and feature flags)
- **No local build:** This is a recovered source tree without build toolchain
- **Entry Point:** `src/main.tsx` (~800KB bundled, Commander-based CLI)

### Linting
- **Linter:** ESLint + Biome (dual setup)
- **Custom rules:** `custom-rules/` namespace for project-specific lint rules
- **Common lint disables:**
  ```typescript
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  // biome-ignore lint/suspicious/noConsole: intentional console output
  // eslint-disable-next-line custom-rules/no-process-env-top-level
  ```

### Testing
- **No test runner available** in this recovered source tree
- Test files follow pattern: `*.test.ts`, `*.test.tsx`
- Example test location: `test/utils/transcriptSearch.renderFidelity.test.tsx`
- **Single test execution:** Not available without original toolchain

### Documentation
- **Live site:** https://mehmoodosman.github.io/claude-code-source-code/
- **Local preview:** `cd docs-site && python3 -m venv .venv && pip install -r requirements.txt && mkdocs serve`

---

## Code Style Guidelines

### Imports
- **Extension required:** Always use `.js` for local imports, `.mjs` for ESM packages (Bun bundler requirement)
- **Import organization:** Type imports first, then regular imports; use `/* eslint-disable @typescript-eslint/no-require-imports */` for lazy `require()`
- **biome-ignore-all** for import order when markers must not be reordered

### Formatting
- **Semicolons:** Required
- **Quotes:** Single quotes for strings
- **Trailing commas:** Use in multi-line objects/arrays
- **Line length:** ~120 characters (soft limit)
- **Arrow functions:** Use `=>` with space before and after
- **Object literals:** Use shorthand when possible

### Types
- **TypeScript:** Strict mode with `zod/v4` for runtime validation
- **Type imports:** Always use `import type {}` for type-only imports
- **Generic types:** Use descriptive names (`Input`, `Output`, `P extends ToolProgressData`)
- **Zod schemas:** Use `z.object()` with `zod/v4` for input validation
- **DeepImmutable:** Use for contexts that must not be mutated

### Naming Conventions
- **Files:** PascalCase for components/tools (`BashTool.tsx`, `AppState.ts`), camelCase for utilities (`errors.ts`, `format.ts`)
- **Classes/Types:** PascalCase (`Tool`, `ToolUseContext`, `ShellError`)
- **Functions/variables:** camelCase (`buildTool`, `isSearchOrReadBashCommand`)
- **Constants:** UPPER_SNAKE_CASE (`TOOL_DEFAULTS`, `BASH_SEARCH_COMMANDS`)
- **React components:** PascalCase with descriptive names (`renderToolUseMessage`, `ToolUseProgressMessage`)
- **Feature flags:** UPPER_SNAKE_CASE (`COORDINATOR_MODE`, `KAIROS`, `PROACTIVE`)

### Error Handling
- **Custom error classes:** Extend `Error` with descriptive names (e.g., `ShellError`, `AbortError`, `TelemetrySafeError`)
- **Error detection:** Use type guards (e.g., `isAbortError()`)
- **Telemetry safety:** Use `TelemetrySafeError_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` for telemetry-logged errors

### React + Ink (Terminal UI)
- **Framework:** React + Ink for terminal UI components
- **Hooks:** Standard React hooks (`useState`, `useEffect`, `useMemo`)
- **Cleanup:** Use `registerCleanup()` for global cleanup handlers
- **Rendering:** Return JSX from `renderToolUseMessage()`, `renderToolResultMessage()` methods

### Comments & Documentation
- **JSDoc:** Use for public APIs and complex functions
- **Inline comments:** Explain "why" not "what"
- **TODO markers:** Use `TODO:` prefix with context
- **File headers:** Add context for side-effect files (e.g., `src/main.tsx` lines 1-8)

### Feature Flags
- **Bun feature flags:** Use `feature()` from `bun:bundle` for dead code elimination
- **Environment flags:** Use `process.env.USER_TYPE === 'ant'` for ant-only features

### Permissions & Security
- **Permission modes:** Use `PermissionMode` type (`'default'`, `'auto'`, `'bypass'`, etc.)
- **Tool validation:** Implement `validateInput()` and `checkPermissions()` in tools
- **Permission context:** Use `ToolPermissionContext` for permission checks
- **Telemetry:** Never log file paths, code snippets, or sensitive data

### Async Patterns
- **Promise handling:** Use `async/await` consistently
- **AbortController:** Pass `AbortSignal` to long-running operations
- **Foreground tasks:** Use `registerForeground()` / `unregisterForeground()` for shell tasks
- **No floating promises:** Use `biome-ignore lint/nursery/noFloatingPromises` with justification

### File Operations
- **FS abstraction:** Use `getFsImplementation()` for cross-platform FS ops
- **Path handling:** Use `expandPath()`, `safeResolvePath()` for path operations
- **Windows compatibility:** Use `src/utils/windowsPaths.ts` for path conversion
- **Sync FS:** Only in exit handlers; disable lint with `/* eslint-disable custom-rules/no-sync-fs */`

### Testing Patterns
- **Test files:** `*.test.ts` / `*.test.tsx`
- **Test structure:** Arrange-Act-Assert pattern
- **Fidelity tests:** Use `renderFidelity.test.tsx` pattern for UI component testing

### Common Patterns
- **Tool definition:** Use `buildTool()` helper with `ToolDef` type
- **State management:** Use `AppState` with `setAppState()` pattern
- **Session storage:** Use `sessionStorage.ts` for JSONL persistence
- **MCP integration:** Use `src/services/mcp/` for Model Context Protocol
- **Lazy require:** Use `lazy require()` for circular dependency breaks (e.g., `const getTeammateUtils = () => require('./utils/teammate.js')`)

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/Tool.ts` | Core Tool interface definition |
| `src/tools.ts` | Tool pool assembly |
| `src/tools/` | Tool implementations (Bash, Read, Write, etc.) |
| `src/services/` | API, MCP, LSP, plugins, analytics |
| `src/state/` | AppState store and state management |
| `src/utils/` | Utilities (permissions, settings, model, session) |
| `src/components/` | React + Ink UI components |
| `src/types/` | TypeScript type definitions |
| `docs-site/agent-learning-guide/` | Agent development tutorials (9 parts) |

---

## Learning Resources

- **Tutorial series:** `docs-site/agent-learning-guide/` (9 comprehensive guides)
- **Start here:** `docs-site/agent-learning-guide/00-learning-roadmap.md` (learning path overview)
- **Code index:** See `docs-site/agent-learning-guide/README.md` for core code locations

---

## Legal Notice

This source tree is reconstructed from a published npm package's source map. The underlying software is Anthropic's proprietary product. This repository is for **architectural reference and educational purposes only**. Use beyond fair use / your local law is your responsibility.
