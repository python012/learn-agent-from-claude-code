# 第 2 篇：Agent 架构入门

## 学习目标

- 理解 Claude Code 的整体架构
- 掌握状态管理、命令系统、工具注册等核心模块
- 了解数据流和执行路径
- 为深入学习工具系统和权限控制打下基础

---

## 2.1 整体架构概览

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI 入口 (main.tsx)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Commander   │  │  初始化流程  │  │   状态提供者            │  │
│  │  命令解析    │  │  Telemetry  │  │   AppStateProvider     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       REPL / 交互界面                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Ink (React)│  │  消息列表    │  │   输入处理              │  │
│  │  终端 UI     │  │  Messages   │  │   PromptInput          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        核心服务层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  API 客户端   │  │  MCP 服务    │  │   工具系统             │  │
│  │  claude.ts  │  │  mcp/       │  │   tools.ts             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  状态管理    │  │  权限系统    │  │   会话管理             │  │
│  │  AppState   │  │  permissions│  │   sessionStorage       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         工具实现层                               │
│  Bash  │  FileRead  │  FileWrite  │  Grep  │  Glob  │  MCP ... │
└─────────────────────────────────────────────────────────────────┘
```

### 核心模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| **入口** | `src/main.tsx` | 命令行解析、初始化、启动 REPL |
| **状态** | `src/state/AppState.tsx` | 全局状态管理、React Context |
| **API** | `src/services/api/claude.ts` | 与 Anthropic API 交互 |
| **工具** | `src/tools.ts` | 工具注册、组装、过滤 |
| **权限** | `src/utils/permissions/` | 权限检查、规则管理 |
| **MCP** | `src/services/mcp/` | Model Context Protocol 实现 |

---

## 2.2 入口点分析：main.tsx

### Commander 命令定义

Claude Code 使用 [Commander.js](https://github.com/tj/commander.js) 作为 CLI 框架：

```typescript
// 来自 src/main.tsx — 简化的命令定义
import { Command as CommanderCommand } from '@commander-js/extra-typings'

const program = new CommanderCommand()
  .name('claude')
  .description('Claude Code CLI — AI 编程助手')
  .version('1.0.0')

  // 全局选项
  .option('-v, --verbose', '详细输出模式')
  .option('-m, --model <model>', '指定模型', 'claude-sonnet-4-6')
  .option('-p, --print', '打印模式（非交互）')
  .option('--permission-mode <mode>', '权限模式', 'default')

  // 子命令
  .command('init')
  .description('初始化项目配置')
  .action(() => { /* ... */ })

  .command('mcp')
  .description('MCP 服务器管理')
  .action(() => { /* ... */ })
```

### 初始化流程

```typescript
// 来自 src/main.tsx — 简化的初始化流程
async function main() {
  // 1. 性能分析起点
  profileCheckpoint('main_tsx_entry')

  // 2. 并行预取（加速启动）
  startMdmRawRead()        // MDM 配置读取
  startKeychainPrefetch()  // Keychain 凭证预取

  // 3. 解析命令行参数
  program.parse(process.argv)
  const options = program.opts()

  // 4. 初始化远程设置和策略
  await loadRemoteManagedSettings()
  await loadPolicyLimits()

  // 5. 初始化 GrowthBook（特性开关）
  await initializeGrowthBook()

  // 6. 初始化 Telemetry
  await initializeTelemetryAfterTrust()

  // 7. 准备状态存储
  const store = createStore(getDefaultAppState())

  // 8. 启动 REPL（交互式界面）
  await launchRepl({
    store,
    options,
    // ...
  })
}
```

### 特性开关（Feature Flags）

使用 Bun 的 `feature()` 函数进行死代码消除：

```typescript
// 来自 src/main.tsx
import { feature } from 'bun:bundle'

// 条件性加载 — 打包时会移除未启用的代码
const coordinatorModeModule = feature('COORDINATOR_MODE')
  ? require('./coordinator/coordinatorMode.js')
  : null

const assistantModule = feature('KAIROS')
  ? require('./assistant/index.js')
  : null

