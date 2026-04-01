# 第 7 篇：多 Agent 协作系统

## 学习目标

- 理解多 Agent 协作的架构设计
- 掌握 Agent 生成和通信机制
- 学习协调器模式（Coordinator Mode）的实现
- 了解工具过滤和权限隔离

---

## 7.1 多 Agent 架构概述

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                               │
│                   (PromptInput / REPL)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     协调器 (Coordinator)                     │
│  - 接收用户请求                                              │
│  - 规划和分配任务                                            │
│  - 合成工人结果                                              │
│  - 与用户通信                                                │
└─────────────────────────────────────────────────────────────┘
                    │                   │
          ┌─────────┴─────────┐   ┌─────┴─────┐
          ▼                   ▼   ▼           ▼
┌─────────────┐       ┌─────────────┐ ┌─────────────┐
│  Worker 1   │       │  Worker 2   │ │  Worker 3   │
│  (研究)     │       │  (实现)     │ │  (测试)     │
└─────────────┘       └─────────────┘ └─────────────┘
```

### Agent 类型

```typescript
// 来自 src/tools/AgentTool/constants.ts
export const AGENT_TOOL_NAME = 'Agent'

// Agent 工具允许生成的 Agent 类型
export const ALLOWED_AGENT_TYPES = [
  'general-purpose',  // 通用 Agent
  'worker',           // 工人 Agent（协调器模式）
  'researcher',       // 研究 Agent
  'reviewer',         // 审查 Agent
] as const
```

---

## 7.2 Agent 工具定义

### 输入输出 Schema

```typescript
// 来自 src/tools/AgentTool/AgentTool.tsx
import { z } from 'zod/v4'
import { lazySchema } from '../../utils/lazySchema.js'

// 基础输入 Schema
const baseInputSchema = lazySchema(() => z.object({
  description: z.string().describe('A short (3-5 word) description of the task'),
  prompt: z.string().describe('The task for the agent to perform'),
  subagent_type: z.string().optional()
    .describe('The type of specialized agent to use'),
  model: z.enum(['sonnet', 'opus', 'haiku']).optional()
    .describe('Optional model override for this agent'),
  run_in_background: z.boolean().optional()
    .describe('Set to true to run this agent in the background'),
}))

// 多 Agent 参数（KAIROS 特性）
const multiAgentInputSchema = z.object({
  name: z.string().optional()
    .describe('Name for the spawned agent. Makes it addressable via SendMessage'),
  team_name: z.string().optional()
    .describe('Team name for spawning'),
  mode: permissionModeSchema().optional()
    .describe('Permission mode for spawned teammate'),
})

// 完整 Schema
const fullInputSchema = lazySchema(() =>
  baseInputSchema().merge(multiAgentInputSchema).extend({
    isolation: z.enum(['worktree', 'remote']).optional()
      .describe('Isolation mode'),
    cwd: z.string().optional()
      .describe('Absolute path to run the agent in'),
  })
)
```

### Agent 工具核心逻辑

```typescript
// 来自 src/tools/AgentTool/AgentTool.tsx — 简化的 call 方法
export const AgentTool = buildTool({
  name: AGENT_TOOL_NAME,

  async call(input, context, canUseTool, parentMessage, onProgress) {
    const appState = context.getAppState()
    const agentId = createAgentId()

    // 1. 解析 Agent 类型
    const agentType = input.subagent_type || 'general-purpose'
    const isForkSubagent = isForkSubagentEnabled() && agentType === FORK_AGENT

    // 2. 获取 Agent 定义
    const agentDefinitions = await getAgentDefinitionsWithOverrides(
      appState.agentDefinitions,
      input.subagent_type,
    )
    const agentDefinition = agentDefinitions.find(
      a => a.agentType === agentType
    ) || GENERAL_PURPOSE_AGENT

    // 3. 解析 Agent 工具列表
    const resolvedTools = resolveAgentTools(
      agentDefinition,
      context.options.tools,
      isAsync = true,
    )

    // 4. 构建系统提示
    const systemPrompt = await buildAgentSystemPrompt(
      agentDefinition,
      resolvedTools.resolvedTools,
      context,
    )

    // 5. 构建消息历史
    const messages = isForkSubagent
      ? buildForkedMessages(context.messages, agentDefinition)
      : [createUserMessage(input.prompt)]

    // 6. 运行 Agent
    const result = await runAsyncAgentLifecycle(
      {
        agentId,
        agentType: agentDefinition.agentType,
        model: getAgentModel(agentDefinition, input.model, appState),
        systemPrompt,
        messages,
        tools: resolvedTools.resolvedTools,
      },
      {
        context,
        input,
        parentMessage,
        onProgress,
      },
    )

    return { data: result }
  },
})
```

---

## 7.3 工具过滤机制

### Agent 工具过滤

```typescript
// 来自 src/tools/AgentTool/agentToolUtils.ts
const ALL_AGENT_DISALLOWED_TOOLS = new Set([
  'TaskCreateTool',
  'TaskUpdateTool',
  'TaskListTool',
  // ... 不允许 Agent 使用的工具
])

