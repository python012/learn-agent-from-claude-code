# 参考 Claude Code 源代码学习 Agent 开发

[![GitHub Stars](https://img.shields.io/github/stars/python012/learn-agent-from-claude-code?style=flat-square&logo=github)](https://github.com/python012/learn-agent-from-claude-code/stargazers)
[![License](https://img.shields.io/github/license/python012/learn-agent-from-claude-code?style=flat-square&label=license)](LICENSE)
[![TypeScript](https://img.shields.io/github/languages/top/python012/learn-agent-from-claude-code?style=flat-square&logo=typescript)](https://github.com/python012/learn-agent-from-claude-code/search?l=typescript)
[![Python](https://img.shields.io/badge/language-Python-blue?style=flat-square&logo=python)](https://github.com/python012/learn-agent-from-claude-code/tree/main/examples/simple-agent-python)

本仓库包含一套完整的 **Agent 开发教程系列**，通过深入分析和解读 Claude Code 源码，引导有一定经验的软件工程师学习 AI Agent 开发。

## 学习指南（共 9 篇）

| 序号 | 文档 | 核心内容 |
|------|------|----------|
| 00 | [学习路线总览](docs-site/agent-learning-guide/00-learning-roadmap.md) | 系列介绍、学习路径、时间估算 |
| 01 | [LLM 基础与 Agent 概念](docs-site/agent-learning-guide/01-llm-fundamentals-and-agent-concepts.md) | API 交互、消息格式、工具调用、流式响应 |
| 02 | [Agent 架构入门](docs-site/agent-learning-guide/02-agent-architecture-introduction.md) | 整体架构、状态管理、命令系统、数据流 |
| 03 | [工具系统详解](docs-site/agent-learning-guide/03-tool-system-explained.md) | Tool 接口、工具实现、权限控制、自定义工具 |
| 04 | [会话与状态管理](docs-site/agent-learning-guide/04-session-and-state-management.md) | 会话存储、消息链、持久化、恢复机制 |
| 05 | [权限与安全控制](docs-site/agent-learning-guide/05-permission-and-security-control.md) | 权限模式、规则系统、Auto Mode 分类器 |
| 06 | [MCP 与外部集成](docs-site/agent-learning-guide/06-mcp-and-external-integration.md) | MCP 协议、外部工具集成、资源管理 |
| 07 | [多 Agent 协作系统](docs-site/agent-learning-guide/07-multi-agent-collaboration-system.md) | Agent 生成、通信、协调器模式 |
| 08 | [实战：构建自己的 Agent](docs-site/agent-learning-guide/08-build-your-own-agent.md) | 综合实践、从零实现完整 Agent 系统（TypeScript + Python 双版本） |

### 快速开始

1. **初学者路径**（22-32 小时）：按顺序阅读第 01-08 篇
2. **进阶路径**（有 LLM 经验）：第 02 → 03 → 05 → 06 → 07 → 08 篇
3. **专题深入**：工具开发、权限系统、架构设计

完整学习指南索引：[docs-site/agent-learning-guide/README.md](docs-site/agent-learning-guide/README.md)

### 核心代码索引

#### TypeScript 版本（参考 Claude Code）

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

#### Python 版本（第 08 篇实战示例）

| 模块 | 源码路径 | 用途 |
|------|----------|------|
| Agent 核心 | `examples/simple-agent-python/src/agent/agent.py` | Agent 核心实现 |
| LLM 客户端 | `examples/simple-agent-python/src/agent/llm_client.py` | OpenAI 客户端封装 |
| 工具基类 | `examples/simple-agent-python/src/tools/base.py` | Tool 接口定义 |
| 状态管理 | `examples/simple-agent-python/src/state/store.py` | 状态存储 |
| 权限检查 | `examples/simple-agent-python/src/permissions/checker.py` | 权限规则系统 |

> **说明**: 第 8 篇实战提供两个版本的 SimpleAgent 实现：
> - **TypeScript 版本**: `examples/simple-agent/` — 适合熟悉 Node.js 生态的开发者
> - **Python 版本**: `examples/simple-agent-python/` — 适合熟悉 Python 生态的开发者

---

## 关于本仓库

本仓库以 **AI Agent 开发学习** 为核心主题，提供完整的教程系列和示例代码。

- **学习指南**：位于 [`docs-site/agent-learning-guide/`](docs-site/agent-learning-guide/) 目录，是仓库的核心内容
  - 完整索引：[docs-site/agent-learning-guide/README.md](docs-site/agent-learning-guide/README.md)
- **示例代码**：位于 [`examples/`](examples/) 目录
  - `examples/simple-agent/` — TypeScript 版本 SimpleAgent 实现
  - `examples/simple-agent-python/` — Python 版本 SimpleAgent 实现
- **源码参考**：位于 `src/` 目录，保留 Claude Code 代码作为架构学习参考
- **原文档站**：位于 `docs-site/` 目录，保留原 MkDocs 文档

> **注意**：`src/` 目录为只读架构参考，无 `package.json`，不可直接构建或运行。请将其视为 **学习资源** 而非可执行项目。