// 在代码中使用
if (feature('COORDINATOR_MODE') && coordinatorModeModule?.isCoordinatorMode()) {
  // 协调器模式逻辑
}
```

---

## 2.3 状态管理：AppState

### 状态存储结构

参考 `src/state/AppStateStore.ts`：

```typescript
export type AppState = {
  // === 设置相关 ===
  settings: SettingsJson
  verbose: boolean
  mainLoopModel: ModelSetting

  // === UI 状态 ===
  statusLineText: string | undefined
  expandedView: 'none' | 'tasks' | 'teammates'
  isBriefOnly: boolean
  footerSelection: FooterItem | null

  // === 权限相关 ===
  toolPermissionContext: ToolPermissionContext

  // === 任务管理 ===
  tasks: { [taskId: string]: TaskState }

  // === MCP 相关 ===
  mcp: {
    clients: MCPServerConnection[]
    tools: Tool[]
    resources: Record<string, ServerResource[]>
  }

  // === 插件相关 ===
  plugins: {
    enabled: LoadedPlugin[]
    disabled: LoadedPlugin[]
    errors: PluginError[]
  }

  // === 模式特性 ===
  kairosEnabled: boolean           // Assistant 模式
  replBridgeEnabled: boolean       // 桥接模式
  remoteSessionUrl: string | undefined
}
```

### 状态存储实现

参考 `src/state/store.ts`（简化版）：

```typescript
// 简单的 Redux-like 状态存储
export type Store<T> = {
  getState: () => T
  setState: (updater: T | ((prev: T) => T)) => void
  subscribe: (listener: () => void) => () => void
}

export function createStore<T>(
  initialState: T,
  onChange?: (args: { newState: T; oldState: T }) => void
): Store<T> {
  let state = initialState
  const listeners = new Set<() => void>()

  return {
    getState: () => state,

    setState: (updater) => {
      const oldState = state
      const newState = typeof updater === 'function'
        ? (updater as (prev: T) => T)(oldState)
        : updater

      // 优化：如果状态未变，不通知监听器
      if (Object.is(oldState, newState)) return

      state = newState
      listeners.forEach(listener => listener())
      onChange?.({ newState, oldState })
    },

    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    }
  }
}
```

### React Hook 封装

```typescript
// 来自 src/state/AppState.tsx
import { useSyncExternalStore } from 'react'

/**
 * 订阅 AppState 的一个切片，仅在选择值变化时重新渲染
 */
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore()

  const get = () => {
    const state = store.getState()
    return selector(state)
  }

  return useSyncExternalStore(store.subscribe, get, get)
}

/**
 * 获取 setState 更新函数，不订阅任何状态
 */
export function useSetAppState() {
  return useAppStore().setState
}
```

### 使用示例

```tsx
// 在组件中使用
function StatusLine() {
  // 仅订阅 statusLineText，其他状态变化不会触发重新渲染
  const statusLineText = useAppState(s => s.statusLineText)
  const verbose = useAppState(s => s.verbose)

  return (
    <Box>
      <Text>{statusLineText}</Text>
      {verbose && <Text>[DEBUG MODE]</Text>}
    </Box>
  )
}

// 更新状态
function SomeComponent() {
  const setAppState = useSetAppState()

  const handleAction = () => {
    setAppState(prev => ({
      ...prev,
      statusLineText: '处理中...',
    }))
  }
}
```

---

## 2.4 命令系统

### 命令注册

参考 `src/commands.ts`：

```typescript
export type Command = {
  name: string
  description: string
  aliases?: string[]
  category: 'general' | 'git' | 'mcp' | 'plugins' | 'skills'
  action: (args: string[]) => Promise<void>
}

// 获取所有可用命令
export function getCommands(): Command[] {
  return [
    {
      name: 'diff',
      description: '显示未提交的更改',
      category: 'git',
      action: async () => { /* ... */ }
    },
    {
      name: 'commit',
      description: '创建 git 提交',
      category: 'git',
      action: async (args) => { /* ... */ }
    },
    {
      name: 'mcp',
      description: '管理 MCP 服务器',
      category: 'mcp',
      action: async () => { /* ... */ }
    },
    // ... 更多命令
  ]
}
```

### 命令执行流程

```
用户输入：/commit -m "fix bug"
         │
         ▼