const CUSTOM_AGENT_DISALLOWED_TOOLS = new Set([
  'WebBrowserTool',
  // ... 不允许自定义 Agent 使用的工具
])

const ASYNC_AGENT_ALLOWED_TOOLS = new Set([
  'Bash',
  'FileRead',
  'FileEdit',
  'FileWrite',
  'Grep',
  'Glob',
  'Agent',  // 允许生成子 Agent
  // ... 允许异步 Agent 使用的工具
])

/**
 * 过滤 Agent 可用的工具
 */
export function filterToolsForAgent({
  tools,
  isBuiltIn,
  isAsync = false,
  permissionMode,
}: {
  tools: Tools
  isBuiltIn: boolean
  isAsync?: boolean
  isAsync?: boolean
  permissionMode?: PermissionMode
}): Tools {
  return tools.filter(tool => {
    // 允许 MCP 工具
    if (tool.name.startsWith('mcp__')) {
      return true
    }

    // 允许计划模式下的 ExitPlanMode
    if (
      toolMatchesName(tool, EXIT_PLAN_MODE_V2_TOOL_NAME) &&
      permissionMode === 'plan'
    ) {
      return true
    }

    // 所有 Agent 禁止的工具
    if (ALL_AGENT_DISALLOWED_TOOLS.has(tool.name)) {
      return false
    }

    // 自定义 Agent 额外禁止的工具
    if (!isBuiltIn && CUSTOM_AGENT_DISALLOWED_TOOLS.has(tool.name)) {
      return false
    }

    // 异步 Agent 只允许特定工具
    if (isAsync && !ASYNC_AGENT_ALLOWED_TOOLS.has(tool.name)) {
      // 允许在进程队友生成同步子 Agent
      if (isAgentSwarmsEnabled() && isInProcessTeammate()) {
        if (toolMatchesName(tool, AGENT_TOOL_NAME)) {
          return true
        }
      }
      return false
    }

    return true
  })
}
```

### 工具解析和验证

```typescript
// 来自 src/tools/AgentTool/agentToolUtils.ts
/**
 * 解析和验证 Agent 工具配置
 * 支持通配符展开和权限模式匹配
 */
