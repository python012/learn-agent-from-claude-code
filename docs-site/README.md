# Agent 开发学习指南

[![GitHub Stars](https://img.shields.io/github/stars/python012/learn-agent-from-claude-code?style=flat-square&logo=github)](https://github.com/python012/learn-agent-from-claude-code/stargazers)
[![License](https://img.shields.io/github/license/python012/learn-agent-from-claude-code?style=flat-square&label=license)](https://github.com/python012/learn-agent-from-claude-code/blob/main/LICENSE)

> 通过深入分析 Claude Code 源代码，系统学习 AI Agent 开发

---

## 📚 系列概述

本系列文档通过深入分析 Claude Code 源代码，引导有 Python 和 TypeScript 经验的工程师系统学习 AI Agent 开发。

### 完整教程列表

| 序号 | 文档 | 核心内容 |
|------|------|----------|
| 00 | [学习路线总览](./agent-learning-guide/00-learning-roadmap.md) | 系列介绍、学习路径、时间估算 |
| 01 | [LLM 基础与 Agent 概念](./agent-learning-guide/01-llm-fundamentals-and-agent-concepts.md) | API 交互、消息格式、工具调用、流式响应 |
| 02 | [Agent 架构入门](./agent-learning-guide/02-agent-architecture-introduction.md) | 整体架构、状态管理、命令系统、数据流 |
| 03 | [工具系统详解](./agent-learning-guide/03-tool-system-explained.md) | Tool 接口、工具实现、权限控制、自定义工具 |
| 04 | [会话与状态管理](./agent-learning-guide/04-session-and-state-management.md) | 会话存储、消息链、持久化、恢复机制 |
| 05 | [权限与安全控制](./agent-learning-guide/05-permission-and-security-control.md) | 权限模式、规则系统、Auto Mode 分类器 |
| 06 | [MCP 与外部集成](./agent-learning-guide/06-mcp-and-external-integration.md) | MCP 协议、外部工具集成、资源管理 |
| 07 | [多 Agent 协作系统](./agent-learning-guide/07-multi-agent-collaboration-system.md) | Agent 生成、通信、协调器模式 |
| 08 | [实战：构建自己的 Agent](./agent-learning-guide/08-build-your-own-agent.md) | 综合实践、从零实现完整 Agent 系统 |

---

## 🚀 快速开始

### 学习路径建议

**初学者路径**（22-32 小时）：按顺序阅读第 01-08 篇

**进阶路径**（有 LLM 经验）：第 02 → 03 → 05 → 06 → 07 → 08 篇

### 示例代码

本系列提供完整的示例代码：

- **TypeScript 版本**：[examples/simple-agent](https://github.com/python012/learn-agent-from-claude-code/tree/main/examples/simple-agent)
- **Python 版本**：[examples/simple-agent-python](https://github.com/python012/learn-agent-from-claude-code/tree/main/examples/simple-agent-python)

### 高级示例

- [多 Agent 协作示例](https://github.com/python012/learn-agent-from-claude-code/tree/main/examples/simple-agent-python/examples/multi_agent_collaboration.py)
- [MCP 集成示例](https://github.com/python012/learn-agent-from-claude-code/tree/main/examples/simple-agent-python/examples/mcp_integration.py)

---

## 📖 核心概念速查

### Agent = LLM + Tools + State + Permissions

```
┌─────────────────────────────────────────────────────────┐
│                      Agent                              │
├─────────────┬─────────────┬─────────────┬───────────────┤
│    LLM      │   Tools     │    State    │  Permissions  │
│   决策核心   │  能力扩展   │  上下文记忆  │   安全边界    │
└─────────────┴─────────────┴─────────────┴───────────────┘
```

### 工具调用流程

```
用户请求 → LLM 决策 → 工具调用 → 权限检查 → 执行 → 返回结果 → LLM 总结
```

---

## 🛠️ 本地开发

### 预览文档站点

```bash
# 安装依赖
pip install mkdocs mkdocs-material

# 本地预览
mkdocs serve
```

访问 http://127.0.0.1:8000 查看文档。

### 构建静态站点

```bash
mkdocs build
```

---

## 📦 部署到 GitHub Pages

### 自动部署（推荐）

已配置 GitHub Actions，推送到 `main` 分支时自动部署。

### 手动部署

```bash
mkdocs gh-deploy
```

---

## 🔗 相关链接

- [GitHub 仓库](https://github.com/python012/learn-agent-from-claude-code)
- [Issue 反馈](https://github.com/python012/learn-agent-from-claude-code/issues)
- [MCP 官方仓库](https://github.com/modelcontextprotocol)

---

## 📄 License

MIT License
