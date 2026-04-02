# 第 3 篇：工具系统详解

## 学习目标

- 理解工具系统的核心设计模式
- 学会定义和实现自定义工具
- 掌握工具权限控制机制
- 了解工具执行的完整流程

---

## 3.1 工具接口定义

### 核心接口：`Tool`

参考 `src/Tool.ts`，工具接口定义了所有工具必须实现的方法：

```typescript
export type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
  // === 基本属性 ===
  readonly name: string                    // 工具名称
  readonly aliases?: string[]              // 可选别名
  readonly searchHint?: string             // 搜索提示词
  readonly inputSchema: Input              // 输入验证 Schema
  readonly inputJSONSchema?: ToolInputJSONSchema  // MCP 工具用 JSON Schema
  readonly outputSchema?: z.ZodType<unknown>      // 输出验证 Schema

  // === 核心方法 ===
  call(
    args: z.infer<Input>,                  // 解析后的输入
    context: ToolUseContext,               // 工具执行上下文
    canUseTool: CanUseToolFn,              // 权限检查函数
    parentMessage: AssistantMessage,       // 父消息
    onProgress?: ToolCallProgress<P>,      // 进度回调
  ): Promise<ToolResult<Output>>           // 执行结果

  description(
    input: z.infer<Input>,
    options: {
      isNonInteractiveSession: boolean
      toolPermissionContext: ToolPermissionContext
      tools: Tools
    },
  ): Promise<string>                       // 工具描述（给模型看）

  prompt(options: {...}): Promise<string>  // 工具提示（给系统看）

  // === UI 渲染方法 ===
  renderToolUseMessage(
    input: Partial<z.infer<Input>>,
    options: { theme: ThemeName; verbose: boolean }
  ): React.ReactNode                       // 渲染工具使用消息

  renderToolResultMessage(
    content: Output,
    progressMessagesForMessage: ProgressMessage<P>[],
    options: { style?: 'condensed'; theme: ThemeName; ... }
  ): React.ReactNode                       // 渲染工具结果

  // === 权限和安全 ===
  isConcurrencySafe(input: z.infer<Input>): boolean    // 是否可并发
  isReadOnly(input: z.infer<Input>): boolean           // 是否只读
  isDestructive?(input: z.infer<Input>): boolean       // 是否破坏性操作
  checkPermissions(
    input: z.infer<Input>,
    context: ToolUseContext,
  ): Promise<PermissionResult>             // 权限检查

  // === 其他元数据 ===
  isEnabled(): boolean                     // 是否启用
  userFacingName(input: Partial<z.infer<Input>>): string  // 用户友好的名称
  maxResultSizeChars: number               // 结果最大字符数
}
```

### 工具构建器：`buildTool`

提供默认值，简化工具定义：

```typescript
// 来自 src/Tool.ts
const TOOL_DEFAULTS = {
  isEnabled: () => true,
  isConcurrencySafe: (_input?: unknown) => false,
  isReadOnly: (_input?: unknown) => false,
  isDestructive: (_input?: unknown) => false,
  checkPermissions: (
    input: { [key: string]: unknown },
    _ctx?: ToolUseContext,
  ): Promise<PermissionResult> =>
    Promise.resolve({ behavior: 'allow', updatedInput: input }),
  toAutoClassifierInput: (_input?: unknown) => '',
  userFacingName: (_input?: unknown) => '',
}

export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,
    userFacingName: () => def.name,
    ...def,
  } as BuiltTool<D>
}
```

---

## 3.2 工具实现示例：BashTool

### 输入输出 Schema

