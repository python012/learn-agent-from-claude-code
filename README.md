# 参考 Claude Code 源代码学习 Agent 开发

本仓库包含一套完整的 **Agent 开发教程系列**，通过深入分析 Claude Code 源代码，引导有 Python/TypeScript 经验的工程师系统学习 Agent 开发。

## 学习指南（共 9 篇）

| 序号 | 文档 | 核心内容 |
|------|------|----------|
| 00 | [学习路线总览](docs/agent-learning-guide/00-学习路线总览.md) | 系列介绍、学习路径、时间估算 |
| 01 | [LLM 基础与 Agent 概念](docs/agent-learning-guide/01-LLM基础与Agent概念.md) | API 交互、消息格式、工具调用、流式响应 |
| 02 | [Agent 架构入门](docs/agent-learning-guide/02-Agent架构入门.md) | 整体架构、状态管理、命令系统、数据流 |
| 03 | [工具系统详解](docs/agent-learning-guide/03-工具系统详解.md) | Tool 接口、工具实现、权限控制、自定义工具 |
| 04 | [会话与状态管理](docs/agent-learning-guide/04-会话与状态管理.md) | 会话存储、消息链、持久化、恢复机制 |
| 05 | [权限与安全控制](docs/agent-learning-guide/05-权限与安全控制.md) | 权限模式、规则系统、Auto Mode 分类器 |
| 06 | [MCP 与外部集成](docs/agent-learning-guide/06-MCP与外部集成.md) | MCP 协议、外部工具集成、资源管理 |
| 07 | [多 Agent 协作系统](docs/agent-learning-guide/07-多Agent协作系统.md) | Agent 生成、通信、协调器模式 |
| 08 | [实战：构建自己的 Agent](docs/agent-learning-guide/08-实战构建自己的Agent.md) | 综合实践、从零实现完整 Agent 系统 |

### 快速开始

1. **初学者路径**（22-32 小时）：按顺序阅读第 01-08 篇
2. **进阶路径**（有 LLM 经验）：第 02 → 03 → 05 → 06 → 07 → 08 篇
3. **专题深入**：工具开发、权限系统、架构设计

完整学习指南索引：[docs/agent-learning-guide/README.md](docs/agent-learning-guide/README.md)

### 核心代码索引

| 模块 | 源码路径 | 用途 |
|------|----------|------|
| Tool 接口 | `src/Tool.ts` | 工具接口定义 |
| 工具注册 | `src/tools.ts` | 工具池组装 |
| 状态管理 | `src/state/AppStateStore.ts` | 全局状态 |
| API 调用 | `src/services/api/claude.ts` | LLM API 客户端 |
| 权限检查 | `src/utils/permissions/permissions.ts` | 权限规则系统 |
| 会话存储 | `src/utils/sessionStorage.ts` | JSONL 持久化 |
| Agent 工具 | `src/tools/AgentTool/AgentTool.tsx` | 多 Agent 协作 |
| MCP 客户端 | `src/services/mcp/client.ts` | 外部工具集成 |

---

## 关于本仓库

本仓库最初是作为 Claude Code 源代码的恢复版本而创建，现转型为 **Agent 开发学习参考仓库**。

- **学习指南**：位于 [`docs/agent-learning-guide/`](docs/agent-learning-guide/) 目录，是仓库的核心内容
  - 完整索引：[docs/agent-learning-guide/README.md](docs/agent-learning-guide/README.md)
- **源码参考**：位于 `src/` 目录，保留原始 Claude Code 代码作为学习参考
- **原文档站**：位于 `docs-site/` 目录，保留原 MkDocs 文档

> **注意**：`src/` 部分为只读参考，无 `package.json`，构建需要原始工具链（Bun、内部特性、私有依赖）。请将其视为 **架构参考** 而非可构建项目。

---

# Claude Code — recovered source tree

## What this is

