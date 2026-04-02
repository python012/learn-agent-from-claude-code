# Agent 开发学习指南 — 完整索引

## 系列概述

本系列文档通过深入分析 Claude Code 源代码，引导有 Python 和 TypeScript 经验的工程师系统学习 Agent 开发。

---

## 文档导航

| 序号 | 文档 | 状态 | 核心内容 |
|------|------|------|----------|
| 00 | [学习路线总览](./00-学习路线总览.md) | ✅ 完成 | 系列介绍、学习路径、时间估算 |
| 01 | [LLM 基础与 Agent 概念](./01-LLM基础与Agent概念.md) | ✅ 完成 | API 交互、消息格式、工具调用、流式响应 |
| 02 | [Agent 架构入门](./02-Agent架构入门.md) | ✅ 完成 | 整体架构、状态管理、命令系统、数据流 |
| 03 | [工具系统详解](./03-工具系统详解.md) | ✅ 完成 | Tool 接口、工具实现、权限控制、自定义工具 |
| 04 | [会话与状态管理](./04-会话与状态管理.md) | ✅ 完成 | 会话存储、消息链、持久化、恢复机制 |
| 05 | [权限与安全控制](./05-权限与安全控制.md) | ✅ 完成 | 权限模式、规则系统、Auto Mode 分类器 |
| 06 | [MCP 与外部集成](./06-MCP与外部集成.md) | ✅ 完成 | MCP 协议、外部工具集成、资源管理 |
| 07 | [多 Agent 协作系统](./07-多Agent协作系统.md) | ✅ 完成 | Agent 生成、通信、协调器模式 |
| 08 | [实战：构建你自己的 Agent](./08-实战构建自己的Agent.md) | ✅ 完成 | 综合实践、从零实现完整 Agent 系统 |

---

## 快速查阅

### 按主题查找

#### LLM 与 API
- [第 1 篇](./01-LLM基础与Agent概念.md) — LLM API 基础
  - 消息格式（user/assistant/tool_result）
  - 工具调用（Tool Use）
  - 流式响应（Streaming）
  - Token 与计费

#### 架构设计
- [第 2 篇](./02-Agent架构入门.md) — Agent 架构入门
  - 整体架构图
  - 状态管理（AppState）
  - 命令系统
  - 数据流和执行路径

#### 工具开发
- [第 3 篇](./03-工具系统详解.md) — 工具系统详解
  - Tool 接口定义
  - buildTool 构建器
  - BashTool / FileWriteTool 示例
  - 自定义工具开发指南

#### 会话管理
- [第 4 篇](./04-会话与状态管理.md) — 会话与状态管理
  - JSONL 存储格式
  - 消息链组织
  - 会话恢复
  - Worktree 会话

#### 权限安全
- [第 5 篇](./05-权限与安全控制.md) — 权限与安全控制
  - 权限模式（6 种模式）
  - 规则系统（allow/deny/ask）
  - Auto Mode 分类器
  - 拒绝跟踪

---

## 核心代码位置索引

### 基础类型

| 类型 | 文件路径 | 用途 |
|------|----------|------|
| `Tool` | `src/Tool.ts` | 工具接口定义 |
| `Tools` | `src/tools.ts` | 工具集合类型 |
| `Message` | `src/types/message.ts` | 消息类型 |
| `AppState` | `src/state/AppStateStore.ts` | 全局状态 |
| `PermissionMode` | `src/types/permissions.ts` | 权限模式 |

### 核心模块

| 模块 | 文件路径 | 关键函数 |
|------|----------|----------|
| 工具注册 | `src/tools.ts` | `getTools()`, `assembleToolPool()` |
| API 调用 | `src/services/api/claude.ts` | `runQuery()` |
| 权限检查 | `src/utils/permissions/permissions.ts` | `hasPermissionsToUseTool()` |
| 状态管理 | `src/state/store.ts` | `createStore()` |
| 会话存储 | `src/utils/sessionStorage.ts` | `loadTranscriptFile()`, `cacheSessionTitle()` |

### 工具实现

| 工具 | 文件路径 | 特点 |
|------|----------|------|
| BashTool | `src/tools/BashTool/BashTool.tsx` | 命令执行、沙箱、后台任务 |
| FileWriteTool | `src/tools/FileWriteTool/FileWriteTool.ts` | 文件写入、diff 生成、LSP 通知 |
| AgentTool | `src/tools/AgentTool/AgentTool.tsx` | 子代理生成、任务管理 |
| FileReadTool | `src/tools/FileReadTool/FileReadTool.tsx` | 文件读取、内容限制 |