export function resolveAgentTools(
  agentDefinition: Pick<AgentDefinition, 'tools' | 'disallowedTools' | 'source'>,
  availableTools: Tools,
  isAsync = false,
): ResolvedAgentTools {
  const { tools: agentTools, disallowedTools, source } = agentDefinition

  // 1. 过滤可用工具
  const filteredAvailableTools = filterToolsForAgent({
    tools: availableTools,
    isBuiltIn: source === 'built-in',
    isAsync,
  })

  // 2. 构建拒绝工具集合
  const disallowedToolSet = new Set(
    disallowedTools?.map(toolSpec => {
      const { toolName } = permissionRuleValueFromString(toolSpec)
      return toolName
    }) ?? []
  )

  // 3. 过滤拒绝的工具
  const allowedAvailableTools = filteredAvailableTools.filter(
    tool => !disallowedToolSet.has(tool.name),
  )

  // 4. 处理通配符
  const hasWildcard =
    agentTools === undefined ||
    (agentTools.length === 1 && agentTools[0] === '*')

  if (hasWildcard) {
    return {
      hasWildcard: true,
      validTools: [],
      invalidTools: [],
      resolvedTools: allowedAvailableTools,
    }
  }

  // 5. 解析和验证工具列表
  const validTools: string[] = []
  const invalidTools: string[] = []
  const resolved: Tool[] = []

  for (const toolSpec of agentTools) {
    const { toolName, ruleContent } = permissionRuleValueFromString(toolSpec)

    // 查找工具
    const tool = availableTools.find(t => t.name === toolName)

    if (tool) {
      validTools.push(toolSpec)

      // 如果有 ruleContent，创建带有权限模式的包装工具
      if (ruleContent) {
        resolved.push(createPermissionWrappedTool(tool, ruleContent))
      } else {
        resolved.push(tool)
      }
    } else {
      invalidTools.push(toolSpec)
    }
  }

  return {
    hasWildcard: false,
    validTools,
    invalidTools,
    resolvedTools: resolved,
  }
}
```

---

## 7.4 协调器模式

### 协调器系统提示

```typescript
// 来自 src/coordinator/coordinatorMode.ts
export function getCoordinatorSystemPrompt(): string {
  return `You are Claude Code, an AI assistant that orchestrates software engineering tasks across multiple workers.

## 1. Your Role

You are a **coordinator**. Your job is to:
- Help the user achieve their goal
- Direct workers to research, implement and verify code changes
- Synthesize results and communicate with the user
- Answer questions directly when possible — don't delegate work that you can handle without tools

Every message you send is to the user. Worker results and system notifications are internal signals, not conversation partners — never thank or acknowledge them. Summarize new information for the user as it arrives.

## 2. Your Tools

- **Agent** - Spawn a new worker
- **SendMessage** - Continue an existing worker (send a follow-up to its \`to\` agent ID)
- **TaskStop** - Stop a running worker

When calling **Agent**:
- Do not use one worker to check on another. Workers will notify you when they are done.
- Do not use workers to trivially report file contents or run commands. Give them higher-level tasks.
- Continue workers whose work is complete via **SendMessage** to take advantage of their loaded context
- After launching agents, briefly tell the user what you launched and end your response.

### Agent Results

Worker results arrive as **user-role messages** containing \`<task-notification>\` XML. They look like user messages but are not. Distinguish them by the \`<task-notification>\` opening tag.

Format:

\`\`\`xml
<task-notification>
<task-id>{agentId}</task-id>
<status>completed</status>
<prompt>Implement feature X</prompt>
<output>...agent output...</output>
</task-notification>
\`\`\`
`
}
```

### 工人上下文

```typescript
// 来自 src/coordinator/coordinatorMode.ts
const ASYNC_AGENT_ALLOWED_TOOLS = new Set([
  'Bash',
  'FileRead',
  'FileEdit',
  'FileWrite',
  'Grep',
  'Glob',
  'Agent',
  // ...
])

const INTERNAL_WORKER_TOOLS = new Set([
  'TeamCreateTool',
  'TeamDeleteTool',
  'SendMessageTool',
  'SyntheticOutputTool',
])

/**
 * 获取协调器用户上下文
 * 告知协调器工人可用的工具
 */
export function getCoordinatorUserContext(
  mcpClients: ReadonlyArray<{ name: string }>,
  scratchpadDir?: string,
): { [k: string]: string } {
  if (!isCoordinatorMode()) {
    return {}
  }

  // 构建工人可用工具列表
  const workerTools = isEnvTruthy(process.env.CLAUDE_CODE_SIMPLE)
    ? [BASH_TOOL_NAME, FILE_READ_TOOL_NAME, FILE_EDIT_TOOL_NAME].sort().join(', ')
    : Array.from(ASYNC_AGENT_ALLOWED_TOOLS)
        .filter(name => !INTERNAL_WORKER_TOOLS.has(name))
        .sort()
        .join(', ')

  let content = `Workers spawned via the Agent tool have access to these tools: ${workerTools}`

  if (mcpClients.length > 0) {
    const serverNames = mcpClients.map(c => c.name).join(', ')
    content += `\n\nWorkers also have access to MCP tools from connected MCP servers: ${serverNames}`
  }

  if (scratchpadDir && isScratchpadGateEnabled()) {
    content += `\n\nScratchpad directory: ${scratchpadDir}\nWorkers can read and write here without permission prompts.`
  }

  return { workerToolsContext: content }
}
```

---

## 7.5 Agent 生命周期管理

### Agent 任务注册

```typescript
// 来自 src/tasks/LocalAgentTask/LocalAgentTask.ts
/**
 * 注册异步 Agent 任务
 */