┌─────────────────┐
│  解析命令前缀    │  → 识别 "/" 前缀
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  查找命令定义    │  → 匹配 "commit"
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  解析参数        │  → 提取 "-m" 和 "fix bug"
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  执行命令动作    │  → 调用 commit 的 action 函数
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  显示结果        │  → 更新 UI 显示提交结果
└─────────────────┘
```

---

## 2.5 工具系统概览

### 工具注册和组装

参考 `src/tools.ts`：

```typescript
// 获取所有基础工具
export function getAllBaseTools(): Tools {
  return [
    AgentTool,        // 子代理工具
    BashTool,         // Bash 命令执行
    GlobTool,         // 文件 glob 搜索
    GrepTool,         // 内容 grep 搜索
    FileReadTool,     // 文件读取
    FileEditTool,     // 文件编辑
    FileWriteTool,    // 文件写入
    WebFetchTool,     // 网页抓取
    WebSearchTool,    // 网络搜索
    // ... 条件性加载的工具
  ]
}

// 根据权限上下文过滤工具
export const getTools = (
  permissionContext: ToolPermissionContext
): Tools => {
  // 1. 获取所有基础工具
  const tools = getAllBaseTools()

  // 2. 过滤被拒绝的工具
  let allowedTools = filterToolsByDenyRules(tools, permissionContext)

  // 3. 过滤未启用的工具
  const isEnabled = allowedTools.map(tool => tool.isEnabled())
  return allowedTools.filter((_, i) => isEnabled[i])
}

// 组装完整工具池（包括 MCP 工具）
export function assembleToolPool(
  permissionContext: ToolPermissionContext,
  mcpTools: Tools,
): Tools {
  const builtInTools = getTools(permissionContext)

  // 过滤 MCP 工具
  const allowedMcpTools = filterToolsByDenyRules(mcpTools, permissionContext)

  // 合并并去重（内置工具优先）
  return uniqBy(
    [...builtInTools].sort(byName).concat(allowedMcpTools.sort(byName)),
    'name',
  )
}
```

### 工具 API Schema 转换

```typescript
// 来自 src/utils/api.ts — 简化的工具 Schema 转换
export function toolToAPISchema(tool: Tool): BetaToolUnion {
  return {
    name: tool.name,
    description: await tool.description(...),
    input_schema: tool.inputJSONSchema ?? zodToJsonSchema(tool.inputSchema),
    // 可选的缓存范围
    cache_scope: shouldUseGlobalCacheScope() ? 'global' : undefined,
  }
}
```

---

## 2.6 数据流和执行路径

### 完整请求流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 用户输入                                                      │
│    "帮我创建一个新文件，内容是 Hello World"                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 消息标准化                                                    │
│    normalizeMessagesForAPI(messages)                            │
│    - 转换为 API 格式                                              │
│    - 添加系统提示                                                │
│    - 注入工具定义                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. API 调用                                                      │
│    client.messages.stream({                                     │
│      model, messages, tools, system                             │
│    })                                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 流式响应处理                                                  │
│    for await (const event of stream) {                          │
│      - content_block_start                                      │
│      - content_block_delta (文本/工具输入)                        │
│      - content_block_stop                                       │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. 工具调用检测和执行                                            │
│    if (event.content_block.type === 'tool_use') {               │
│      const tool = tools.find(t => t.name === block.name)        │
│      const result = await tool.call(input, context)             │
│    }                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. 发送工具结果                                                  │
│    messages.push({                                              │
│      role: 'user',                                              │
│      content: [{ type: 'tool_result', tool_use_id, content }]   │
│    })                                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. 继续 API 调用获取后续回复                                       │
│    （回到步骤 3）                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. 更新 UI 显示结果                                              │
│    setAppState(prev => ({                                       │
│      ...prev,                                                   │
│      messages: [...prev.messages, newMessages]                  │
│    }))                                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 关键函数调用链

```
main.tsx:main()
  │
  ├─> launchRepl()
  │     │
  │     ├─> initializeToolPermissionContext()
  │     ├─> getTools(permissionContext)
  │     │     │
  │     │     └─> getAllBaseTools()
  │     │     └─> filterToolsByDenyRules()
  │     │
  │     └─> runQuery()  [src/services/api/claude.ts]
  │           │
  │           ├─> normalizeMessagesForAPI()
  │           ├─> toolToAPISchema()
  │           ├─> client.messages.stream()
  │           │
  │           └─> for await (event of stream)
  │                 │
  │                 ├─> handleToolUse(event)
  │                 │     │
  │                 │     └─> tool.call(input, context)
  │                 │           │
  │                 │           └─> BashTool.call() / FileWriteTool.call() / ...
  │                 │
  │                 └─> appendMessage(event)
  │
  └─> render(<App />)
        │
        └─> <MessageList />
        └─> <PromptInput />
