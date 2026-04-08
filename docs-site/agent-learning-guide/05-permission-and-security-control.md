# 第 5 篇：权限与安全控制

## 学习目标

- 理解 Agent 权限系统的设计原则
- 掌握权限规则的配置和执行流程
- 学习 Auto Mode 分类器的工作原理
- 了解安全边界和风险控制机制

---

## 5.1 权限模式

### 权限模式类型

```typescript
// 来自 src/types/permissions.ts
export const PERMISSION_MODES = [
  'default',       // 默认模式：询问所有未明确允许的操作
  'plan',          // 计划模式：暂停等待用户批准计划
  'acceptEdits',   // 接受编辑模式：自动允许工作目录内的文件编辑
  'bypassPermissions', // 绕过权限：允许所有操作（危险）
  'dontAsk',       // 不询问：拒绝所有需要询问的操作
  'auto',          // 自动模式：使用 AI 分类器决定（需要 TRANSCRIPT_CLASSIFIER 特性）
] as const

export type PermissionMode = typeof PERMISSION_MODES[number]
```

### 模式配置

```typescript
// 来自 src/utils/permissions/PermissionMode.ts
type PermissionModeConfig = {
  title: string        // 显示名称
  shortTitle: string   // 简称
  symbol: string       // UI 符号
  color: ModeColorKey  // 颜色主题
  external: ExternalPermissionMode
}

const PERMISSION_MODE_CONFIG = {
  default: {
    title: 'Default',
    shortTitle: 'Default',
    symbol: '',
    color: 'text',
    external: 'default',
  },
  plan: {
    title: 'Plan Mode',
    shortTitle: 'Plan',
    symbol: '⏸',  // 暂停符号
    color: 'planMode',
    external: 'plan',
  },
  acceptEdits: {
    title: 'Accept edits',
    shortTitle: 'Accept',
    symbol: '⏵⏵',  // 快进符号
    color: 'autoAccept',
    external: 'acceptEdits',
  },
  auto: {
    title: 'Auto mode',
    shortTitle: 'Auto',
    symbol: '⏵⏵',
    color: 'warning',
    external: 'default',
  },
  // ...
}
```

---

## 5.2 权限规则系统

### 规则结构

```typescript
// 来自 src/types/permissions.ts
/**
 * 权限规则值
 */
export type PermissionRuleValue = {
  toolName: string      // 工具名称，如 "Bash"
  ruleContent?: string  // 可选的规则内容，如命令前缀或文件路径
}

/**
 * 权限规则
 */
export type PermissionRule = {
  source: PermissionRuleSource    // 规则来源
  ruleBehavior: PermissionBehavior // 允许/拒绝/询问
  ruleValue: PermissionRuleValue   // 规则内容
}

/**
 * 规则来源（优先级从低到高）
 */
export type PermissionRuleSource =
  | 'localSettings'    // 本地设置
  | 'userSettings'     // 用户设置
  | 'projectSettings'  // 项目设置
  | 'cliArg'           // 命令行参数
  | 'session'          // 会话临时规则
  | 'policySettings'   // 策略设置（只读）
  | 'flagSettings'     // 特性标志设置（只读）
  | 'command'          // 命令临时规则
```

### 规则解析

```typescript
// 来自 src/utils/permissions/permissionRuleParser.ts
/**
 * 字符串 → PermissionRuleValue
 *
 * 示例：
 *   "Bash"           → { toolName: "Bash" }
 *   "Bash(git *)"    → { toolName: "Bash", ruleContent: "git *" }
 *   "FileWrite(src/*)" → { toolName: "FileWrite", ruleContent: "src/*" }
 */
export function permissionRuleValueFromString(
  str: string,
): PermissionRuleValue {
  const match = str.match(/^(\w+)(?:\((.+)\))?$/)

  if (!match) {
    return { toolName: str }
  }

  return {
    toolName: match[1],
    ruleContent: match[2],
  }
}

/**
 * PermissionRuleValue → 字符串
 */
export function permissionRuleValueToString(
  rule: PermissionRuleValue,
): string {
  if (!rule.ruleContent) {
    return rule.toolName
  }
  return `${rule.toolName}(${rule.ruleContent})`
}
```

---

## 5.3 权限检查流程