---

## 关键概念速查

### Agent 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│ Agent = LLM + Tools + State + Permissions                   │
│                                                             │
│ - LLM: 决策核心（理解任务、规划步骤、调用工具）                 │
│ - Tools: 能力扩展（Bash、文件操作、网络搜索等）                │
│ - State: 上下文记忆（消息历史、会话状态）                      │
│ - Permissions: 安全边界（什么能做、什么需要用户确认）           │
└─────────────────────────────────────────────────────────────┘
```

### 工具调用流程

```
1. 模型决定调用工具 → 返回 tool_use 内容块
2. 查找工具定义 → tools.find(t => t.name === toolName)
3. 验证输入 Schema → tool.inputSchema.parse(input)
4. 检查权限 → hasPermissionsToUseTool()
5. 执行工具 → tool.call(input, context)
6. 处理结果 → 限制大小、生成 UI、追加消息
7. 发送结果给 API → tool_result 消息
8. 模型继续回复
```

### 权限检查流程

```
1. 检查拒绝规则 → getDenyRuleForTool()
2. 检查询问规则 → getAskRuleForTool()
3. 工具特定检查 → tool.checkPermissions()
4. 安全检查 → 敏感路径保护
5. 模式转换
   - bypassPermissions → 允许
   - dontAsk → 拒绝
   - auto → 分类器决定