On **31 March 2026**, developers reported that the published npm package for Anthropic's **Claude Code** CLI shipped a large bundled `cli.js` together with a **source map** (`.map`). Because the map pointed back to original paths and content, the TypeScript/React implementation could be reconstructed from the registry artifact. This repository holds that kind of **recovered `src/` tree** — useful for understanding architecture and integration, not an official release or supported SDK.

## How it leaked

Chaofan Shou (@Fried_rice) discovered the leak and posted it publicly:

> Claude code source code has been leaked via a map file in their npm registry!
>
> — @Fried_rice, 31 March 2026

The source map file in the published npm package contained a reference to the full, unobfuscated TypeScript source, which was downloadable as a zip archive from Anthropic's R2 storage bucket.

## Overview

Claude Code is Anthropic's official CLI tool that lets you interact with Claude directly from the terminal to perform software engineering tasks — editing files, running commands, searching codebases, managing git workflows, and more.

This repository contains the leaked `src/` directory.

| Property    | Value                                |
| ----------- | ------------------------------------ |
| Leaked on   | 2026-03-31                           |
| Language    | TypeScript                           |
| Runtime     | Bun                                  |
| Terminal UI | React + Ink (React for CLI)          |
| Scale       | ~1,900 files, 512,000+ lines of code |