### 完整流程

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

  // === 步骤 1: 处理允许的决定 ===
  if (result.behavior === 'allow') {
    // 在 Auto Mode 下重置连续拒绝计数
    const appState = context.getAppState()
    if (appState.toolPermissionContext.mode === 'auto') {
      const currentDenialState =
        context.localDenialTracking ?? appState.denialTracking
      if (currentDenialState && currentDenialState.consecutiveDenials > 0) {
        const newDenialState = recordSuccess(currentDenialState)
        persistDenialState(context, newDenialState)
      }
    }
    return result
  }

  // === 步骤 2: 应用 dontAsk 模式 ===
  if (result.behavior === 'ask') {
    const appState = context.getAppState()

    if (appState.toolPermissionContext.mode === 'dontAsk') {
      return {
        behavior: 'deny',
        decisionReason: { type: 'mode', mode: 'dontAsk' },
        message: DONT_ASK_REJECT_MESSAGE(tool.name),
      }
    }

    // === 步骤 3: Auto Mode 分类器 ===
    if (feature('TRANSCRIPT_CLASSIFIER') &&
        appState.toolPermissionContext.mode === 'auto') {

      return await handleAutoModeClassifier(
        tool, input, context, assistantMessage, result
      )
    }

    // === 步骤 4: 无头模式（无 UI）===
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

### 内层权限检查

```typescript
// 来自 src/utils/permissions/permissions.ts
async function hasPermissionsToUseToolInner(
  tool: Tool,
  input: { [key: string]: unknown },
  context: ToolUseContext,
): Promise<PermissionDecision> {
  let appState = context.getAppState()

  // === 步骤 1a: 检查工具拒绝规则 ===
  const denyRule = getDenyRuleForTool(appState.toolPermissionContext, tool)
  if (denyRule) {
    return {
      behavior: 'deny',
      decisionReason: { type: 'rule', rule: denyRule },
      message: `Permission to use ${tool.name} has been denied.`,
    }
  }

  // === 步骤 1b: 检查工具询问规则 ===
  const askRule = getAskRuleForTool(appState.toolPermissionContext, tool)
  if (askRule) {
    const canSandboxAutoAllow =
      tool.name === BASH_TOOL_NAME &&
      SandboxManager.isSandboxingEnabled() &&
      SandboxManager.isAutoAllowBashIfSandboxedEnabled() &&
      shouldUseSandbox(input)

    if (!canSandboxAutoAllow) {
      return {
        behavior: 'ask',
        decisionReason: { type: 'rule', rule: askRule },
        message: createPermissionRequestMessage(tool.name),
      }
    }
  }

  // === 步骤 1c: 工具特定权限检查 ===
  let toolPermissionResult: PermissionResult = {
    behavior: 'passthrough',
    message: createPermissionRequestMessage(tool.name),
  }
  try {
    const parsedInput = tool.inputSchema.parse(input)
    toolPermissionResult = await tool.checkPermissions(parsedInput, context)
  } catch (e) {
    if (e instanceof AbortError || e instanceof APIUserAbortError) {
      throw e
    }
    logError(e)
  }

  // === 步骤 1d: 工具实现拒绝 ===
  if (toolPermissionResult?.behavior === 'deny') {
    return toolPermissionResult
  }

  // === 步骤 1e: 需要用户交互的工具 ===
  if (
    tool.requiresUserInteraction?.() &&
    toolPermissionResult?.behavior === 'ask'
  ) {
    return toolPermissionResult
  }

  // === 步骤 1f: 内容特定的询问规则 ===
  if (
    toolPermissionResult?.behavior === 'ask' &&
    toolPermissionResult.decisionReason?.type === 'rule' &&
    toolPermissionResult.decisionReason.rule.ruleBehavior === 'ask'
  ) {
    return toolPermissionResult
  }

  // === 步骤 1g: 安全检查（.git/, .claude/等）===
  if (
    toolPermissionResult?.behavior === 'ask' &&
    toolPermissionResult.decisionReason?.type === 'safetyCheck'
  ) {
    return toolPermissionResult
  }

  // === 步骤 2a: 检查模式是否允许 ===
  appState = context.getAppState()
  const shouldBypassPermissions =
    appState.toolPermissionContext.mode === 'bypassPermissions' ||
    (appState.toolPermissionContext.mode === 'plan' &&
      appState.toolPermissionContext.isBypassPermissionsModeAvailable)

  if (shouldBypassPermissions) {
    return {
      behavior: 'allow',
      updatedInput: getUpdatedInputOrFallback(toolPermissionResult, input),
      decisionReason: { type: 'mode', mode: appState.toolPermissionContext.mode },
    }
  }

  // === 步骤 2b: 工具完全允许 ===
  const alwaysAllowedRule = toolAlwaysAllowedRule(
    appState.toolPermissionContext,
    tool,
  )
  if (alwaysAllowedRule) {
    return {
      behavior: 'allow',
      updatedInput: getUpdatedInputOrFallback(toolPermissionResult, input),
      decisionReason: { type: 'rule', rule: alwaysAllowedRule },
    }
  }

  // === 步骤 3: 将 "passthrough" 转换为 "ask" ===
  const result: PermissionDecision =
    toolPermissionResult.behavior === 'passthrough'
      ? {
          ...toolPermissionResult,
          behavior: 'ask' as const,
          message: createPermissionRequestMessage(
            tool.name,
            toolPermissionResult.decisionReason,
          ),
        }
      : toolPermissionResult

  return result
}
```

---

## 5.4 Auto Mode 分类器

### 分类器工作流程

```typescript
// 来自 src/utils/permissions/permissions.ts
async function handleAutoModeClassifier(
  tool: Tool,
  input: { [key: string]: unknown },
  context: ToolUseContext,
  assistantMessage: AssistantMessage,
  result: PermissionDecision,
): Promise<PermissionDecision> {
  const appState = context.getAppState()

  // === 安全检查：需要交互式审批的路径 ===
  if (
    result.decisionReason?.type === 'safetyCheck' &&
    !result.decisionReason.classifierApprovable
  ) {
    if (appState.toolPermissionContext.shouldAvoidPermissionPrompts) {
      return {
        behavior: 'deny',
        message: result.message,
        decisionReason: {
          type: 'asyncAgent',
          reason: 'Safety check requires interactive approval',
        },
      }
    }
    return result
  }

  // === 需要用户交互的工具 ===
  if (tool.requiresUserInteraction?.() && result.behavior === 'ask') {
    return result
  }

  // === 获取拒绝跟踪状态 ===
  const denialState =
    context.localDenialTracking ??
    appState.denialTracking ??
    createDenialTrackingState()

  // === PowerShell 特殊处理 ===
  if (
    tool.name === POWERSHELL_TOOL_NAME &&
    !feature('POWERSHELL_AUTO_MODE')
  ) {
    if (appState.toolPermissionContext.shouldAvoidPermissionPrompts) {
      return {
        behavior: 'deny',
        message: 'PowerShell tool requires interactive approval',
        decisionReason: {
          type: 'asyncAgent',
          reason: 'PowerShell requires interactive approval',
        },
      }
    }
    return result
  }

  // === 快速路径 1: acceptEdits 模式检查 ===
  if (
    result.behavior === 'ask' &&
    tool.name !== AGENT_TOOL_NAME &&
    tool.name !== REPL_TOOL_NAME
  ) {
    try {
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
        const newDenialState = recordSuccess(denialState)
        persistDenialState(context, newDenialState)

        logEvent('tengu_auto_mode_decision', {
          decision: 'allowed',
          toolName: sanitizeToolNameForAnalytics(tool.name),
          confidence: 'high',
          fastPath: 'acceptEdits',
          agentMsgId: assistantMessage.message.id,
        })

        return {
          behavior: 'allow',
          updatedInput: acceptEditsResult.updatedInput,
          decisionReason: { type: 'mode', mode: 'auto' },
        }
      }
    } catch (e) {
      // 分类器回退
    }
  }

  // === 快速路径 2: 安全工具白名单 ===
  if (classifierDecisionModule!.isAutoModeAllowlistedTool(tool.name)) {
    const newDenialState = recordSuccess(denialState)
    persistDenialState(context, newDenialState)

    logEvent('tengu_auto_mode_decision', {
      decision: 'allowed',
      toolName: sanitizeToolNameForAnalytics(tool.name),
      confidence: 'high',
      fastPath: 'allowlist',
      agentMsgId: assistantMessage.message.id,
    })

    return {
      behavior: 'allow',
      updatedInput: input,
      decisionReason: { type: 'mode', mode: 'auto' },
    }
  }

  // === 运行分类器 ===
  const action = formatActionForClassifier(tool.name, input)
  setClassifierChecking(toolUseID)

  let classifierResult
  try {
    classifierResult = await classifyYoloAction(
      context.messages,
      action,
      context.options.tools,
      appState.toolPermissionContext,
      context.abortController.signal,
    )
  } finally {
    clearClassifierChecking(toolUseID)
  }

  // === 处理分类器结果 ===
  if (classifierResult.shouldBlock) {
    // 分类器阻止
    const newDenialState = recordDenial(denialState)
    persistDenialState(context, newDenialState)

    // 检查是否超出拒绝限制
    const denialLimitResult = handleDenialLimitExceeded(
      newDenialState,
      appState,
      classifierResult.reason,
      assistantMessage,
      tool,
      result,
      context,
    )
    if (denialLimitResult) {
      return denialLimitResult
    }

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
  const newDenialState = recordSuccess(denialState)
  persistDenialState(context, newDenialState)

  return {
    behavior: 'allow',
    updatedInput: input,
    decisionReason: {
      type: 'classifier',
      classifier: 'auto-mode',
      reason: classifierResult.reason,
    },
  }
}
```

### 分类器 prompt 构造

```typescript
// 来自 src/utils/permissions/yoloClassifier.ts
/**
 * 为分类器构造 action 描述
 */
export function formatActionForClassifier(
  toolName: string,
  input: { [key: string]: unknown },
): string {
  switch (toolName) {
    case 'Bash':
      return `Execute bash command: ${input.command}`

    case 'FileWrite':
      return `Write to file ${input.file_path}: ${truncate(input.content, 100)}`

    case 'FileEdit':
      return `Edit file ${input.file_path}`

    case 'Agent':
      return `Spawn sub-agent: ${input.agent_type || 'general-purpose'} — ${input.prompt}`

    default:
      return `Use ${toolName}`
  }
}

/**
 * 运行分类器 API 调用
 */
export async function classifyYoloAction(
  messages: Message[],
  action: string,
  tools: Tools,
  permissionContext: ToolPermissionContext,
  signal: AbortSignal,
): Promise<ClassifierResult> {
  // 构造分类器 prompt
  const systemPrompt = `
You are a security classifier for an AI coding assistant.
Your task is to determine if an action is safe to execute automatically.

Rules for blocking:
- Commands that download and execute code
- Modifications to sensitive files (.git/, .ssh/, system configs)
- Network operations to untrusted hosts
- Destructive operations without confirmation

Respond with:
- shouldBlock: true/false
- reason: brief explanation
- confidence: high/medium/low
`.trim()

  const userPrompt = `
Current conversation context:
${messages.map(m => formatMessageForClassifier(m)).join('\n\n')}

Action to classify: ${action}

Available tools: ${tools.map(t => t.name).join(', ')}

Current permission mode: ${permissionContext.mode}
`.trim()

  // 调用分类器 API
  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',  // 使用快速模型
    max_tokens: 256,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ],
  })

  // 解析结果
  const content = extractTextContent(response.content[0])
  const parsed = parseClassifierResponse(content)

  return {
    shouldBlock: parsed.shouldBlock,
    reason: parsed.reason,
    confidence: parsed.confidence,
    usage: response.usage,
    model: response.model,
    durationMs: /* 计算耗时 */,
  }
}
```

---

## 5.5 拒绝跟踪

### 拒绝状态管理

```typescript
// 来自 src/utils/permissions/denialTracking.ts
export type DenialTrackingState = {
  consecutiveDenials: number  // 连续拒绝次数
  totalDenials: number        // 总会话拒绝次数
  lastDenialTime?: number     // 上次拒绝时间
}

export const DENIAL_LIMITS = {
  maxConsecutive: 5,  // 连续拒绝上限
  maxTotal: 20,       // 总会话拒绝上限
}

/**
 * 记录一次拒绝
 */
export function recordDenial(
  state: DenialTrackingState,
): DenialTrackingState {
  return {
    consecutiveDenials: state.consecutiveDenials + 1,
    totalDenials: state.totalDenials + 1,
    lastDenialTime: Date.now(),
  }
}

/**
 * 记录一次成功
 */
export function recordSuccess(
  state: DenialTrackingState,
): DenialTrackingState {
  return {
    ...state,
    consecutiveDenials: 0,  // 重置连续计数
  }
}

/**
 * 检查是否应该回退到用户提示
 */
export function shouldFallbackToPrompting(
  state: DenialTrackingState,
): boolean {
  return (
    state.consecutiveDenials >= DENIAL_LIMITS.maxConsecutive ||
    state.totalDenials >= DENIAL_LIMITS.maxTotal
  )
}
```

### 拒绝限制处理

```typescript
// 来自 src/utils/permissions/permissions.ts
function handleDenialLimitExceeded(
  denialState: DenialTrackingState,
  appState: { toolPermissionContext: { shouldAvoidPermissionPrompts?: boolean } },
  classifierReason: string,
  assistantMessage: AssistantMessage,
  tool: Tool,
  result: PermissionDecision,
  context: ToolUseContext,
): PermissionDecision | null {
  if (!shouldFallbackToPrompting(denialState)) {
    return null
  }

  const hitTotalLimit = denialState.totalDenials >= DENIAL_LIMITS.maxTotal
  const isHeadless = appState.toolPermissionContext.shouldAvoidPermissionPrompts

  const warning = hitTotalLimit
    ? `${denialState.totalDenials} actions were blocked this session.`
    : `${denialState.consecutiveDenials} consecutive actions were blocked.`

  logEvent('tengu_auto_mode_denial_limit_exceeded', {
    limit: hitTotalLimit ? 'total' : 'consecutive',
    mode: isHeadless ? 'headless' : 'cli',
    messageID: assistantMessage.message.id,
    consecutiveDenials: denialState.consecutiveDenials,
    totalDenials: denialState.totalDenials,
    toolName: sanitizeToolNameForAnalytics(tool.name),
  })

  // 无头模式：直接中止
  if (isHeadless) {
    throw new AbortError(
      'Agent aborted: too many classifier denials in headless mode',
    )
  }

  // 交互式模式：回退到用户提示
  logForDebugging(
    `Classifier denial limit exceeded, falling back to prompting: ${warning}`,
    { level: 'warn' },
  )

  // 重置计数器
  if (hitTotalLimit) {
    persistDenialState(context, {
      ...denialState,
      totalDenials: 0,
      consecutiveDenials: 0,
    })
  }

  return {
    ...result,
    decisionReason: {
      type: 'classifier',
      classifier: 'auto-mode',
      reason: `${warning}\n\nLatest blocked action: ${classifierReason}`,
    },
  }
}
```

---

## 5.6 文件系统权限

### 写入权限检查

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

### 路径规则匹配

```typescript
// 来自 src/utils/permissions/shellRuleMatching.ts
/**
 * 匹配通配符模式
 *
 * 支持的模式：
 * - 精确匹配："src/index.ts"
 * - 通配符："src/*.ts"
 * - 目录前缀："src/**"
 * - glob 风格："**/*.test.ts"
 */
export function matchWildcardPattern(
  pattern: string,
  filePath: string,
): boolean {
  // 转换为正则表达式
  const regexPattern = pattern
    .replace(/[.+?^${}()|[\]\\]/g, '\\$&')  // 转义特殊字符
    .replace(/\*\*/g, '___DOUBLE_STAR___')  // 临时替换 **
    .replace(/\*/g, '[^/]*')                 // * → 非斜杠字符
    .replace('___DOUBLE_STAR___', '.*')      // ** → 任意字符

  const regex = new RegExp(`^${regexPattern}$`)
  return regex.test(filePath)
}

/**
 * 检查路径是否匹配规则
 */
export function matchingRuleForInput(
  filePath: string,
  context: ToolPermissionContext,
  operation: 'read' | 'edit',
  behavior: PermissionBehavior,
): PermissionRule | null {
  const rules = getRulesForBehavior(context, behavior)

  for (const rule of rules) {
    const { toolName, ruleContent } = rule.ruleValue

    // 检查工具名称
    if (
      toolName !== 'FileWrite' &&
      toolName !== 'FileEdit' &&
      toolName !== 'FileRead'
    ) {
      continue
    }

    // 检查路径模式
    if (ruleContent && matchWildcardPattern(ruleContent, filePath)) {
      return rule
    }
  }

  return null
}
```

---

## 5.7 安全检查

### 敏感路径保护

```typescript
// 来自 src/utils/permissions/autoModeState.ts
const SENSITIVE_PATHS = [
  '.git/',
  '.claude/',
  '.vscode/',
  '.ssh/',
  '.env',
  'node_modules/',
  // 系统配置
  '/etc/',
  '/usr/',
  // Windows 敏感路径
  'C:/Windows/',
  'C:/Program Files/',
]

/**
 * 检查路径是否在敏感目录中
 */
export function isSensitivePath(filePath: string): boolean {
  const normalized = filePath.toLowerCase()

  for (const sensitivePath of SENSITIVE_PATHS) {
    if (
      normalized.includes(sensitivePath.toLowerCase()) ||
      normalized.startsWith(sensitivePath.toLowerCase())
    ) {
      return true
    }
  }

  return false
}

/**
 * 检查写操作是否需要安全检查
 */
export function checkPathSafetyForAutoEdit(
  filePath: string,
): { type: 'safetyCheck'; classifierApprovable?: boolean } | null {
  if (isSensitivePath(filePath)) {
    return {
      type: 'safetyCheck',
      classifierApprovable: false,  // 敏感路径不能通过分类器绕过
    }
  }

  return null
}
```

---

## 5.8 Hook 权限检查

```typescript
// 来自 src/utils/hooks.js
/**
 * 执行 PreToolUse Hooks
 */
export async function executePreToolUseHooks(
  toolName: string,
  input: { [key: string]: unknown },
  context: ToolUseContext,
): Promise<HookResult[]> {
  const hooks = getRegisteredHooks('PreToolUse')
  const results = []

  for (const hook of hooks) {
    // 检查 if 条件
    if (hook.if && !evaluateHookCondition(hook.if, toolName, input)) {
      continue
    }

    try {
      const result = await executeHook(hook, { toolName, input, context })
      results.push(result)
    } catch (e) {
      logError(`Hook ${hook.name} failed: ${e.message}`)
    }
  }

  return results
}

/**
 * 执行 PermissionRequest Hooks（用于无头模式）
 */
async function runPermissionRequestHooksForHeadlessAgent(
  tool: Tool,
  input: { [key: string]: unknown },
  toolUseID: string,
  context: ToolUseContext,
  permissionMode: string | undefined,
  suggestions: PermissionUpdate[] | undefined,
): Promise<PermissionDecision | null> {
  for await (const hookResult of executePermissionRequestHooks(
    tool.name,
    toolUseID,
    input,
    context,
    permissionMode,
    suggestions,
    context.abortController.signal,
  )) {
    if (!hookResult.permissionRequestResult) {
      continue
    }

    const decision = hookResult.permissionRequestResult

    if (decision.behavior === 'allow') {
      // 持久化权限更新
      if (decision.updatedPermissions?.length) {
        persistPermissionUpdates(decision.updatedPermissions)
      }
      return decision
    }

    if (decision.behavior === 'deny') {
      return decision
    }
  }

  return null  // 无 Hook 提供决定
}
```

---

## 5.9 规则优先级

```
权限检查优先级（从高到低）：

1. 安全检查（.git/, .claude/ 等）— 不可绕过
2. 拒绝规则（deny）
3. 询问规则（ask）
4. 工具特定检查（tool.checkPermissions）
5. 需要用户交互的工具
6. 模式转换
   - bypassPermissions → 允许所有
   - dontAsk → 拒绝所有需要询问的
   - auto → 分类器决定
   - acceptEdits → 允许工作目录内的编辑
7. 允许规则（allow）
8. 默认行为 → 询问用户
```

---

## 5.10 关键代码位置索引

| 功能 | 文件路径 | 关键函数/类型 |
|------|----------|---------------|
| 权限模式 | `src/types/permissions.ts` | `PermissionMode`, `PERMISSION_MODES` |
| 权限规则 | `src/types/permissions.ts` | `PermissionRule`, `PermissionRuleValue` |
| 权限检查 | `src/utils/permissions/permissions.ts` | `hasPermissionsToUseTool` |
| 文件权限 | `src/utils/permissions/filesystem.ts` | `checkWritePermissionForTool` |
| 规则匹配 | `src/utils/permissions/shellRuleMatching.ts` | `matchWildcardPattern` |
| 拒绝跟踪 | `src/utils/permissions/denialTracking.ts` | `DenialTrackingState`, `recordDenial` |
| Auto Mode | `src/utils/permissions/yoloClassifier.ts` | `classifyYoloAction` |
| 安全检查 | `src/utils/permissions/autoModeState.ts` | `isSensitivePath` |
| Hook 执行 | `src/utils/hooks.js` | `executePreToolUseHooks` |

---

## 课后练习

1. **阅读代码**：
   - 打开 `src/utils/permissions/permissions.ts`，完整阅读 `hasPermissionsToUseTool` 函数
   - 打开 `src/utils/permissions/shellRuleMatching.ts`，查看通配符匹配实现
   - 打开 `src/utils/permissions/denialTracking.ts`，理解拒绝跟踪逻辑

2. **思考问题**：
   - 为什么要有多个规则来源（local、user、project）？
   - Auto Mode 分类器的快速路径有什么作用？
   - 如何处理拒绝限制被触发的情况？

3. **实践**：
   - 设计一个权限规则配置格式
   - 实现简单的路径通配符匹配函数

---

**下一步**：[第 6 篇 — MCP 与外部集成](./06-mcp-and-external-integration.md)