6. 检查允许规则 → toolAlwaysAllowedRule()
7. 默认 → 询问用户
```

---

## 学习路径建议

### 初学者路径（22-32 小时）

```
第 1 篇 (4-6h) → 第 2 篇 (4-6h) → 第 3 篇 (6-8h) →
第 4 篇 (4-6h) → 第 5 篇 (4-6h) → 实战篇 (4-6h)
```

### 进阶路径（针对有 LLM 经验者）

```
第 2 篇 (2-3h) → 第 3 篇 (4-5h) → 第 5 篇 (4-5h) →
第 6 篇 (MCP 集成) → 第 7 篇 (多 Agent 协作) → 第 8 篇 (实战)
```

### 专题深入

**工具开发专题**
- 第 3 篇：工具系统详解
- 阅读源码：`src/Tool.ts`, `src/tools/BashTool/BashTool.tsx`
- 实践：实现一个自定义工具

**权限系统专题**
- 第 5 篇：权限与安全控制
- 阅读源码：`src/utils/permissions/permissions.ts`
- 实践：配置权限规则

**架构设计专题**
- 第 2 篇：Agent 架构入门
- 第 4 篇：会话与状态管理
- 阅读源码：`src/state/AppState.tsx`, `src/main.tsx`

---

## 常用命令和配置

### MCP 服务器配置

```json
// ~/.claude/mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"]
    }
  }
}
```

### 权限规则配置

```json
// ~/.claude/settings.json
{
  "tools": {
    "alwaysAllow": [
      "Bash(git *)",
      "FileRead(src/**)"
    ],
    "alwaysDeny": [
      "Bash(rm -rf *)",
      "Bash(curl * | bash)"
    ]
  }
}
```

---

## 常用概念速查表

### LLM 基础概念

| 概念 | 说明 | 示例/值 |
|------|------|--------|
| **System Prompt** | 系统级指令，定义 Agent 角色和行为边界 | "You are Claude, an AI assistant..." |
| **User Message** | 用户发送的消息 | "帮我 refactor 这个函数" |
| **Assistant Message** | 模型生成的回复 | 包含文本和 tool_use |
| **Tool Use** | 模型请求调用工具 | `{name: "Bash", input: {command: "ls"}}` |
| **Tool Result** | 工具执行结果 | `{stdout: "file1.txt", exitCode: 0}` |
| **Context Window** | 模型能处理的最大 token 数 | 200K tokens (Claude 3.5) |
| **Streaming** | 流式输出，逐块返回响应 | `delta: {content: "..."}` |
| **Temperature** | 输出随机性 (0-1) | 0.7 (默认) |
| **Max Tokens** | 单次回复最大 token 数 | 8192 |

### Agent 架构概念

| 概念 | 说明 | 代码位置 |
|------|------|---------|
| **AppState** | 全局状态存储 | `src/state/AppState.ts` |
| **ToolUseContext** | 工具执行上下文 | `src/Tool.ts:158` |
| **PermissionMode** | 权限模式 (6 种) | `src/types/permissions.ts` |
| **Message Chain** | 消息历史链表 | `src/types/message.ts` |
| **Session Storage** | JSONL 持久化存储 | `src/utils/sessionStorage.ts` |
| **Query Loop** | 主查询循环 | `src/query.ts` |
| **REPL** | 交互式终端界面 | `src/replLauncher.tsx` |

### 工具系统概念

| 概念 | 说明 | 相关类型 |
|------|------|---------|
| **Tool Interface** | 工具接口定义 | `Tool<Input, Output, P>` |
| **ToolDef** | 工具定义（用于 buildTool） | `ToolDef<Input, Output, P>` |
| **buildTool()** | 工具构建器，填充默认方法 | `src/Tool.ts:757` |
| **ToolUseContext** | 工具执行时的上下文 | `src/Tool.ts:158` |
| **ToolProgressData** | 工具进度数据类型 | `src/types/tools.ts` |
| **ToolResult** | 工具返回结果包装 | `src/Tool.ts:324` |
| **isConcurrencySafe** | 是否可并发执行 | `Tool.isConcurrencySafe()` |
| **isReadOnly** | 是否为只读操作 | `Tool.isReadOnly()` |
| **toAutoClassifierInput** | 转为分类器输入 | `Tool.toAutoClassifierInput()` |

### 权限系统概念

| 概念 | 说明 | 值/类型 |
|------|------|--------|
| **PermissionMode** | 权限模式 | `default`, `auto`, `bypass`, `dontAsk`, `test`, `transcript` |
| **ToolPermissionContext** | 权限检查上下文 | `src/Tool.ts:122` |
| **PermissionResult** | 权限检查结果 | `{behavior: 'allow'/'deny'/'ask'}` |
| **Always Allow Rule** | 始终允许规则 | `Bash(git *)` |
| **Always Deny Rule** | 始终拒绝规则 | `Bash(rm -rf /)` |
| **Auto Mode Classifier** | 自动模式分类器 | `src/utils/permissions/autoModeClassifier.ts` |
| **Denial Tracking** | 拒绝计数跟踪 | `src/utils/permissions/denialTracking.ts` |

### MCP 概念

| 概念 | 说明 | 示例 |
|------|------|------|
| **MCP Server** | MCP 协议服务器 | `@modelcontextprotocol/server-github` |
| **MCP Client** | Claude Code 中的 MCP 客户端 | `src/services/mcp/client.ts` |
| **MCP Resource** | MCP 资源 URI | `github://repos/{owner}/{repo}` |
| **MCP Tool** | MCP 暴露的工具 | `github-create_issue` |
| **MCP Config** | MCP 配置文件 | `~/.claude/mcp.json` |
| **Stdio Transport** | 标准输入输出传输 | `{command, args, env}` |
| **SDK Transport** | 进程内 SDK 传输 | `InProcessTransport` |
| **MCP OAuth** | MCP OAuth 认证流程 | `src/services/mcp/oauth.ts` |

---

## 术语中英对照表

### LLM & API 术语

| 中文 | 英文 | 缩写/别名 |
|------|------|----------|
| 大型语言模型 | Large Language Model | LLM |
| 人工智能助手 | AI Assistant | Agent |
| 提示词 | Prompt | - |
| 系统提示词 | System Prompt | - |
| 补全/回复 | Completion | - |
| 令牌/词元 | Token | - |
| 上下文窗口 | Context Window | Context |
| 流式响应 | Streaming Response | Stream |
| 工具调用 | Tool Use / Tool Call | Function Calling |
| 消息格式 | Message Format | - |
| 内容块 | Content Block | - |
| 用户消息 | User Message | - |
| 助手消息 | Assistant Message | - |
| 工具结果 | Tool Result | - |

### 架构术语

| 中文 | 英文 | 缩写/别名 |
|------|------|----------|
| 状态管理 | State Management | AppState |
| 全局状态 | Global State | AppStateStore |
| 消息链 | Message Chain | MessageHistory |
| 会话存储 | Session Storage | Transcript Storage |
| 持久化 | Persistence | JSONL Storage |
| 恢复机制 | Recovery Mechanism | Session Restore |
| 交互式模式 | Interactive Mode | REPL |
| 打印模式 | Print Mode | Non-interactive |
| 后台任务 | Background Task | - |
| 前台任务 | Foreground Task | - |
| 中断处理 | Interrupt Handling | - |
| 清理处理器 | Cleanup Handler | - |

