# 第 8 篇：实战 — 构建你自己的 Agent

## 学习目标

- 综合运用前 7 篇知识，从零构建一个完整的 Agent 系统
- 掌握 OpenAI API 的集成方法
- 实现工具系统、状态管理、会话持久化等核心模块
- 理解生产级 Agent 的关键设计决策

---

## 8.1 项目概述

### 8.1.1 目标系统

我们将构建一个名为 `SimpleAgent` 的轻量级 Agent 系统，它具备以下核心能力：

```
┌─────────────────────────────────────────────────────────────┐
│                      SimpleAgent                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   用户输入层                              │ │
│  │              (CLI / REPL / API)                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                                │
│                              ▼                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   核心引擎                                │ │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────────────┐  │ │
│  │  │ LLM 客户端  │  │ 工具管理器 │  │ 状态管理器           │  │ │
│  │  │ (OpenAI)  │  │           │  │ (会话/消息链)        │  │ │
│  │  └───────────┘  └───────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                                │
│              ┌───────────────┼───────────────┐               │
│              ▼               ▼               ▼               │
│     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐         │
│     │ Bash 工具   │ │ 文件工具    │ │ 网络工具    │         │
│     └─────────────┘ └─────────────┘ └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 8.1.2 技术栈选择

| 组件 | 技术选型 | 理由 |
|------|----------|------|
| 运行时 | Node.js 18+ / Python 3.10+ | 生态成熟，示例使用 TypeScript |
| LLM | OpenAI API | 行业标准，文档完善 |
| 语言 | TypeScript | 类型安全，与前文代码风格一致 |
| 构建工具 | tsup / tsc | 快速构建，配置简单 |

### 8.1.3 项目结构

```
simple-agent/
├── src/
│   ├── index.ts              # 入口文件
│   ├── agent/
│   │   ├── Agent.ts          # Agent 核心类
│   │   ├── LLMClient.ts      # OpenAI 客户端封装
│   │   └── types.ts          # 类型定义
│   ├── tools/
│   │   ├── Tool.ts           # Tool 接口定义
│   │   ├── BashTool.ts       # Bash 工具实现
│   │   ├── FileReadTool.ts   # 文件读取工具
│   │   ├── FileWriteTool.ts  # 文件写入工具
│   │   └── index.ts          # 工具注册
│   ├── state/
│   │   ├── StateStore.ts     # 状态管理
│   │   └── SessionStorage.ts # 会话持久化
│   ├── permissions/
│   │   ├── PermissionChecker.ts  # 权限检查
│   │   └── types.ts              # 权限类型
│   └── utils/
│       ├── logger.ts         # 日志工具
│       └── validators.ts     # 输入验证
├── tests/
│   ├── agent.test.ts
│   └── tools.test.ts
├── package.json
├── tsconfig.json
└── README.md
```

---

## 8.2 核心类型定义

### 8.2.1 消息类型

参考 Claude Code 的消息类型设计（`src/types/message.ts`），我们定义简化版本：

```typescript
// src/agent/types.ts

import { z } from 'zod'

// UUID 类型
export type UUID = string

// 消息内容块类型
export type TextContent = {
  type: 'text'
  text: string
}

export type ToolUseContent = {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, unknown>
}

export type ToolResultContent = {
  type: 'tool_result'
  tool_use_id: string
  content: string
  is_error?: boolean
}

// 消息内容联合类型
export type MessageContent = TextContent | ToolUseContent | ToolResultContent

// 用户消息参数
export type UserMessageParam = {
  role: 'user'
  content: string | MessageContent[]
}

// 助手消息参数
export type AssistantMessageParam = {
  role: 'assistant'
  content: string | MessageContent[]
  tool_calls?: ToolCall[]
}

