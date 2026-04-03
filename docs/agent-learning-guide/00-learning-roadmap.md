# Agent 开发学习指南 — 学习路线总览

## 系列简介

本系列文档通过深入分析 Claude Code 源代码，引导有 Python 和 TypeScript 经验的工程师系统学习 Agent 开发。

> **重要说明**: 本项目是从 npm source-map 恢复的 Claude Code 源代码，作为学习参考。代码仅供学习架构设计，不可直接运行。

---

## 目标读者

- 熟练使用 Python 和 TypeScript 的工程师
- 了解 LLM 基本概念（prompt、completion、token）
- **无需** LLM API 使用经验（本指南会介绍）

---

## 学习目标

完成本系列学习后，你将能够：

1. 设计一个类似 Claude Code 的 CLI Agent 架构
2. 为自己的项目添加 Agent 功能
3. 理解并修改此类 Agent 项目的代码
4. 独立设计和实现生产级 Agent 系统

---

## 文档结构

本系列共 8 篇文档，按推荐学习顺序排列：

### 第 1 篇：[LLM 基础与 Agent 概念](./01-llm-fundamentals-and-agent-concepts.md)

**学习目标**：
- 理解 LLM API 的基本工作原理
- 掌握消息格式、工具调用、流式响应等核心概念
- 为后续阅读代码打下理论基础

**关键代码文件**：
- `src/services/api/claude.ts` — API 调用核心逻辑

---

### 第 2 篇：[Agent 架构入门](./02-agent-architecture-introduction.md)

**学习目标**：
- 理解 Claude Code 的整体架构
- 掌握状态管理、命令系统、工具注册等核心模块
- 了解数据流和执行路径

**关键代码文件**：
- `src/main.tsx` — 入口点和命令系统
- `src/state/AppState.tsx` — 状态管理
- `src/Task.ts` — 任务抽象

---

### 第 3 篇：[工具系统详解](./03-tool-system-explained.md)

**学习目标**：
- 理解工具系统的核心设计模式
- 学会定义和实现自定义工具
- 掌握工具权限控制机制

**关键代码文件**：
- `src/Tool.ts` — 工具接口定义
- `src/tools.ts` — 工具注册和组装
- `src/tools/BashTool/BashTool.tsx` — 工具实现示例

---

### 第 4 篇：[会话与状态管理](./04-session-and-state-management.md)

**学习目标**：
- 理解多轮对话的上下文管理
- 掌握状态持久化和恢复机制
- 学习会话边界处理

**关键代码文件**：
- `src/state/AppStateStore.ts` — 状态存储
- `src/utils/sessionStorage.ts` — 会话持久化

---

### 第 5 篇：[权限与安全控制](./05-permission-and-security-control.md)

**学习目标**：
- 理解 Agent 权限系统的设计原则
- 掌握权限规则的配置和执行流程
- 学习自动模式分类器的工作原理

**关键代码文件**：
- `src/utils/permissions/permissions.ts` — 权限检查核心逻辑
- `src/types/permissions.ts` — 权限类型定义

---

### 第 6 篇：[MCP 与外部集成](./06-mcp-and-external-integration.md)

**学习目标**：
- 理解 Model Context Protocol (MCP) 的设计
- 学习如何集成外部工具和服务
- 掌握 MCP 客户端的实现方式

**关键代码文件**：
- `src/services/mcp/` — MCP 服务实现
- `src/tools/ListMcpResourcesTool/` — MCP 工具示例

---

### 第 7 篇：[多 Agent 协作系统](./07-multi-agent-collaboration-system)

**学习目标**：
- 理解多 Agent 协作的架构设计
- 掌握 Agent 生成和通信机制
- 学习协调器模式的实现

**关键代码文件**：
- `src/tools/AgentTool/AgentTool.tsx` — Agent 工具实现
- `src/coordinator/` — 协调器模式

---

### 第 8 篇：[实战：构建你自己的 Agent](./08-build-your-own-agent.md)

**学习目标**：
- 综合运用前面所学知识
- 从零开始设计并实现一个简易 Agent
- 获得实际动手经验

**关键代码参考**：
- 综合前面所有文档的代码示例
- `examples/simple-agent/` — TypeScript 版本实现
- `examples/simple-agent-python/` — Python 版本实现

> **说明**: 第 8 篇实战提供两个版本的 SimpleAgent 实现，功能对等，可任选其一学习。

---

## 学习方法建议

### 1. 按顺序学习

每篇文档都建立在前一篇的基础上，请按顺序学习。

### 2. 边读边思考

对于每个设计决策，问自己：
- 为什么这样设计？
- 有没有其他方案？
- 如果是我，会怎么实现？

### 3. 对照代码阅读

文档中引用的代码片段，建议在 IDE 中打开对应文件对照阅读，理解上下文。

### 4. 实践为主

理论理解后，务必动手实现一个简化版本，加深理解。

---

## 前置知识准备

### 必需

- **TypeScript 基础**：接口、泛型、类型推断
- **Python 基础**：装饰器、异步编程
- **JavaScript 运行时**：模块系统、事件循环

### 推荐

- **React 基础**：组件、Hooks、Context（用于理解 UI 部分）
- **Node.js/Bun**：包管理、模块解析

---

## 学习路径时间估算

| 阶段 | 文档 | 预计时间 |
|------|------|----------|
| 基础 | 第 1-2 篇 | 4-6 小时 |
| 核心 | 第 3-5 篇 | 8-12 小时 |
| 进阶 | 第 6-7 篇 | 6-8 小时 |
| 实战 | 第 8 篇 | 4-6 小时 |
| **总计** | | **22-32 小时** |

---

## 后续资源

完成本系列学习后，可进一步参考：

- [Anthropic 官方文档](https://code.claude.com/docs/)
- [Model Context Protocol 规范](https://modelcontextprotocol.io/)
- [Ink (React for CLI) 文档](https://github.com/vadimdemedes/ink)

---

**下一步**：开始 [第 1 篇 — LLM 基础与 Agent 概念](./01-llm-fundamentals-and-agent-concepts.md)