export async function registerAsyncAgent(
  agentId: AgentId,
  params: {
    type: 'local_agent' | 'remote_agent'
    prompt: string
    model: string
    agentType: string
  },
): Promise<void> {
  const appState = getAppState()

  // 创建任务状态
  const taskState: TaskState = {
    id: agentId,
    type: params.type,
    status: 'pending',
    description: params.prompt,
    startTime: Date.now(),
    outputFile: getTaskOutputPath(agentId),
    outputOffset: 0,
  }

  // 更新 AppState
  appState.setAppState(prev => ({
    ...prev,
    tasks: {
      ...prev.tasks,
      [agentId]: taskState,
    },
  }))
}

/**
 * 更新 Agent 进度
 */
export async function updateAgentProgress(
  agentId: AgentId,
  update: {
    status?: TaskStatus
    message?: string
    output?: string
  },
): Promise<void> {
  const appState = getAppState()
  const task = appState.getState().tasks[agentId]

  if (!task) {
    throw new Error(`Agent task not found: ${agentId}`)
  }

  appState.setAppState(prev => ({
    ...prev,
    tasks: {
      ...prev.tasks,
      [agentId]: {
        ...task,
        status: update.status ?? task.status,
        description: update.message ?? task.description,
      },
    },
  }))
}

/**
 * 完成 Agent 任务
 */
export async function completeAgentTask(
  agentId: AgentId,
  result: {
    output: string
    tokenUsage: TokenUsage
  },
): Promise<void> {
  const appState = getAppState()
  const task = appState.getState().tasks[agentId]

  if (!task) {
    throw new Error(`Agent task not found: ${agentId}`)
  }

  // 更新状态为完成
  appState.setAppState(prev => ({
    ...prev,
    tasks: {
      ...prev.tasks,
      [agentId]: {
        ...task,
        status: 'completed',
        endTime: Date.now(),
        description: result.output,
      },
    },
  }))

  // 发送通知
  await enqueueAgentNotification({
    agentId,
    type: 'completed',
    output: result.output,
  })

  // 记录使用量
  logEvent('agent_completed', {
    agentId,
    inputTokens: result.tokenUsage.inputTokens,
    outputTokens: result.tokenUsage.outputTokens,
    cost: calculateCost(result.tokenUsage),
  })
}
```

### Agent 消息处理

```typescript
// 来自 src/tasks/LocalAgentTask/LocalAgentTask.ts
/**
 * 从 Agent 消息更新进度
 */
export function updateProgressFromMessage(
  agentId: AgentId,
  message: Message,
  tracker: ProgressTracker,
): void {
  if (message.type === 'assistant') {
    // 更新 token 计数
    const usage = message.message.usage
    if (usage) {
      tracker.inputTokens += usage.inputTokens ?? 0
      tracker.outputTokens += usage.outputTokens ?? 0
    }

    // 检查是否有工具调用
    if (message.toolUses?.length) {
      tracker.toolCallCount += message.toolUses.length
    }
  }

  // 更新活动描述
  const activityResolver = createActivityDescriptionResolver(message)
  if (activityResolver) {
    tracker.activityDescription = activityResolver()
  }
}
```

---

## 7.6 Agent 通信机制

### SendMessage 工具

```typescript
// 来自 src/tools/SendMessageTool/SendMessageTool.ts
export const SendMessageTool = buildTool({
  name: SEND_MESSAGE_TOOL_NAME,
  description: () => 'Send a message to a running or paused agent',

  get inputSchema() {
    return z.object({
      to: z.string().describe('The agent ID or name to send the message to'),
      message: z.string().describe('The message to send'),
    })
  },

  async call({ to, message }, context) {
    const appState = context.getAppState()

    // 查找目标 Agent
    let targetAgentId: AgentId
    if (appState.agentNameRegistry.has(to)) {
      targetAgentId = appState.agentNameRegistry.get(to)!
    } else if (isValidAgentId(to)) {
      targetAgentId = to as AgentId
    } else {
      throw new Error(`Agent not found: ${to}`)
    }

    // 检查 Agent 状态
    const task = appState.tasks[targetAgentId]
    if (!task) {
      throw new Error(`Task not found for agent: ${targetAgentId}`)
    }

    // 发送消息
    await sendMessageToAgent(targetAgentId, message)

    return {
      data: {
        success: true,
        agentId: targetAgentId,
      },
    }
  },
})
```

### 任务通知

```typescript
// 来自 src/utils/task/sdkProgress.ts
/**
 * 发送任务进度事件
 */