```typescript
// 来自 src/tools/BashTool/BashTool.tsx
import { z } from 'zod/v4'
import { lazySchema } from '../../utils/lazySchema.js'

// 输入 Schema
const fullInputSchema = lazySchema(() => z.strictObject({
  command: z.string().describe('The command to execute'),
  timeout: semanticNumber(z.number().optional())
    .describe(`Optional timeout in milliseconds (max ${getMaxTimeoutMs()})`),
  description: z.string().optional()
    .describe('Clear, concise description of what this command does'),
  run_in_background: semanticBoolean(z.boolean().optional())
    .describe('Set to true to run this command in the background'),
  dangerouslyDisableSandbox: semanticBoolean(z.boolean().optional())
    .describe('Set this to true to dangerously override sandbox mode'),
}))

// 输出 Schema
const outputSchema = lazySchema(() => z.object({
  stdout: z.string().describe('The standard output of the command'),
  stderr: z.string().describe('The standard error output of the command'),
  interrupted: z.boolean().describe('Whether the command was interrupted'),
  backgroundTaskId: z.string().optional()
    .describe('ID of the background task if running in background'),
  returnCodeInterpretation: z.string().optional()
    .describe('Semantic interpretation for non-error exit codes'),
}))

type InputSchema = ReturnType<typeof inputSchema>
type OutputSchema = ReturnType<typeof outputSchema>
```

### 工具定义

```typescript
// 来自 src/tools/BashTool/BashTool.tsx
export const BashTool = buildTool({
  name: 'Bash',
  maxResultSizeChars: 1_000_000,

  // 输入输出 Schema
  get inputSchema(): InputSchema { return inputSchema() },
  get outputSchema(): OutputSchema { return outputSchema() },

  // 工具描述
  async description() {
    return 'Execute a bash command on the local machine.'
  },

  // 获取路径（用于权限检查）
  getPath(input): string {
    return input.command  // Bash 工具的路径是命令本身
  },

  // 准备权限匹配器
  async preparePermissionMatcher({ command }) {
    return pattern => matchWildcardPattern(pattern, command)
  },

  // 权限检查
  async checkPermissions(input, context): Promise<PermissionResult> {
    const appState = context.getAppState()
    return checkBashPermissionForTool(
      BashTool,
      input,
      appState.toolPermissionContext,
    )
  },

  // 是否是只读操作
  isReadOnly(input): boolean {
    return isReadOnlyCommand(input.command)
  },

  // 是否是破坏性操作
  isDestructive(input): boolean {
    return isDestructiveCommand(input.command)
  },

  // UI 渲染
  renderToolUseMessage,
  renderToolResultMessage,
  renderToolUseProgressMessage,

  // 核心执行方法
  async call(input, context, canUseTool, parentMessage, onProgress) {
    // 1. 扩展路径
    const command = expandPath(input.command)

    // 2. 检查是否需要沙箱
    const useSandbox = shouldUseSandbox(input) && !input.dangerouslyDisableSandbox

    // 3. 获取超时设置
    const timeoutMs = getDefaultTimeoutMs(command)

    // 4. 执行命令
    const result = await exec(command, {
      cwd: getCwd(),
      timeout: timeoutMs,
      sandbox: useSandbox,
      signal: context.abortController.signal,
      onOutput: (output) => {
        // 进度回调
        onProgress?.({
          toolUseID: parentMessage.tool_use_id,
          data: { type: 'bash_progress', output }
        })
      }
    })

    // 5. 构建结果
    const output: Out = {
      stdout: result.stdout,
      stderr: result.stderr,
      interrupted: result.signal !== undefined,
      returnCodeInterpretation: interpretReturnCode(result.exitCode),
    }

    return { data: output }
  },
})
```

---

## 3.3 工具实现示例：FileWriteTool

### 输入输出 Schema

```typescript
// 来自 src/tools/FileWriteTool/FileWriteTool.ts
const inputSchema = lazySchema(() =>
  z.strictObject({
    file_path: z
      .string()
      .describe('The absolute path to the file to write'),
    content: z.string().describe('The content to write to the file'),
  }),
)

const outputSchema = lazySchema(() =>
  z.object({
    type: z.enum(['create', 'update'])
      .describe('Whether a new file was created or updated'),
    filePath: z.string().describe('The path to the file'),
    content: z.string().describe('The content written'),
    structuredPatch: z.array(hunkSchema())
      .describe('Diff patch showing the changes'),
    originalFile: z.string().nullable()
      .describe('The original file content (null for new files)'),
    gitDiff: gitDiffSchema().optional(),
  }),
)
```