// 工具调用
export type ToolCall = {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

// 工具结果消息参数
export type ToolMessageParam = {
  role: 'tool'
  tool_call_id: string
  content: string
}

// 完整消息类型
export type Message = {
  uuid: UUID
  parentUuid: UUID | null
  timestamp: number
} & (
  | { type: 'user'; message: UserMessageParam }
  | { type: 'assistant'; message: AssistantMessageParam }
  | { type: 'tool'; message: ToolMessageParam }
  | { type: 'system'; subtype: string; content: string }
)

// Zod Schema 用于验证
export const messageSchema = z.object({
  uuid: z.string(),
  parentUuid: z.string().nullable(),
  timestamp: z.number(),
  type: z.enum(['user', 'assistant', 'tool', 'system']),
  message: z.object({
    role: z.enum(['user', 'assistant', 'tool']),
    content: z.union([z.string(), z.array(z.object({}).passthrough())]),
  }).passthrough(),
})
```

### 8.2.2 工具接口定义

参考 `src/Tool.ts` 的设计，定义简化的 Tool 接口：

```typescript
// src/tools/Tool.ts

import { z } from 'zod'

// 工具输入/输出上下文
export type ToolContext = {
  cwd: string
  sessionId: string
  signal?: AbortSignal
}

// 工具调用结果
export type ToolResult = {
  content: string
  isError?: boolean
  metadata?: Record<string, unknown>
}

// 工具定义接口
export interface Tool {
  /** 工具名称（唯一标识） */
  readonly name: string

  /** 工具描述（用于系统提示） */
  readonly description: string

  /** 输入 Schema 验证 */
  readonly inputSchema: z.ZodType

  /** 是否并发安全 */
  readonly isConcurrencySafe: () => boolean

  /** 是否只读操作 */
  readonly isReadOnly: () => boolean

  /** 执行工具调用 */
  call(
    input: unknown,
    context: ToolContext,
  ): Promise<ToolResult>

  /** 可选：自定义权限检查 */
  checkPermissions?(
    input: unknown,
    context: ToolContext,
  ): Promise<PermissionCheckResult>
}

// 权限检查结果
export type PermissionCheckResult = {
  allowed: boolean
  reason?: string
  requiresUserConfirmation?: boolean
}

// buildTool 辅助函数（简化版）
export function buildTool<T extends z.ZodType>(
  definition: {
    name: string
    description: string
    inputSchema: T
    isConcurrencySafe?: () => boolean
    isReadOnly?: () => boolean
    checkPermissions?: Tool['checkPermissions']
    call: (
      input: z.infer<T>,
      context: ToolContext,
    ) => Promise<ToolResult>
  },
): Tool {
  return {
    name: definition.name,
    description: definition.description,
    inputSchema: definition.inputSchema,
    isConcurrencySafe: definition.isConcurrencySafe ?? (() => false),
    isReadOnly: definition.isReadOnly ?? (() => false),
    checkPermissions: definition.checkPermissions,
    async call(input: unknown, context: ToolContext): Promise<ToolResult> {
      // 验证输入
      const parsedInput = definition.inputSchema.parse(input)
      // 调用实际实现
      return definition.call(parsedInput, context)
    },
  }
}
```

---

## 8.3 OpenAI 客户端实现

### 8.3.1 客户端封装

```typescript
// src/agent/LLMClient.ts

import OpenAI from 'openai'
import { Message, AssistantMessageParam, UserMessageParam, ToolMessageParam, ToolUseContent } from './types.js'
import { Tool } from '../tools/Tool.js'

// OpenAI 工具定义
export type OpenAITool = {
  type: 'function'
  function: {
    name: string
    description: string
    parameters: Record<string, unknown>
  }
}

// LLM 响应结果
export type LLMResponse = {
  content: string | null
  toolCalls: ToolUseContent[]
  usage: {
    inputTokens: number
    outputTokens: number
    totalTokens: number
  }
}

// LLM 客户端配置
export type LLMClientConfig = {
  apiKey: string
  model: string
  maxTokens: number
  temperature?: number
}

export class LLMClient {
  private client: OpenAI
  private config: LLMClientConfig

  constructor(config: LLMClientConfig) {
    this.config = config
    this.client = new OpenAI({
      apiKey: config.apiKey,
    })
  }

  /**
   * 将内部工具转换为 OpenAI 工具格式
   */
  private convertTools(tools: Tool[]): OpenAITool[] {
    return tools.map(tool => {
      // 从 Zod Schema 提取 JSON Schema
      const jsonSchema = this.zodSchemaToJsonSchema(tool.inputSchema)
      return {
        type: 'function',
        function: {
          name: tool.name,
          description: tool.description,
          parameters: jsonSchema,
        },
      }
    })
  }

  /**
   * 简化的 Zod 到 JSON Schema 转换
   * 生产环境建议使用 zod-to-json-schema 库
   */
  private zodSchemaToJsonSchema(schema: z.ZodType): Record<string, unknown> {
    if (schema instanceof z.ZodObject) {
      const shape = schema.shape
      const properties: Record<string, unknown> = {}
      const required: string[] = []

      for (const [key, value] of Object.entries(shape)) {
        properties[key] = this.zodSchemaToJsonSchema(value as z.ZodType)
        if (!(value as z.ZodType).isOptional()) {
          required.push(key)
        }
      }

      return {
        type: 'object',
        properties,
        required,
      }
    }

    if (schema instanceof z.ZodString) {
      return { type: 'string' }
    }

    if (schema instanceof z.ZodNumber) {
      return { type: 'number' }
    }

    if (schema instanceof z.ZodBoolean) {
      return { type: 'boolean' }
    }

    if (schema instanceof z.ZodArray) {
      return {
        type: 'array',
        items: this.zodSchemaToJsonSchema(schema.element),
      }
    }

    if (schema instanceof z.ZodOptional) {
      return this.zodSchemaToJsonSchema(schema.unwrap())
    }

    // 默认返回 string
    return { type: 'string' }
  }

  /**
   * 将内部消息转换为 OpenAI 消息格式
   */
  private convertMessages(messages: Message[]): (UserMessageParam | AssistantMessageParam | ToolMessageParam)[] {
    const openaiMessages: (UserMessageParam | AssistantMessageParam | ToolMessageParam)[] = []

    for (const msg of messages) {
      if (msg.type === 'user') {
        openaiMessages.push(msg.message)
      } else if (msg.type === 'assistant' && msg.message.tool_calls?.length) {
        // 有工具调用的助手消息
        openaiMessages.push({
          role: 'assistant',
          content: null,
          tool_calls: msg.message.tool_calls,
        })
      } else if (msg.type === 'assistant') {
        openaiMessages.push(msg.message)
      } else if (msg.type === 'tool') {
        openaiMessages.push(msg.message)
      }
    }

    return openaiMessages
  }

  /**
   * 发送请求到 OpenAI API
   */
  async chat(
    messages: Message[],
    tools: Tool[] = [],
  ): Promise<LLMResponse> {
    const openaiMessages = this.convertMessages(messages)
    const openaiTools = this.convertTools(tools)

    const response = await this.client.chat.completions.create({
      model: this.config.model,
      messages: openaiMessages,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature ?? 0.7,
      tools: openaiTools.length > 0 ? openaiTools : undefined,
      tool_choice: openaiTools.length > 0 ? 'auto' : undefined,
    })

    const choice = response.choices[0]
    if (!choice) {
      throw new Error('No response from OpenAI')
    }

    // 提取工具调用
    const toolCalls: ToolUseContent[] = []
    if (choice.message.tool_calls) {
      for (const toolCall of choice.message.tool_calls) {
        toolCalls.push({
          type: 'tool_use',
          id: toolCall.id,
          name: toolCall.function.name,
          input: JSON.parse(toolCall.function.arguments),
        })
      }
    }

    return {
      content: choice.message.content,
      toolCalls,
      usage: {
        inputTokens: response.usage?.prompt_tokens ?? 0,
        outputTokens: response.usage?.completion_tokens ?? 0,
        totalTokens: response.usage?.total_tokens ?? 0,
      },
    }
  }
}
```

---

## 8.4 状态管理实现

### 8.4.1 状态存储

参考 `src/state/store.ts` 的 Redux-like 模式：

```typescript
// src/state/StateStore.ts

// 应用状态类型
export type AppState = {
  sessionId: string
  messages: Message[]
  pendingToolCalls: Array<{
    id: string
    name: string
    input: Record<string, unknown>
  }>
  isProcessing: boolean
  tokenUsage: {
    inputTokens: number
    outputTokens: number
  }
}

// 状态存储接口
export type StateStore = {
  getState: () => AppState
  setState: (updater: AppState | ((prev: AppState) => AppState)) => void
  subscribe: (listener: () => void) => () => void
}

// 创建状态存储
export function createStateStore(initialState?: Partial<AppState>): StateStore {
  let state: AppState = {
    sessionId: crypto.randomUUID(),
    messages: [],
    pendingToolCalls: [],
    isProcessing: false,
    tokenUsage: {
      inputTokens: 0,
      outputTokens: 0,
    },
    ...initialState,
  }

  const listeners = new Set<() => void>()

  return {
    getState: () => state,

    setState: (updater) => {
      const oldState = state
      const newState = typeof updater === 'function'
        ? (updater as (prev: AppState) => AppState)(oldState)
        : updater

      // 浅比较优化
      if (Object.is(oldState, newState)) {
        return
      }

      state = newState
      listeners.forEach(listener => listener())
    },

    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
```

### 8.4.2 React Context 集成（可选）

如果使用 React UI，可以创建 Context Provider：

```typescript
// src/state/StateContext.tsx

import React, { createContext, useContext, useSyncExternalStore } from 'react'
import type { StateStore, AppState } from './StateStore'

const StateContext = createContext<StateStore | null>(null)

export function StateProvider({
  store,
  children,
}: {
  store: StateStore
  children: React.ReactNode
}) {
  return (
    <StateContext.Provider value={store}>
      {children}
    </StateContext.Provider>
  )
}

export function useAppState(): AppState {
  const store = useContext(StateContext)
  if (!store) {
    throw new Error('useAppState must be used within StateProvider')
  }

  // 使用 useSyncExternalStore 实现响应式更新
  return useSyncExternalStore(
    store.subscribe,
    () => store.getState(),
    () => store.getState(),
  )
}
```

---

## 8.5 工具实现

### 8.5.1 Bash 工具

参考 `src/tools/BashTool/BashTool.tsx` 的实现：

```typescript
// src/tools/BashTool.ts

import { buildTool, ToolContext, ToolResult } from './Tool.js'
import { z } from 'zod'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

const inputSchema = z.object({
  command: z.string().describe('The bash command to execute'),
  description: z.string().optional().describe('Why you want to run this command'),
})

export const BashTool = buildTool({
  name: 'Bash',
  description: 'Execute bash commands in the terminal',
  inputSchema,

  isConcurrencySafe: () => false,
  isReadOnly: () => false,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { command } = input

    // 安全检查：危险命令拦截
    const dangerousPatterns = [
      /rm\s+(-[rf]+\s+)?\//,  // rm -rf /
      /curl.*\|\s*(bash|sh)/, // curl | bash
      /wget.*\|\s*(bash|sh)/, // wget | bash
      /:\(\)\{/,              // fork bomb
    ]

    for (const pattern of dangerousPatterns) {
      if (pattern.test(command)) {
        return {
          content: `Command blocked for security: ${command}`,
          isError: true,
          metadata: { blocked: true, reason: 'dangerous_command' },
        }
      }
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        cwd: context.cwd,
        timeout: 60000, // 60 秒超时
        maxBuffer: 10 * 1024 * 1024, // 10MB 输出限制
      })

      const result = stdout || stderr || '(no output)'

      return {
        content: result,
        isError: false,
        metadata: {
          exitCode: 0,
          commandLength: command.length,
        },
      }
    } catch (error) {
      const execError = error as Error & { code?: number; stdout?: string; stderr?: string }
      return {
        content: `Error executing command: ${execError.message}\n${execError.stderr || ''}`,
        isError: true,
        metadata: {
          exitCode: execError.code ?? 1,
          command,
        },
      }
    }
  },
})
```

### 8.5.2 文件读取工具

参考 `src/tools/FileReadTool/FileReadTool.tsx`：

```typescript
// src/tools/FileReadTool.ts

import { buildTool, ToolContext, ToolResult } from './Tool.js'
import { z } from 'zod'
import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import { join } from 'path'

const inputSchema = z.object({
  path: z.string().describe('Absolute or relative path to the file'),
  description: z.string().optional().describe('Why you need to read this file'),
})

export const FileReadTool = buildTool({
  name: 'FileRead',
  description: 'Read content from a file',
  inputSchema,

  isConcurrencySafe: () => true,
  isReadOnly: () => true,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { path: inputPath } = input

    // 路径解析和安全检查
    const resolvedPath = inputPath.startsWith('/')
      ? inputPath
      : join(context.cwd, inputPath)

    // 防止路径遍历攻击
    const normalizedPath = join(context.cwd, resolvedPath)
    if (!normalizedPath.startsWith(context.cwd)) {
      return {
        content: `Access denied: Path ${inputPath} is outside working directory`,
        isError: true,
        metadata: { blocked: true, reason: 'path_traversal' },
      }
    }

    // 检查文件存在
    if (!existsSync(normalizedPath)) {
      return {
        content: `File not found: ${normalizedPath}`,
        isError: true,
        metadata: { notFound: true },
      }
    }

    try {
      const content = await readFile(normalizedPath, 'utf-8')

      // 限制返回内容大小
      const maxLines = 2000
      const lines = content.split('\n')
      const truncatedContent = lines.length > maxLines
        ? lines.slice(0, maxLines).join('\n') + `\n\n... (${lines.length - maxLines} more lines)`
        : content

      return {
        content: truncatedContent,
        isError: false,
        metadata: {
          totalLines: lines.length,
          fileSize: Buffer.byteLength(content, 'utf-8'),
          path: normalizedPath,
        },
      }
    } catch (error) {
      const readError = error as Error
      return {
        content: `Error reading file: ${readError.message}`,
        isError: true,
        metadata: { error: readError.message },
      }
    }
  },
})
```

### 8.5.3 文件写入工具

参考 `src/tools/FileWriteTool/FileWriteTool.ts`：

```typescript
// src/tools/FileWriteTool.ts