### 工具术语

| 中文 | 英文 | 缩写/别名 |
|------|------|----------|
| 工具 | Tool | - |
| 工具定义 | Tool Definition | ToolDef |
| 工具池 | Tool Pool | Tools |
| 工具注册 | Tool Registration | - |
| 工具实现 | Tool Implementation | - |
| 输入模式 | Input Schema | Zod Schema |
| 输出模式 | Output Schema | - |
| 只读工具 | Read-only Tool | - |
| 并发安全 | Concurrency Safe | - |
| 破坏性操作 | Destructive Operation | - |
| 工具进度 | Tool Progress | - |
| 工具结果截断 | Tool Result Truncation | - |
| 工具摘要 | Tool Summary | - |

### 权限术语

| 中文 | 英文 | 缩写/别名 |
|------|------|----------|
| 权限模式 | Permission Mode | - |
| 默认模式 | Default Mode | - |
| 自动模式 | Auto Mode | - |
|  bypass 模式 | Bypass Mode | - |
| 不询问模式 | Don't Ask Mode | - |
| 允许规则 | Allow Rule | Always Allow |
| 拒绝规则 | Deny Rule | Always Deny |
| 询问规则 | Ask Rule | - |
| 权限检查 | Permission Check | - |
| 分类器 | Classifier | Auto Mode Classifier |
| 拒绝跟踪 | Denial Tracking | - |
| 安全边界 | Security Boundary | - |

### MCP 术语

| 中文 | 英文 | 缩写/别名 |
|------|------|----------|
| 模型上下文协议 | Model Context Protocol | MCP |
| MCP 服务器 | MCP Server | - |
| MCP 客户端 | MCP Client | - |
| MCP 资源 | MCP Resource | - |
| MCP 工具 | MCP Tool | - |
| MCP 提示词 | MCP Prompt | - |
| 标准输入输出传输 | Stdio Transport | - |
| SDK 传输 | SDK Transport | In-Process |
| OAuth 认证 | OAuth Authentication | - |
| 官方注册表 | Official Registry | - |
| 资源模板 | Resource Template | - |

### 界面术语

| 中文 | 英文 | 缩写/别名 |
|------|------|----------|
| 终端用户界面 | Terminal User Interface | TUI |
| 命令行界面 | Command Line Interface | CLI |
| 交互式 | Interactive | REPL |
| 非交互式 | Non-interactive | Print Mode |
| 响应式 | Reactive | - |
| 组件 | Component | React Component |
| Hook | Hook | React Hook |
| 渲染 | Render | - |
| 进度指示器 | Progress Indicator | Spinner |
| 通知 | Notification | - |

---

## 术语表

| 术语 | 英文 | 解释 |
|------|------|------|
| Agent | Agent | 能够自主执行任务的 AI 系统 |
| 工具 | Tool | Agent 可调用的外部函数 |
| 提示词 | Prompt | 发送给 LLM 的指令 |
| 完成 | Completion | LLM 生成的回复 |
| Token | Token | LLM 处理的基本单位 |
| MCP | Model Context Protocol | 连接外部工具的协议标准 |
| TUI | Terminal User Interface | 终端用户界面 |
| CLI | Command Line Interface | 命令行界面 |

---

## 后续更新

本系列文档已全部完成：

- [x] 第 0 篇：学习路线总览
- [x] 第 1 篇：LLM 基础与 Agent 概念
- [x] 第 2 篇：Agent 架构入门
- [x] 第 3 篇：工具系统详解
- [x] 第 4 篇：会话与状态管理
- [x] 第 5 篇：权限与安全控制
- [x] 第 6 篇：MCP 与外部集成
- [x] 第 7 篇：多 Agent 协作系统
- [x] 第 8 篇：实战：构建你自己的 Agent

---

## 反馈与贡献

如有问题或建议，欢迎通过以下方式反馈：

- GitHub Issues: [项目地址](https://github.com/python012/learn-agent-from-claude-code)
- 文档讨论区

---

**开始学习**：[第 0 篇 — 学习路线总览](./00-学习路线总览.md)