### 工具定义

```typescript
// 来自 src/tools/FileWriteTool/FileWriteTool.ts
export const FileWriteTool = buildTool({
  name: 'FileWriteTool',
  searchHint: 'create or overwrite files',
  maxResultSizeChars: 100_000,
  strict: true,  // 严格模式

  // Schema
  get inputSchema(): InputSchema { return inputSchema() },
  get outputSchema(): OutputSchema { return outputSchema() },

  // 描述
  async description() {
    return 'Write a file to the local filesystem.'
  },

  // 获取文件路径
  getPath(input): string {
    return input.file_path
  },

  // 准备权限匹配器
  async preparePermissionMatcher({ file_path }) {
    return pattern => matchWildcardPattern(pattern, file_path)
  },

  // 权限检查
  async checkPermissions(input, context): Promise<PermissionDecision> {
    const appState = context.getAppState()
    return checkWritePermissionForTool(
      FileWriteTool,
      input,
      appState.toolPermissionContext,
    )
  },

  // 输入验证
  async validateInput({ file_path, content }, toolUseContext) {
    const fullFilePath = expandPath(file_path)

    // 检查秘密信息
    const secretError = checkTeamMemSecrets(fullFilePath, content)
    if (secretError) {
      return { result: false, message: secretError, errorCode: 0 }
    }

    // 检查权限规则
    const denyRule = matchingRuleForInput(
      fullFilePath,
      appState.toolPermissionContext,
      'edit',
      'deny',
    )
    if (denyRule !== null) {
      return {
        result: false,
        message: 'File is in a directory that is denied.',
        errorCode: 1,
      }
    }

    // 检查文件是否被修改
    const fileMtimeMs = await getFileModificationTime(fullFilePath)
    const readTimestamp = toolUseContext.readFileState.get(fullFilePath)
    if (readTimestamp && fileMtimeMs > readTimestamp.timestamp) {
      return {
        result: false,
        message: FILE_UNEXPECTEDLY_MODIFIED_ERROR,
        errorCode: 2,
      }
    }

    return { result: true }
  },

  // 核心执行方法
  async call(input, context) {
    const fullFilePath = expandPath(input.file_path)

    // 读取原始内容（用于生成 diff）
    let originalContent: string | null = null
    try {
      originalContent = readFileSync(fullFilePath, 'utf-8')
    } catch (e) {
      if (!isENOENT(e)) throw e
    }

    // 写入文件
    await writeTextContent(fullFilePath, input.content)

    // 生成 diff
    const structuredPatch = generatePatch(originalContent, input.content)
    const gitDiff = await fetchSingleFileGitDiff(fullFilePath)

    // 通知 LSP 服务器
    await notifyVscodeFileUpdated(fullFilePath)

    // 构建结果
    const output: Output = {
      type: originalContent === null ? 'create' : 'update',
      filePath: fullFilePath,
      content: input.content,
      structuredPatch,
      originalFile: originalContent,
      gitDiff,
    }

    return { data: output }
  },
})
```

---

## 3.4 工具注册和组装

### 工具注册表

```typescript
// 来自 src/tools.ts
import { BashTool } from './tools/BashTool/BashTool.js'
import { FileReadTool } from './tools/FileReadTool/FileReadTool.js'
import { FileWriteTool } from './tools/FileWriteTool/FileWriteTool.js'
import { GrepTool } from './tools/GrepTool/GrepTool.js'
import { AgentTool } from './tools/AgentTool/AgentTool.js'
// ... 更多工具

// 获取所有基础工具
export function getAllBaseTools(): Tools {
  return [
    AgentTool,
    BashTool,
    // 如果有嵌入式搜索工具，就不需要独立的 Glob/Grep 工具
    ...(hasEmbeddedSearchTools() ? [] : [GlobTool, GrepTool]),
    FileReadTool,
    FileEditTool,
    FileWriteTool,
    WebFetchTool,
    WebSearchTool,
    // 条件性加载的工具
    ...(isTodoV2Enabled()
      ? [TaskCreateTool, TaskGetTool, TaskUpdateTool, TaskListTool]
      : []),
    // ... 更多条件性工具
  ]
}
```