import { buildTool, ToolContext, ToolResult } from './Tool.js'
import { z } from 'zod'
import { writeFile, mkdir } from 'fs/promises'
import { dirname, join } from 'path'
import { existsSync } from 'fs'

const inputSchema = z.object({
  path: z.string().describe('Absolute or relative path to the file'),
  content: z.string().describe('Content to write to the file'),
  description: z.string().optional().describe('Why you need to write this file'),
})

export const FileWriteTool = buildTool({
  name: 'FileWrite',
  description: 'Write content to a file (creates new file or overwrites existing)',
  inputSchema,

  isConcurrencySafe: () => false,
  isReadOnly: () => false,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { path: inputPath, content } = input

    // 路径解析和安全检查
    const resolvedPath = inputPath.startsWith('/')
      ? inputPath
      : join(context.cwd, inputPath)

    const normalizedPath = join(context.cwd, resolvedPath)
    if (!normalizedPath.startsWith(context.cwd)) {
      return {
        content: `Access denied: Path ${inputPath} is outside working directory`,
        isError: true,
        metadata: { blocked: true, reason: 'path_traversal' },
      }
    }

    // 敏感文件保护
    const sensitivePatterns = [
      /\.env$/,
      /package\.json$/,
      /tsconfig\.json$/,
      /\.git\/config$/,
    ]

    for (const pattern of sensitivePatterns) {
      if (pattern.test(normalizedPath)) {
        return {
          content: `Writing to ${normalizedPath} requires explicit permission`,
          isError: true,
          metadata: { blocked: true, reason: 'sensitive_file' },
        }
      }
    }

    try {
      // 确保目录存在
      const dir = dirname(normalizedPath)
      if (!existsSync(dir)) {
        await mkdir(dir, { recursive: true })
      }

      // 写入文件
      await writeFile(normalizedPath, content, 'utf-8')

      return {
        content: `Successfully wrote ${content.length} bytes to ${normalizedPath}`,
        isError: false,
        metadata: {
          bytesWritten: content.length,
          path: normalizedPath,
          created: !existsSync(normalizedPath),
        },
      }
    } catch (error) {
      const writeError = error as Error
      return {
        content: `Error writing file: ${writeError.message}`,
        isError: true,
        metadata: { error: writeError.message },
      }
    }
  },
})
```

### 8.5.4 工具注册

```typescript
// src/tools/index.ts