Discussion and context: [Hacker News thread on the npm source-map leak](https://news.ycombinator.com/item?id=47584540).

**Legal / ethical note:** The underlying software is Anthropic's proprietary product. This README describes structure for analysis only; redistribution or use beyond fair use / your local law is your responsibility.

## How the codebase fits together

The CLI is a **Bun-bundled** application whose spine is `src/main.tsx`: a [Commander](https://github.com/tj/commander.js)-based program named `claude` that registers global options, subcommands, and a `preAction` hook where trust, settings, telemetry gates, and prefetch work run before the interactive or print-mode loop.

### Directory structure

The tree below matches this repo's `src/` layout. For root-level filenames, per-folder notes, and selected subtrees (`services/`, `tools/`, `utils/`), see [docs/directory-structure.md](docs/directory-structure.md).

```text
src/
├── main.tsx
├── QueryEngine.ts
├── Task.ts
├── Tool.ts
├── commands.ts
├── context.ts
├── cost-tracker.ts
├── costHook.ts
├── dialogLaunchers.tsx
├── history.ts
├── ink.ts
├── interactiveHelpers.tsx
├── projectOnboardingState.ts
├── query.ts
├── replLauncher.tsx
├── setup.ts
├── tasks.ts
├── tools.ts
│
├── assistant/
├── bootstrap/
├── bridge/
├── buddy/
├── cli/
├── commands/
├── components/
├── constants/
├── context/
├── coordinator/
├── entrypoints/
├── hooks/
├── ink/
├── keybindings/
├── memdir/
├── migrations/
├── moreright/
├── native-ts/
├── outputStyles/
├── plugins/
├── query/
├── remote/
├── schemas/
├── screens/
├── server/
├── services/
├── skills/
├── state/
├── tasks/
├── tools/
├── types/
├── upstreamproxy/
├── utils/
├── vim/
├── voice/
└── docs/agent-learning-guide/
```

### High-level layers

| Area                                                                                       | Role                                                                                                                                      |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **`main.tsx` + `cli/`**                                                                    | Argument parsing, early startup (MDM/keychain prefetch side effects), routing to REPL, `-p`/`--print`, doctor, install, MCP helpers, etc. |
| **`replLauncher.js` / `components/` / `ink/`**                                             | Terminal UI built with **React + Ink**; dialogs, status, and input handling.                                                              |
| **`services/api/`**                                                                        | HTTP client to Anthropic APIs, bootstrap, files, session ingress, usage, retries.                                                         |
| **`services/mcp/`**                                                                        | Model Context Protocol: config parsing, stdio/SDK transports, connection manager, OAuth, enterprise/XAA paths.                            |
| **`services/compact/`**                                                                    | Session compaction (memory/context management hooks the model loop).                                                                      |
| **`services/lsp/`**                                                                        | Optional LSP integration for editor-like features in the terminal workflow.                                                               |
| **`tools/`**                                                                               | Tool implementations the agent invokes (bash, read/write, grep/glob, web, todos, tasks, teammates, MCP tools, etc.).                      |
| **`utils/swarm/`**                                                                         | Multi-agent **teammate** flows: backends for tmux, iTerm, in-process runners, permission sync, reconnection.                              |
| **`coordinator/`**                                                                         | Gated behind bundle feature `COORDINATOR_MODE` (multi-agent coordination).                                                                |
| **`assistant/`**                                                                           | Gated behind bundle feature `KAIROS` (assistant / Agent SDK–oriented mode).                                                               |
| **`plugins/`**, **`skills/`**                                                              | Bundled and user plugins; skill loading and telemetry.                                                                                    |
| **`utils/settings/`**, **`services/policyLimits/`**, **`services/remoteManagedSettings/`** | Layered configuration, enterprise policy, and remote-managed settings.                                                                    |
| **`buddy/`**, **`upstreamproxy/`**, **`voice/`**, **`vim/`**                               | Product features (buddy flows, upstream proxy, voice, vim-style editing).                                                                 |
| **`utils/deepLink/`**, **`utils/claudeInChrome/`**                                         | OS integration: URL schemes, Chrome native messaging, optional MCP entrypoints.                                                           |

Execution paths converge on shared **state** (`state/`, `bootstrap/`), **permissions** (`utils/permissions/`), and **session storage** (`utils/sessionStorage.js`, hooks in `utils/sessionStart.js`). Non-interactive and SDK-style use share much of the same stack as the full-screen REPL, with different front-ends for I/O.

## Documentation (GitHub Pages)

Full internals documentation is built with **MkDocs Material** from [`docs-site/`](docs-site/). The site includes **system design** (layers, state flow, security/trust), **architecture** overview and **workflows**, a **developer hub** (editing docs, navigating `src/`, Bun feature flags), **guides** for greenfield agentic CLI and docs/CI patterns, **reference** pages per subsystem, **official docs map**, and **appendices** (directory layout, tools, env vars, glossary).

- **Live site:** [https://mehmoodosman.github.io/claude-code-source-code/](https://mehmoodosman.github.io/claude-code-source-code/)
- **Local preview:** `cd docs-site && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && mkdocs serve`
- **Publish:** pushing to `main` runs [`.github/workflows/pages.yml`](.github/workflows/pages.yml) and deploys to `gh-pages`.

**Contributing to docs:** edit Markdown under `docs-site/docs/`; keep the [official docs map](docs-site/docs/official-docs-map.md) in sync with [Anthropic's docs index](https://code.claude.com/docs/llms.txt) when adding major features.

### Next steps (forks / new clones)

1. **Commit and push** so `main` includes `docs-site/` and `.github/workflows/pages.yml`.
2. **Run the Pages workflow** (or wait for it on push).
3. **Settings → Pages** → deploy from branch **`gh-pages`** / **`/ (root)`** (unless you switch to the GitHub Actions Pages source).
4. Set **`site_url`** in `mkdocs.yml` to your live URL and align **`repo_url`** / **`extra.social`** with your fork, then push to refresh the site.

## Repository layout

- **`src/`** — Application source (thousands of modules) as recovered from the bundle map.
- **`docs-site/`** — MkDocs source for the GitHub Pages documentation site.
- **`docs/`** — Short pointer plus [`directory-structure.md`](docs/directory-structure.md) (`src/` layout reference).
- **`scripts/`** — Optional helpers (e.g. `gen-appendices.sh`).
- There is **no `package.json` in this clone**; building would require the original toolchain (Bun, internal `bun:bundle` features, and private deps). Treat this tree as a **read-only architectural reference**.