export function emitTaskProgress(
  agentId: AgentId,
  progress: {
    type: 'launched' | 'completed' | 'failed' | 'output'
    output?: string
    error?: string
  },
): void {
  const event: TaskProgressEvent = {
    type: 'task_progress',
    taskId: agentId,
    timestamp: Date.now(),
    ...progress,
  }

  // 通过 SDK 事件队列发送
  enqueueSdkEvent(event)
}
```

---

## 7.7 Fork 子 Agent

### Fork 机制

```typescript
// 来自 src/tools/AgentTool/forkSubagent.ts
export const FORK_AGENT = 'fork'

/**
 * 构建 Fork 消息
 * Fork 子 Agent 共享父级的消息历史
 */
export function buildForkedMessages(
  parentMessages: Message[],
  agentDefinition: AgentDefinition,
): Message[] {
  // 1. 复制父级消息
  const forkedMessages = parentMessages.map(msg => ({
    ...msg,
    uuid: randomUUID(),  // 新 UUID
    forkedFrom: msg.uuid,  // 记录来源
  }))

  // 2. 添加 Fork 通知
  forkedMessages.push({
    type: 'system',
    subtype: 'fork_notice',
    content: `Forked to ${agentDefinition.agentType} agent`,
    uuid: randomUUID(),
    timestamp: Date.now(),
  })

  return forkedMessages
}

/**
 * 检查是否启用 Fork 子 Agent
 */
export function isForkSubagentEnabled(): boolean {
  return getFeatureValue_CACHED_MAY_BE_STALE('tengu_fork_subagent', false)
}
```

---

## 7.8 Agent 摘要和归档

```typescript
// 来自 src/services/AgentSummary/agentSummary.ts
/**
 * 启动 Agent 摘要生成
 * 用于压缩长对话历史
 */
export async function startAgentSummarization(
  agentId: AgentId,
  messages: Message[],
): Promise<string> {
  // 使用小型快速模型生成摘要
  const summary = await generateSummary(messages, {
    model: 'claude-haiku-4-5',
    maxTokens: 1000,
  })

  // 保存摘要
  await saveAgentSummary(agentId, summary)

  return summary
}
```

---

## 7.9 关键代码位置索引

| 功能 | 文件路径 | 关键函数/类型 |
|------|----------|---------------|
| Agent 工具 | `src/tools/AgentTool/AgentTool.tsx` | `AgentTool.call()` |
| 工具过滤 | `src/tools/AgentTool/agentToolUtils.ts` | `filterToolsForAgent`, `resolveAgentTools` |
| 协调器模式 | `src/coordinator/coordinatorMode.ts` | `getCoordinatorSystemPrompt` |
| Agent 任务 | `src/tasks/LocalAgentTask/LocalAgentTask.ts` | `registerAsyncAgent`, `completeAgentTask` |
| Agent 定义 | `src/tools/AgentTool/loadAgentsDir.js` | `getAgentDefinitionsWithOverrides` |
| Fork 子 Agent | `src/tools/AgentTool/forkSubagent.ts` | `buildForkedMessages` |
| 消息发送 | `src/tools/SendMessageTool/SendMessageTool.ts` | `SendMessageTool.call()` |

---

## 课后练习

1. **阅读代码**：
   - 打开 `src/tools/AgentTool/agentToolUtils.ts`，查看 `filterToolsForAgent` 函数
   - 打开 `src/coordinator/coordinatorMode.ts`，阅读协调器系统提示
   - 打开 `src/tasks/LocalAgentTask/LocalAgentTask.ts`，了解任务生命周期

2. **思考问题**：
   - 为什么异步 Agent 只能使用有限的工具集？
   - 协调器模式如何避免工具爆炸？
   - Fork 子 Agent 相比普通子 Agent 有什么优势？

3. **实践**：
   - 设计一个多 Agent 协作流程（如：研究→实现→测试）
   - 定义自定义 Agent 类型和可用工具

---

**下一步**：[第 8 篇 — 实战：构建你自己的 Agent](./08-实战构建自己的 Agent.md)