import { Tool } from './Tool.js'
import { BashTool } from './BashTool.js'
import { FileReadTool } from './FileReadTool.js'
import { FileWriteTool } from './FileWriteTool.js'

// 所有内置工具
export const builtInTools: Tool[] = [
  BashTool,
  FileReadTool,
  FileWriteTool,
]

// 根据权限上下文过滤工具
export function assembleToolPool(
  tools: Tool[],
  options?: {
    readOnlyOnly?: boolean
    excludeTools?: string[]
  },
): Tool[] {
  let filtered = tools

  // 只读模式过滤
  if (options?.readOnlyOnly) {
    filtered = filtered.filter(tool => tool.isReadOnly())
  }

  // 排除特定工具
  if (options?.excludeTools) {
    const excludeSet = new Set(options.excludeTools)
    filtered = filtered.filter(tool => !excludeSet.has(tool.name))
  }

  return filtered
}

// 获取默认工具池
export function getDefaultToolPool(): Tool[] {
  return assembleToolPool(builtInTools)
}
```

---

## 8.6 会话持久化

### 8.6.1 JSONL 存储

参考 `src/utils/sessionStorage.ts` 的实现：

```typescript
// src/state/SessionStorage.ts

import { Message } from '../agent/types.js'
import { readFile, writeFile, mkdir, appendFile } from 'fs/promises'
import { dirname, join } from 'path'
import { existsSync } from 'fs'

// JSONL 条目
export type TranscriptEntry = {
  type: string
  uuid: string
  parentUuid: string | null
  timestamp: number
  data: unknown
}

// 会话元数据
export type SessionMetadata = {
  sessionId: string
  title?: string
  createdAt: number
  updatedAt: number
  projectDir: string
}

export class SessionStorage {
  private sessionDir: string

  constructor(sessionDir: string) {
    this.sessionDir = sessionDir
  }

  /**
   * 获取会话文件路径
   */
  getSessionPath(sessionId: string): string {
    return join(this.sessionDir, `${sessionId}.jsonl`)
  }

  /**
   * 获取元数据路径
   */
  getMetadataPath(sessionId: string): string {
    return join(this.sessionDir, 'metadata', `${sessionId}.json`)
  }

  /**
   * 追加消息到会话日志
   */
  async appendMessage(sessionId: string, message: Message): Promise<void> {
    const logPath = this.getSessionPath(sessionId)

    // 确保目录存在
    await mkdir(dirname(logPath), { recursive: true })

    // 转换为 JSONL 条目
    const entry: TranscriptEntry = {
      type: message.type,
      uuid: message.uuid,
      parentUuid: message.parentUuid,
      timestamp: message.timestamp,
      data: message,
    }

    // 追加一行 JSON
    const line = JSON.stringify(entry) + '\n'
    await appendFile(logPath, line, 'utf-8')
  }

  /**
   * 加载会话日志
   */
  async loadSession(sessionId: string): Promise<Message[]> {
    const logPath = this.getSessionPath(sessionId)

    if (!existsSync(logPath)) {
      return []
    }

    const content = await readFile(logPath, 'utf-8')
    const lines = content.trim().split('\n').filter(line => line.length > 0)

    const messages: Message[] = []
    for (const line of lines) {
      try {
        const entry: TranscriptEntry = JSON.parse(line)
        messages.push(entry.data as Message)
      } catch (e) {
        // 跳过损坏的行
        console.warn(`Failed to parse line: ${e}`)
      }
    }

    return messages
  }