### 工具过滤

```typescript
// 来自 src/tools.ts
/**
 * 根据拒绝规则过滤工具
 * 如果工具匹配拒绝规则且没有 ruleContent，则被过滤掉
 */
export function filterToolsByDenyRules<
  T extends {
    name: string
    mcpInfo?: { serverName: string; toolName: string }
  },
>(tools: readonly T[], permissionContext: ToolPermissionContext): T[] {
  return tools.filter(tool => !getDenyRuleForTool(permissionContext, tool))
}

/**
 * 获取工具列表（应用权限过滤）
 */
export const getTools = (
  permissionContext: ToolPermissionContext
): Tools => {
  // 简单模式：只返回 Bash、Read、Edit
  if (isEnvTruthy(process.env.CLAUDE_CODE_SIMPLE)) {
    const simpleTools: Tool[] = [BashTool, FileReadTool, FileEditTool]
    return filterToolsByDenyRules(simpleTools, permissionContext)
  }

  // 获取所有基础工具
  const tools = getAllBaseTools()

  // 过滤被拒绝的工具
  let allowedTools = filterToolsByDenyRules(tools, permissionContext)

  // 过滤未启用的工具
  const isEnabled = allowedTools.map(tool => tool.isEnabled())
  return allowedTools.filter((_, i) => isEnabled[i])
}
```

### 工具池组装

```typescript
// 来自 src/tools.ts
/**
 * 组装完整工具池（内置工具 + MCP 工具）
 */
export function assembleToolPool(
  permissionContext: ToolPermissionContext,
  mcpTools: Tools,
): Tools {
  const builtInTools = getTools(permissionContext)

  // 过滤 MCP 工具
  const allowedMcpTools = filterToolsByDenyRules(mcpTools, permissionContext)

  // 按名称排序并去重（内置工具优先）
  const byName = (a: Tool, b: Tool) => a.name.localeCompare(b.name)
  return uniqBy(
    [...builtInTools].sort(byName).concat(allowedMcpTools.sort(byName)),
    'name',
  )
}
```

---

## 3.5 工具权限控制

### 权限检查流程