```

---

## 2.7 任务抽象：Task.ts

### 任务类型定义

```typescript
// 来自 src/Task.ts
export type TaskType =
  | 'local_bash'          // 本地 Bash 执行
  | 'local_agent'         // 本地 Agent
  | 'remote_agent'        // 远程 Agent
  | 'in_process_teammate' // 进程内队友
  | 'local_workflow'      // 本地工作流
  | 'monitor_mcp'         // MCP 监控
  | 'dream'               // Dream 模式

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'killed'

// 任务句柄
export type TaskHandle = {
  taskId: string
  cleanup?: () => void
}

// 任务上下文
export type TaskContext = {
  abortController: AbortController
  getAppState: () => AppState
  setAppState: SetAppState
}
```

### 任务 ID 生成

```typescript
// 来自 src/Task.ts
const TASK_ID_PREFIXES: Record<string, string> = {
  local_bash: 'b',
  local_agent: 'a',
  remote_agent: 'r',
  in_process_teammate: 't',
  local_workflow: 'w',
  monitor_mcp: 'm',
  dream: 'd',
}

export function generateTaskId(type: TaskType): string {
  const prefix = getTaskIdPrefix(type)
  const bytes = randomBytes(8)
  let id = prefix
  for (let i = 0; i < 8; i++) {
    id += TASK_ID_ALPHABET[bytes[i]! % TASK_ID_ALPHABET.length]
  }
  return id
}

// 示例输出：
// local_bash  → b3x9k2m7
// local_agent → a8j4n1p5
```

---

## 2.8 会话管理

### 会话 ID 和持久化

```typescript
// 来自 src/bootstrap/state.ts 和 src/utils/sessionStorage.ts
let sessionId: UUID
let sessionTitle: string | undefined

export function getSessionId(): UUID {
  return sessionId
}

export function switchSession(newSessionId?: UUID): void {
  sessionId = newSessionId ?? randomUUID()
  // 持久化到磁盘
  saveSessionMetadata(sessionId)
}

// 会话元数据保存
export function cacheSessionTitle(sessionId: UUID, title: string): void {
  const metadataPath = get_session_metadata_dir(sessionId)
  writeFileSync(metadataPath, JSON.stringify({ title, timestamp: Date.now() }))
}
```

### 会话恢复

```typescript
// 来自 src/utils/conversationRecovery.ts
export function loadConversationForResume(
  sessionId: UUID
): MessageType[] | null {
  const sessionPath = getSessionFilePath(sessionId)

  try {
    const content = readFileSync(sessionPath)
    const data = JSON.parse(content)
    return data.messages
  } catch (e) {
    if (isENOENT(e)) {
      return null  // 会话不存在
    }
    logError(e)
    return null
  }
}
```

---

## 2.9 MCP 集成

### MCP 服务器连接

```typescript
// 来自 src/services/mcp/types.ts
export type MCPServerConnection = {
  name: string
  status: 'connecting' | 'connected' | 'disconnected' | 'error'
  error?: string
  config: McpServerConfig
  tools: Tool[]
  resources: ServerResource[]
  client?: M CPClient
}