  /**
   * 保存会话元数据
   */
  async saveMetadata(metadata: SessionMetadata): Promise<void> {
    const metadataPath = this.getMetadataPath(metadata.sessionId)
    await mkdir(dirname(metadataPath), { recursive: true })
    await writeFile(metadataPath, JSON.stringify(metadata, null, 2), 'utf-8')
  }

  /**
   * 加载会话元数据
   */
  async loadMetadata(sessionId: string): Promise<SessionMetadata | null> {
    const metadataPath = this.getMetadataPath(sessionId)

    if (!existsSync(metadataPath)) {
      return null
    }

    const content = await readFile(metadataPath, 'utf-8')
    return JSON.parse(content) as SessionMetadata
  }

  /**
   * 提取会话标题
   */
  extractTitle(messages: Message[]): string | null {
    // 找到第一个用户消息作为标题
    for (const msg of messages) {
      if (msg.type === 'user') {
        const text = this.extractTextContent(msg.message.content)
        if (text && text.length > 0) {
          // 截断到 50 字符
          return text.length > 50 ? text.slice(0, 50) + '...' : text
        }
      }
    }
    return null
  }

  private extractTextContent(content: unknown): string {
    if (typeof content === 'string') {
      return content
    }
    if (Array.isArray(content)) {
      return content
        .filter(c => c.type === 'text')
        .map(c => c.text)
        .join(' ')
    }
    return ''
  }
}
```

---

## 8.7 权限系统

### 8.7.1 权限模式定义

参考 `src/utils/permissions/permissions.ts` 的设计：

```typescript
// src/permissions/types.ts

import { z } from 'zod'

// 权限模式
export type PermissionMode =
  | 'default'        // 默认：询问用户
  | 'plan'          // 计划模式
  | 'acceptEdits'    // 接受编辑（自动允许文件修改）
  | 'bypassPermissions' // 完全跳过权限检查
  | 'dontAsk'        // 不询问（自动拒绝）
  | 'auto'           // AI 自动分类

// 规则类型
export type RuleType = 'allow' | 'deny' | 'ask'

// 权限规则
export type PermissionRule = {
  type: RuleType
  toolName: string
  pattern?: string  // 支持通配符匹配
  description?: string
}

// 权限检查结果
export type PermissionCheck = {
  allowed: boolean
  requiresConfirmation: boolean
  reason?: string
  mode: PermissionMode
}

// 权限规则值解析
export function permissionRuleValueFromString(
  value: string,
): { toolName: string; ruleContent?: string } {
  // 解析 "Bash(git *)" 格式
  const match = value.match(/^(\w+)(?:\((.*)\))?$/)
  if (match) {
    return {
      toolName: match[1]!,
      ruleContent: match[2],
    }
  }
  return { toolName: value }
}
```

### 8.7.2 权限检查器

```typescript
// src/permissions/PermissionChecker.ts

import { Tool } from '../tools/Tool.js'
import { ToolContext } from '../tools/Tool.js'
import { PermissionMode, PermissionRule, PermissionCheck } from './types.js'
import { permissionRuleValueFromString } from './types.js'

export class PermissionChecker {
  private mode: PermissionMode
  private allowRules: PermissionRule[]
  private denyRules: PermissionRule[]
  private askRules: PermissionRule[]

  constructor(options: {
    mode: PermissionMode
    allowRules?: string[]
    denyRules?: string[]
    askRules?: string[]
  }) {
    this.mode = options.mode
    this.allowRules = this.parseRules(options.allowRules ?? [])
    this.denyRules = this.parseRules(options.denyRules ?? [])
    this.askRules = this.parseRules(options.askRules ?? [])
  }

  private parseRules(rules: string[]): PermissionRule[] {
    return rules.map(ruleStr => {
      const { toolName, ruleContent } = permissionRuleValueFromString(ruleStr)
      return {
        type: 'allow', // 类型由调用方决定
        toolName,
        pattern: ruleContent,
      }
    })
  }

  /**
   * 检查工具调用权限
   */
  async checkPermission(
    tool: Tool,
    input: unknown,
    context: ToolContext,
  ): Promise<PermissionCheck> {
    // 1. bypassPermissions 模式：总是允许
    if (this.mode === 'bypassPermissions') {
      return {
        allowed: true,
        requiresConfirmation: false,
        reason: 'bypassPermissions mode',
        mode: this.mode,
      }
    }

    // 2. dontAsk 模式：总是拒绝
    if (this.mode === 'dontAsk') {
      return {
        allowed: false,
        requiresConfirmation: false,
        reason: 'dontAsk mode',
        mode: this.mode,
      }
    }

    // 3. 检查拒绝规则
    if (this.matchesRule(this.denyRules, tool.name, input)) {
      return {
        allowed: false,
        requiresConfirmation: false,
        reason: `Denied by rule: ${tool.name}`,
        mode: this.mode,
      }
    }

    // 4. 检查允许规则
    if (this.matchesRule(this.allowRules, tool.name, input)) {
      return {
        allowed: true,
        requiresConfirmation: false,
        reason: `Allowed by rule: ${tool.name}`,
        mode: this.mode,
      }
    }

    // 5. 检查询问规则
    if (this.matchesRule(this.askRules, tool.name, input)) {
      return {
        allowed: false,
        requiresConfirmation: true,
        reason: `Requires confirmation: ${tool.name}`,
        mode: this.mode,
      }
    }

    // 6. 根据模式决定默认行为
    switch (this.mode) {
      case 'acceptEdits':
        if (tool.isReadOnly()) {
          return {
            allowed: true,
            requiresConfirmation: false,
            reason: 'Read-only tool in acceptEdits mode',
            mode: this.mode,
          }
        }
        return {
          allowed: false,
          requiresConfirmation: true,
          reason: 'Edit requires confirmation',
          mode: this.mode,
        }

      case 'plan':
        // 计划模式允许特定工具
        const planAllowedTools = ['FileRead', 'Glob', 'Grep']
        if (planAllowedTools.includes(tool.name)) {
          return {
            allowed: true,
            requiresConfirmation: false,
            reason: 'Allowed in plan mode',
            mode: this.mode,
          }
        }
        return {
          allowed: false,
          requiresConfirmation: true,
          reason: 'Plan mode requires confirmation for this tool',
          mode: this.mode,
        }

      case 'auto':
        // TODO: AI 分类器
        return {
          allowed: false,
          requiresConfirmation: true,
          reason: 'Auto mode requires AI classification',
          mode: this.mode,
        }

      default:
        // default 模式：默认询问
        return {
          allowed: false,
          requiresConfirmation: true,
          reason: 'Default mode requires confirmation',
          mode: this.mode,
        }
    }
  }