```typescript
// 来自 src/utils/permissions/permissions.ts
export const hasPermissionsToUseTool: CanUseToolFn = async (
  tool,
  input,
  context,
  assistantMessage,
  toolUseID,
): Promise<PermissionDecision> => {
  const result = await hasPermissionsToUseToolInner(tool, input, context)

  // 1. 如果允许，重置连续拒绝计数
  if (result.behavior === 'allow') {
    const appState = context.getAppState()
    if (appState.toolPermissionContext.mode === 'auto') {
      const newDenialState = recordSuccess(
        context.localDenialTracking ?? appState.denialTracking
      )
      persistDenialState(context, newDenialState)
    }
    return result
  }

  // 2. 应用 dontAsk 模式：'ask' → 'deny'
  if (result.behavior === 'ask') {
    const appState = context.getAppState()

    if (appState.toolPermissionContext.mode === 'dontAsk') {
      return {
        behavior: 'deny',
        decisionReason: { type: 'mode', mode: 'dontAsk' },
        message: DONT_ASK_REJECT_MESSAGE(tool.name),
      }
    }

    // 3. Auto Mode：使用 AI 分类器
    if (feature('TRANSCRIPT_CLASSIFIER') &&
        appState.toolPermissionContext.mode === 'auto') {

      // 检查是否是可以快速通过的操作
      if (tool.name !== 'Agent' && tool.name !== 'REPL') {
        const acceptEditsResult = await tool.checkPermissions(parsedInput, {
          ...context,
          getAppState: () => ({
            ...context.getAppState(),
            toolPermissionContext: {
              ...context.getAppState().toolPermissionContext,
              mode: 'acceptEdits' as const,
            },
          }),
        })
        if (acceptEditsResult.behavior === 'allow') {
          // 快速通过：文件编辑在工作目录内
          return {
            behavior: 'allow',
            updatedInput: acceptEditsResult.updatedInput,
            decisionReason: { type: 'mode', mode: 'auto' },
          }
        }
      }

      // 运行分类器
      const action = formatActionForClassifier(tool.name, input)
      const classifierResult = await classifyYoloAction(
        context.messages,
        action,
        context.options.tools,
        appState.toolPermissionContext,
      )

      if (classifierResult.shouldBlock) {
        // 分类器阻止
        const newDenialState = recordDenial(denialState)
        persistDenialState(context, newDenialState)

        return {
          behavior: 'deny',
          decisionReason: {
            type: 'classifier',
            classifier: 'auto-mode',
            reason: classifierResult.reason,
          },
          message: buildYoloRejectionMessage(classifierResult.reason),
        }
      }

      // 分类器允许
      return {
        behavior: 'allow',
        decisionReason: {
          type: 'classifier',
          classifier: 'auto-mode',
          reason: classifierResult.reason,
        },
      }
    }

    // 4. 无头模式：运行 Hook，然后自动拒绝
    if (appState.toolPermissionContext.shouldAvoidPermissionPrompts) {
      const hookDecision = await runPermissionRequestHooksForHeadlessAgent(
        tool, input, toolUseID, context, appState.toolPermissionContext.mode
      )
      if (hookDecision) {
        return hookDecision
      }
      return {
        behavior: 'deny',
        decisionReason: { type: 'asyncAgent' },
        message: AUTO_REJECT_MESSAGE(tool.name),
      }
    }
  }

  return result
}
```

### 权限规则匹配

```typescript
// 来自 src/utils/permissions/permissions.ts
/**
 * 检查工具是否匹配规则
 * 例如："Bash" 匹配规则 "Bash"，但不匹配 "Bash(prefix:*)"
 */
function toolMatchesRule(
  tool: Pick<Tool, 'name' | 'mcpInfo'>,
  rule: PermissionRule,
): boolean {
  // 规则必须没有 content 才能匹配整个工具
  if (rule.ruleValue.ruleContent !== undefined) {
    return false
  }

  // MCP 工具通过 server__tool 名称匹配
  const nameForRuleMatch = getToolNameForPermissionCheck(tool)

  // 直接工具名称匹配
  if (rule.ruleValue.toolName === nameForRuleMatch) {
    return true
  }

  // MCP 服务器级别权限：规则 "mcp__server1" 匹配工具 "mcp__server1__tool1"
  const ruleInfo = mcpInfoFromString(rule.ruleValue.toolName)
  const toolInfo = mcpInfoFromString(nameForRuleMatch)

  return (
    ruleInfo !== null &&
    toolInfo !== null &&
    (ruleInfo.toolName === undefined || ruleInfo.toolName === '*') &&
    ruleInfo.serverName === toolInfo.serverName
  )
}

/**
 * 获取拒绝规则
 */
export function getDenyRuleForTool(
  context: ToolPermissionContext,
  tool: Pick<Tool, 'name' | 'mcpInfo'>,
): PermissionRule | null {
  return getDenyRules(context).find(rule => toolMatchesRule(tool, rule)) || null
}
```

### 文件系统权限检查