// MCP 服务器配置
export type McpServerConfig = {
  command: string          // 启动命令
  args?: string[]          // 参数
  env?: Record<string, string>
  cwd?: string
}
```

### MCP 工具集成

```typescript
// 来自 src/services/mcp/client.ts
export async function getMcpToolsCommandsAndResources(
  servers: MCPServerConnection[]
): Promise<{
  tools: Tool[]
  commands: Command[]
  resources: Record<string, ServerResource[]>
}> {
  const allTools: Tool[] = []
  const allCommands: Command[] = []
  const allResources: Record<string, ServerResource[]> = {}

  for (const server of servers) {
    if (server.status !== 'connected') continue

    // 获取服务器工具
    const tools = await server.client!.listTools()
    allTools.push(...tools.map(t => wrapAsMcpTool(t, server.name)))

    // 获取资源
    const resources = await server.client!.listResources()
    allResources[server.name] = resources
  }

  return { tools: allTools, commands: allCommands, resources: allResources }
}
```

---

## 2.10 架构设计要点

### 1. 状态驱动 UI

- 所有 UI 状态集中在 `AppState`
- 使用 selector 模式优化渲染性能
- 状态变更通过 `setAppState` 统一处理

### 2. 工具系统可扩展

- 工具定义与实现分离（`Tool` 接口）
- 支持条件性加载（feature flags）
- MCP 工具与内置工具统一接口

### 3. 权限控制分层

- 规则层：alwaysAllow/alwaysDeny/alwaysAsk
- 工具层：`tool.checkPermissions()`
- 分类器层：Auto Mode 分类器

### 4. 流式处理优先

- API 响应全程流式处理
- 工具调用边解析边执行
- UI 实时更新（打字机效果）

### 5. 模块化设计

```
┌─────────────────────────────────────────┐
│              main.tsx                   │
│  (编排层：初始化、命令解析、启动)          │
└─────────────────────────────────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐
│ State  │ │  API   │ │ Tools  │
│ (状态) │ │ (服务) │ │ (工具) │
└────────┘ └────────┘ └────────┘
```

---

## 2.11 关键代码位置索引

| 功能 | 文件路径 | 关键函数/类型 |
|------|----------|---------------|
| 入口 | `src/main.tsx` | `main()`, `program` |
| 状态 | `src/state/AppState.tsx` | `AppState`, `useAppState` |
| 状态存储 | `src/state/store.ts` | `createStore` |
| 工具定义 | `src/Tool.ts` | `Tool`, `buildTool` |
| 工具注册 | `src/tools.ts` | `getTools`, `assembleToolPool` |
| API 调用 | `src/services/api/claude.ts` | `runQuery` |
| 权限 | `src/utils/permissions/permissions.ts` | `hasPermissionsToUseTool` |
| 任务 | `src/Task.ts` | `TaskType`, `generateTaskId` |
| MCP | `src/services/mcp/client.ts` | `getMcpToolsCommandsAndResources` |
| 会话 | `src/utils/sessionStorage.ts` | `cacheSessionTitle`, `loadConversationForResume` |

---

## 课后练习

1. **阅读代码**：
   - 打开 `src/state/AppStateStore.ts`，查看完整的 `AppState` 类型定义
   - 打开 `src/main.tsx`，找到 `launchRepl` 调用位置
   - 打开 `src/tools.ts`，查看 `getAllBaseTools` 返回的工具列表

2. **思考问题**：
   - 为什么使用 `useSyncExternalStore` 而不是 `useState`？
   - 工具系统为什么需要 `assembleToolPool` 和 `getTools` 两个函数？
   - 特性开关（feature flags）有什么好处？

3. **实践**：
   - 尝试画出你理解的数据流图
   - 如果要添加一个新工具，需要修改哪些文件？

---

**下一步**：[第 3 篇 — 工具系统详解](./03-tool-system-explained.md)