  private matchesRule(
    rules: PermissionRule[],
    toolName: string,
    input: unknown,
  ): boolean {
    for (const rule of rules) {
      if (rule.toolName === toolName || rule.toolName === '*') {
        if (rule.pattern) {
          // 简单通配符匹配
          const regex = new RegExp(rule.pattern.replace(/\*/g, '.*'))
          const inputStr = JSON.stringify(input)
          if (regex.test(inputStr)) {
            return true
          }
        } else {
          return true
        }
      }
    }
    return false
  }

  updateMode(mode: PermissionMode): void {
    this.mode = mode
  }

  addRule(type: RuleType, rule: string): void {
    const parsed = this.parseRules([rule])[0]!
    parsed.type = type

    switch (type) {
      case 'allow':
        this.allowRules.push(parsed)
        break
      case 'deny':
        this.denyRules.push(parsed)
        break
      case 'ask':
        this.askRules.push(parsed)
        break
    }
  }
}
```

---

## 8.8 Agent 核心实现

### 8.8.1 Agent 主类

综合前面所有组件，实现 Agent 核心：

```typescript
// src/agent/Agent.ts

import { Message, UUID, AssistantMessageParam, ToolUseContent } from './types.js'
import { LLMClient } from './LLMClient.js'
import { Tool, ToolContext, ToolResult } from '../tools/Tool.js'
import { StateStore, createStateStore } from '../state/StateStore.js'
import { SessionStorage } from '../state/SessionStorage.js'
import { PermissionChecker } from '../permissions/PermissionChecker.js'

// Agent 配置
export type AgentConfig = {
  sessionId?: string
  cwd: string
  apiKey: string
  model: string
  maxTokens: number
  permissionMode?: 'default' | 'plan' | 'acceptEdits' | 'bypassPermissions' | 'dontAsk' | 'auto'
  allowRules?: string[]
  denyRules?: string[]
}

// Agent 运行结果
export type AgentResult = {
  messages: Message[]
  tokenUsage: {
    inputTokens: number
    outputTokens: number
  }
}

export class Agent {
  private llmClient: LLMClient
  private state: StateStore
  private sessionStorage: SessionStorage
  private permissionChecker: PermissionChecker
  private tools: Map<string, Tool>
  private config: AgentConfig

  constructor(config: AgentConfig) {
    this.config = config

    // 初始化 LLM 客户端
    this.llmClient = new LLMClient({
      apiKey: config.apiKey,
      model: config.model,
      maxTokens: config.maxTokens,
    })

    // 初始化状态存储
    this.state = createStateStore()

    // 初始化会话存储
    this.sessionStorage = new SessionStorage(
      join(process.cwd(), '.claude', 'sessions'),
    )

    // 初始化权限检查器
    this.permissionChecker = new PermissionChecker({
      mode: config.permissionMode ?? 'default',
      allowRules: config.allowRules,
      denyRules: config.denyRules,
    })

    // 初始化工具映射
    this.tools = new Map()

    // 如果有 sessionId，加载历史消息
    if (config.sessionId) {
      this.loadSession(config.sessionId)
    }
  }

  /**
   * 注册工具
   */
  registerTool(tool: Tool): void {
    this.tools.set(tool.name, tool)
  }

  /**
   * 注册多个工具
   */
  registerTools(tools: Tool[]): void {
    for (const tool of tools) {
      this.registerTool(tool)
    }
  }

  /**
   * 加载历史会话
   */
  async loadSession(sessionId: string): Promise<void> {
    const messages = await this.sessionStorage.loadSession(sessionId)
    this.state.setState(prev => ({
      ...prev,
      messages,
    }))
  }

  /**
   * 保存会话
   */
  async saveSession(): Promise<void> {
    const state = this.state.getState()
    const sessionId = state.sessionId

    // 保存消息
    for (const message of state.messages) {
      await this.sessionStorage.appendMessage(sessionId, message)
    }

    // 保存元数据
    const title = this.sessionStorage.extractTitle(state.messages)
    await this.sessionStorage.saveMetadata({
      sessionId,
      title: title ?? undefined,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      projectDir: this.config.cwd,
    })
  }

  /**
   * 添加用户消息
   */
  addUserMessage(content: string): void {
    const message: Message = {
      uuid: crypto.randomUUID(),
      parentUuid: this.getLastMessageUuid(),
      timestamp: Date.now(),
      type: 'user',
      message: {
        role: 'user',
        content,
      },
    }

    this.state.setState(prev => ({
      ...prev,
      messages: [...prev.messages, message],
    }))
  }

  /**
   * 添加助手消息
   */
  addAssistantMessage(content: string, toolCalls?: ToolUseContent[]): void {
    const message: Message = {
      uuid: crypto.randomUUID(),
      parentUuid: this.getLastMessageUuid(),
      timestamp: Date.now(),
      type: 'assistant',
      message: {
        role: 'assistant',
        content,
        tool_calls: toolCalls?.map(tc => ({
          id: tc.id,
          type: 'function',
          function: {
            name: tc.name,
            arguments: JSON.stringify(tc.input),
          },
        })),
      },
    }

    this.state.setState(prev => ({
      ...prev,
      messages: [...prev.messages, message],
    }))
  }