```typescript
// 来自 src/utils/permissions/filesystem.ts
export async function checkWritePermissionForTool(
  tool: Tool,
  input: { file_path: string },
  context: ToolPermissionContext,
): Promise<PermissionDecision> {
  const fullFilePath = expandPath(input.file_path)

  // 检查拒绝规则
  const denyRule = matchingRuleForInput(
    fullFilePath,
    context,
    'edit',
    'deny',
  )
  if (denyRule !== null) {
    return {
      behavior: 'deny',
      decisionReason: { type: 'rule', rule: denyRule },
      message: `Permission to write to ${fullFilePath} has been denied.`,
    }
  }

  // 检查询问规则
  const askRule = matchingRuleForInput(
    fullFilePath,
    context,
    'edit',
    'ask',
  )
  if (askRule !== null) {
    return {
      behavior: 'ask',
      decisionReason: { type: 'rule', rule: askRule },
      message: `Permission to write to ${fullFilePath} requires approval.`,
    }
  }

  // 默认允许
  return {
    behavior: 'allow',
    updatedInput: input,
  }
}
```

---

## 3.6 工具执行流程

### 完整执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 模型决定调用工具                                              │
│    API 返回：content_block { type: 'tool_use', name: 'Bash', ... }│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 查找工具定义                                                  │
│    const tool = tools.find(t => t.name === 'Bash')              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 验证输入 Schema                                               │
│    const parsedInput = tool.inputSchema.parse(rawInput)         │
│    - Zod 验证并转换类型                                          │
│    - 失败则返回错误                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 检查权限                                                      │
│    const permission = await hasPermissionsToUseTool(            │
│      tool, parsedInput, context                                 │
│    )                                                            │
│    - 检查拒绝规则                                                │
│    - 检查询问规则                                                │
│    - Auto Mode 分类器                                            │
│    - 用户确认（交互式）                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. 执行工具                                                      │
│    const result = await tool.call(                              │
│      parsedInput,                                               │
│      context,                                                   │
│      canUseTool,                                                │
│      parentMessage,                                             │
│      onProgress                                                 │
│    )                                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. 处理结果                                                      │
│    - 限制结果大小                                                 │
│    - 生成 UI 渲染                                                  │
│    - 追加到消息历史                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. 发送工具结果给 API                                            │
│    messages.push({                                              │
│      role: 'user',                                              │
│      content: [{                                                │
│        type: 'tool_result',                                     │
│        tool_use_id: toolUseId,                                  │
│        content: resultData                                      │
│      }]                                                         │
│    })                                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 代码实现

```typescript
// 来自 src/services/api/claude.ts — 简化的工具执行逻辑
async function handleToolUse(
  toolUse: BetaToolUseBlock,
  tools: Tools,
  context: ToolUseContext,
): Promise<BetaToolResultBlockParam> {
  // 1. 查找工具
  const tool = tools.find(t => toolMatchesName(t, toolUse.name))
  if (!tool) {
    return {
      type: 'tool_result',
      tool_use_id: toolUse.id,
      content: `Unknown tool: ${toolUse.name}`,
    }
  }

  // 2. 验证输入
  let parsedInput
  try {
    parsedInput = tool.inputSchema.parse(toolUse.input)
  } catch (e) {
    return {
      type: 'tool_result',
      tool_use_id: toolUse.id,
      content: `Invalid input: ${e.message}`,
    }
  }

  // 3. 检查权限
  const permission = await hasPermissionsToUseTool(
    tool,
    parsedInput,
    context,
    parentMessage,
    toolUse.id,
  )

  if (permission.behavior === 'deny') {
    return {
      type: 'tool_result',
      tool_use_id: toolUse.id,
      content: permission.message,
      is_error: true,
    }
  }

  // 4. 执行工具
  try {
    const result = await tool.call(
      parsedInput,
      context,
      canUseTool,
      parentMessage,
      onProgress,
    )

    // 5. 转换结果为 API 格式
    return tool.mapToolResultToToolResultBlockParam(
      result.data,
      toolUse.id,
    )
  } catch (e) {
    return {
      type: 'tool_result',
      tool_use_id: toolUse.id,
      content: `Error: ${e.message}`,
      is_error: true,
    }
  }
}
```

---

## 3.7 工具 UI 渲染

### 工具使用消息渲染

```typescript
// 来自 src/tools/BashTool/UI.tsx
import { Box, Text } from 'ink'
import chalk from 'chalk'

export function renderToolUseMessage(
  input: Partial<BashToolInput>,
  options: { theme: ThemeName; verbose: boolean },
): React.ReactNode {
  const { command, description } = input

  return (
    <Box flexDirection="column">
      <Box>
        <Text bgHex={themeColors[options.theme].bgBlue}>
          <Text color="blue">Bash</Text>
        </Text>
        {description && (
          <Text dimColor> — {description}</Text>
        )}
      </Box>
      <Box paddingLeft={2}>
        <Text>{command}</Text>
      </Box>
    </Box>
  )
}
```

### 工具结果消息渲染

```typescript
// 来自 src/tools/BashTool/UI.tsx
export function renderToolResultMessage(
  content: BashToolOutput,
  options: {
    style?: 'condensed'
    theme: ThemeName
    verbose: boolean
  },
): React.ReactNode {
  const { stdout, stderr, backgroundTaskId } = content

  // 后台任务
  if (backgroundTaskId) {
    return (
      <Box flexDirection="column">
        <Text dimColor>Command running in background (ID: {backgroundTaskId})</Text>
        <Text dimColor>Use TaskOutputTool to check progress</Text>
      </Box>
    )
  }

  // 压缩模式
  if (options.style === 'condensed') {
    const lines = (stdout || stderr || '').split('\n').slice(0, 5)
    return (
      <Box flexDirection="column">
        {lines.map((line, i) => (
          <Text key={i} dimColor>{line}</Text>
        ))}
        {lines.length < (stdout || stderr || '').split('\n').length && (
          <Text dimColor>...</Text>
        )}
      </Box>
    )
  }

  // 详细模式
  return (
    <Box flexDirection="column">
      {stdout && (
        <Box flexDirection="column">
          <Text dimColor>stdout:</Text>
          <Text>{stdout}</Text>
        </Box>
      )}
      {stderr && (
        <Box flexDirection="column">
          <Text dimColor color="yellow">stderr:</Text>
          <Text color="yellow">{stderr}</Text>
        </Box>
      )}
    </Box>
  )
}
```

---

## 3.8 自定义工具开发指南

### 步骤 1：定义输入输出 Schema

```typescript
// my-tool.ts
import { z } from 'zod/v4'
import { lazySchema } from '../../utils/lazySchema.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    query: z.string().describe('The search query'),
    limit: z.number().optional().describe('Maximum results to return'),
  })
)

const outputSchema = lazySchema(() =>
  z.object({
    results: z.array(z.object({
      title: z.string(),
      url: z.string(),
      snippet: z.string(),
    })),
    total: z.number(),
  })
)

type InputSchema = ReturnType<typeof inputSchema>
type OutputSchema = ReturnType<typeof outputSchema>
```

### 步骤 2：实现工具

```typescript
// my-tool.ts
export const MySearchTool = buildTool({
  name: 'MySearchTool',
  searchHint: 'search external data source',
  maxResultSizeChars: 50_000,

  // Schema
  get inputSchema(): InputSchema { return inputSchema() },
  get outputSchema(): OutputSchema { return outputSchema() },

  // 描述
  async description() {
    return 'Search an external data source for information.'
  },

  // 核心执行方法
  async call(input, context) {
    // 调用外部 API
    const response = await fetch(`https://api.example.com/search?q=${input.query}`)
    const data = await response.json()

    // 构建结果
    const output: Output = {
      results: data.results.slice(0, input.limit || 10),
      total: data.total,
    }

    return { data: output }
  },

  // UI 渲染
  renderToolUseMessage(input) {
    return (
      <Box>
        <Text color="cyan">Searching:</Text>
        <Text> {input.query}</Text>
      </Box>
    )
  },

  renderToolResultMessage(content) {
    return (
      <Box flexDirection="column">
        <Text>Found {content.total} results</Text>
        {content.results.map((r, i) => (
          <Box key={i} flexDirection="column">
            <Text bold>{r.title}</Text>
            <Text dimColor>{r.snippet}</Text>
          </Box>
        ))}
      </Box>
    )
  },
})
```

### 步骤 3：注册工具

```typescript
// tools.ts
import { MySearchTool } from './tools/MySearchTool/MySearchTool.js'