  /**
   * 添加工具结果消息
   */
  addToolResultMessage(toolCallId: string, content: string, isError = false): void {
    const message: Message = {
      uuid: crypto.randomUUID(),
      parentUuid: this.getLastMessageUuid(),
      timestamp: Date.now(),
      type: 'tool',
      message: {
        role: 'tool',
        tool_call_id: toolCallId,
        content,
      },
    }

    this.state.setState(prev => ({
      ...prev,
      messages: [...prev.messages, message],
    }))
  }

  /**
   * 获取最后一条消息的 UUID
   */
  private getLastMessageUuid(): UUID | null {
    const state = this.state.getState()
    return state.messages.length > 0 ? state.messages[state.messages.length - 1]!.uuid : null
  }

  /**
   * 执行工具调用
   */
  private async executeToolCall(
    toolCall: ToolUseContent,
  ): Promise<ToolResult> {
    const tool = this.tools.get(toolCall.name)
    if (!tool) {
      return {
        content: `Tool not found: ${toolCall.name}`,
        isError: true,
      }
    }

    const state = this.state.getState()
    const context: ToolContext = {
      cwd: this.config.cwd,
      sessionId: state.sessionId,
    }

    // 权限检查
    const permissionCheck = await this.permissionChecker.checkPermission(
      tool,
      toolCall.input,
      context,
    )

    if (!permissionCheck.allowed) {
      return {
        content: `Permission denied: ${permissionCheck.reason}`,
        isError: true,
        metadata: { permissionDenied: true },
      }
    }

    // 执行工具
    try {
      return await tool.call(toolCall.input, context)
    } catch (error) {
      const err = error as Error
      return {
        content: `Error executing tool: ${err.message}`,
        isError: true,
        metadata: { error: err.message },
      }
    }
  }

  /**
   * 运行 Agent 主循环
   */
  async run(): Promise<AgentResult> {
    const state = this.state.getState()
    const toolList = Array.from(this.tools.values())

    this.state.setState(prev => ({
      ...prev,
      isProcessing: true,
    }))

    try {
      let maxIterations = 10
      let iteration = 0

      while (iteration < maxIterations) {
        iteration++

        // 1. 调用 LLM
        const messages = this.state.getState().messages
        const response = await this.llmClient.chat(messages, toolList)

        // 更新 token 使用
        this.state.setState(prev => ({
          ...prev,
          tokenUsage: {
            inputTokens: prev.tokenUsage.inputTokens + response.usage.inputTokens,
            outputTokens: prev.tokenUsage.outputTokens + response.usage.outputTokens,
          },
        }))

        // 2. 处理响应
        if (response.content) {
          this.addAssistantMessage(response.content)
        }

        if (response.toolCalls.length > 0) {
          this.addAssistantMessage('', response.toolCalls)

          // 3. 执行工具调用
          for (const toolCall of response.toolCalls) {
            const result = await this.executeToolCall(toolCall)
            this.addToolResultMessage(toolCall.id, result.content, result.isError)
          }

          // 继续循环，让 LLM 处理工具结果
          continue
        }

        // 没有工具调用，结束循环
        break
      }

      // 保存会话
      await this.saveSession()

      const finalState = this.state.getState()
      return {
        messages: finalState.messages,
        tokenUsage: finalState.tokenUsage,
      }
    } finally {
      this.state.setState(prev => ({
        ...prev,
        isProcessing: false,
      }))
    }
  }

  /**
   * 获取当前状态
   */
  getState() {
    return this.state.getState()
  }

  /**
   * 订阅状态变化
   */
  subscribeState(listener: () => void) {
    return this.state.subscribe(listener)
  }
}

// 辅助函数
import { join } from 'path'
```

---

## 8.9 使用示例

### 8.9.1 基本用法

```typescript
// examples/basic-usage.ts

import { Agent } from '../src/agent/Agent.js'
import { builtInTools } from '../src/tools/index.js'

async function main() {
  // 创建 Agent 实例
  const agent = new Agent({
    cwd: process.cwd(),
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4o',
    maxTokens: 4096,
    permissionMode: 'bypassPermissions',
  })

  // 注册工具
  agent.registerTools(builtInTools)

  // 添加用户消息
  agent.addUserMessage('创建一个简单的 TypeScript 项目，包含 package.json 和 tsconfig.json')

  // 运行 Agent
  const result = await agent.run()

  // 输出结果
  console.log('Token Usage:')
  console.log(`  Input:  ${result.tokenUsage.inputTokens}`)
  console.log(`  Output: ${result.tokenUsage.outputTokens}`)
  console.log('\nMessages:')
  for (const msg of result.messages) {
    console.log(`[${msg.type}] ${JSON.stringify(msg.message).slice(0, 100)}...`)
  }
}

main().catch(console.error)
```

### 8.9.2 交互式 REPL

```typescript
// examples/repl.ts

import * as readline from 'readline'
import { Agent } from '../src/agent/Agent.js'
import { builtInTools } from '../src/tools/index.js'

async function main() {
  const agent = new Agent({
    cwd: process.cwd(),
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4o',
    maxTokens: 4096,
    permissionMode: 'acceptEdits',
  })

  agent.registerTools(builtInTools)

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  })

  console.log('SimpleAgent REPL - Type your message or "quit" to exit')
  console.log('=' .repeat(50))

  const prompt = () => {
    rl.question('> ', async (input) => {
      if (input.toLowerCase() === 'quit' || input.toLowerCase() === 'exit') {
        rl.close()
        return
      }

      if (input.trim()) {
        agent.addUserMessage(input)

        try {
          const result = await agent.run()
          const lastMessage = result.messages[result.messages.length - 1]
          if (lastMessage?.type === 'assistant') {
            const content = lastMessage.message.content
            console.log(typeof content === 'string' ? content : JSON.stringify(content))
          }
        } catch (error) {
          console.error('Error:', error)
        }
      }

      prompt()
    })
  }

  prompt()
}

main().catch(console.error)
```

### 8.9.3 自定义工具示例

```typescript
// examples/custom-tool.ts

import { buildTool, ToolContext, ToolResult } from '../src/tools/Tool.js'
import { z } from 'zod'
import { Agent } from '../src/agent/Agent.js'

// 创建一个 Weather 工具
const WeatherTool = buildTool({
  name: 'GetWeather',
  description: 'Get current weather for a city',
  inputSchema: z.object({
    city: z.string().describe('City name'),
  }),

  isConcurrencySafe: () => true,
  isReadOnly: () => true,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { city } = input
    // 模拟天气数据
    const weather = ['sunny', 'cloudy', 'rainy', 'windy'][
      Math.floor(Math.random() * 4)
    ]
    const temperature = Math.floor(Math.random() * 30) + 10

    return {
      content: `The weather in ${city} is ${weather}, temperature: ${temperature}°C`,
      isError: false,
      metadata: { city, weather, temperature },
    }
  },
})

async function main() {
  const agent = new Agent({
    cwd: process.cwd(),
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4o',
    maxTokens: 4096,
    permissionMode: 'bypassPermissions',
  })

  // 注册内置工具和自定义工具
  agent.registerTools([
    ...builtInTools,
    WeatherTool,
  ])

  agent.addUserMessage('北京今天的天气怎么样？')

  const result = await agent.run()
  console.log(JSON.stringify(result, null, 2))
}

main().catch(console.error)
```

---

## 8.10 完整项目代码

### 8.10.1 package.json

```json
{
  "name": "simple-agent",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsup src/index.ts --format esm --dts",
    "dev": "tsup src/index.ts --format esm --watch",
    "example:basic": "tsx examples/basic-usage.ts",
    "example:repl": "tsx examples/repl.ts",
    "example:custom-tool": "tsx examples/custom-tool.ts",
    "test": "vitest"
  },
  "dependencies": {
    "openai": "^4.28.0",
    "zod": "^3.22.4"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "tsup": "^8.0.1",
    "tsx": "^4.7.0",
    "typescript": "^5.3.3",
    "vitest": "^1.3.1"
  }
}
```

### 8.10.2 tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "esModuleInterop": true,
    "strict": true,
    "skipLibCheck": true,
    "declaration": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### 8.10.3 src/index.ts

```typescript
// src/index.ts - 统一导出

// Agent 核心
export { Agent } from './agent/Agent.js'
export { LLMClient } from './agent/LLMClient.js'
export type { AgentConfig, AgentResult } from './agent/Agent.js'
export type { LLMClientConfig, LLMResponse } from './agent/LLMClient.js'

// 类型定义
export type {
  Message,
  UUID,
  MessageContent,
  UserMessageParam,
  AssistantMessageParam,
  ToolMessageParam,
  ToolUseContent,
} from './agent/types.js'

// 工具系统
export { buildTool } from './tools/Tool.js'
export type { Tool, ToolContext, ToolResult } from './tools/Tool.js'
export { builtInTools, assembleToolPool, getDefaultToolPool } from './tools/index.js'

// 状态管理
export { createStateStore } from './state/StateStore.js'
export type { StateStore, AppState } from './state/StateStore.js'
export { SessionStorage } from './state/SessionStorage.js'
export type { SessionMetadata } from './state/SessionStorage.js'

// 权限系统
export { PermissionChecker } from './permissions/PermissionChecker.js'
export type {
  PermissionMode,
  PermissionRule,
  PermissionCheck,
} from './permissions/types.js'

// 内置工具
export { BashTool } from './tools/BashTool.js'
export { FileReadTool } from './tools/FileReadTool.js'
export { FileWriteTool } from './tools/FileWriteTool.js'
```

---

## 8.11 扩展阅读

### 8.11.1 参考 Claude Code 的高级特性

1. **多 Agent 协作** - 参考 `src/tools/AgentTool/AgentTool.tsx` 和 `src/coordinator/coordinatorMode.ts`
2. **MCP 集成** - 参考 `src/services/mcp/client.ts`
3. **流式响应** - 参考 `src/services/api/claude.ts`
4. **计划模式** - 参考 `src/tools/EnterPlanModeTool/EnterPlanModeTool.ts`

### 8.11.2 进一步优化方向

1. **流式输出** - 使用 OpenAI 的 streaming API 实现流式响应
2. **函数调用优化** - 使用 OpenAI 的 function calling 优化
3. **上下文压缩** - 实现消息历史压缩和摘要
4. **并发工具执行** - 支持并发安全的工具并行执行
5. **错误恢复** - 实现工具调用失败后的自动重试

---

## 8.12 课后练习

1. **基础练习**：
   - 运行 REPL 示例，尝试让 Agent 创建文件
   - 添加一个新的内置工具（如 `GlobTool`）
   - 配置权限规则，限制某些命令的执行

2. **进阶练习**：
   - 实现流式响应，在终端逐字输出 Agent 回复
   - 添加消息摘要功能，压缩长对话历史
   - 实现简单的 Auto Mode 分类器

3. **综合练习**：
   - 设计一个多 Agent 系统，包含研究 Agent、实现 Agent 和测试 Agent
   - 为每个 Agent 配置不同的工具集和权限模式
   - 实现 Agent 间的消息传递和结果合成

---

## 系列总结

恭喜完成整个 Agent 开发学习系列！你现在掌握了：

1. **LLM API 基础** - 消息格式、工具调用、流式响应
2. **Agent 架构** - 状态管理、命令系统、数据流
3. **工具系统** - Tool 接口、权限控制、自定义工具
4. **会话管理** - JSONL 存储、消息链、持久化恢复
5. **权限安全** - 权限模式、规则系统、Auto Mode
6. **外部集成** - MCP 协议、OAuth 认证、资源管理
7. **多 Agent 协作** - 协调器模式、工具过滤、生命周期
8. **实战能力** - 从零构建完整的 Agent 系统

继续深入的最佳方式是：
- 阅读 Claude Code 完整源代码
- 实践构建自己的 Agent 项目
- 参与开源项目，学习社区最佳实践

祝你在 Agent 开发的道路上不断进步！