export function getAllBaseTools(): Tools {
  return [
    // ... 现有工具
    ...(isEnvTruthy(process.env.ENABLE_MY_SEARCH) ? [MySearchTool] : []),
  ]
}
```

---

## 3.9 关键设计模式

### 1. Schema 验证模式

使用 Zod 进行运行时验证：

```typescript
// 定义时验证
const parsedInput = tool.inputSchema.parse(rawInput)

// 类型推断
type Input = z.infer<typeof inputSchema>
```

### 2. 构建器模式

`buildTool` 提供默认值：

```typescript
const tool = buildTool({
  name: 'MyTool',
  // 其他方法可选，使用默认值
  // isEnabled: () => true (默认)
  // isConcurrencySafe: () => false (默认)
})
```

### 3. 策略模式

不同工具有不同的权限策略：

```typescript
// Bash 工具：基于命令内容
async checkPermissions(input) {
  return checkBashPermission(input.command)
}

// FileWrite 工具：基于文件路径
async checkPermissions(input) {
  return checkWritePermission(input.file_path)
}
```

### 4. 适配器模式

MCP 工具适配为标准 Tool 接口：

```typescript
function wrapAsMcpTool(mcpTool: MCPTool, serverName: string): Tool {
  return buildTool({
    name: `mcp__${serverName}__${mcpTool.name}`,
    inputJSONSchema: mcpTool.inputSchema,
    async call(input, context) {
      return mcpTool.client.execute(input)
    },
    // ...
  })
}
```

---

## 3.10 关键代码位置索引

| 功能 | 文件路径 | 关键函数/类型 |
|------|----------|---------------|
| 工具接口 | `src/Tool.ts` | `Tool`, `buildTool`, `ToolDef` |
| 工具注册 | `src/tools.ts` | `getTools`, `assembleToolPool` |
| Bash 工具 | `src/tools/BashTool/BashTool.tsx` | `BashTool`, `BashToolInput` |
| 文件写入 | `src/tools/FileWriteTool/FileWriteTool.ts` | `FileWriteTool` |
| 权限检查 | `src/utils/permissions/permissions.ts` | `hasPermissionsToUseTool` |
| 文件权限 | `src/utils/permissions/filesystem.ts` | `checkWritePermissionForTool` |
| UI 渲染 | `src/tools/BashTool/UI.tsx` | `renderToolUseMessage` |
| MCP 工具 | `src/services/mcp/client.ts` | `getMcpToolsCommandsAndResources` |

---

## 课后练习

1. **阅读代码**：
   - 打开 `src/Tool.ts`，完整阅读 `Tool` 接口定义
   - 打开 `src/tools/BashTool/BashTool.tsx`，查看 `isSearchOrReadBashCommand` 函数的实现
   - 打开 `src/tools/FileWriteTool/FileWriteTool.ts`，查看 `validateInput` 函数

2. **思考问题**：
   - 为什么使用 `buildTool` 而不是直接实现 `Tool` 接口？
   - 工具为什么要区分 `isReadOnly` 和 `isDestructive`？
   - MCP 工具如何与内置工具统一接口？

3. **实践**：
   - 尝试设计一个自定义工具的 Schema
   - 为你的工具设计权限检查逻辑

---

**下一步**：[第 4 篇 — 会话与状态管理](./04-session-and-state-management.md)
