# SimpleAgent

基于第 08 篇教程构建的轻量级 Agent 系统示例。

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 设置环境变量

```bash
export OPENAI_API_KEY=your-api-key-here
```

### 3. 运行示例

```bash
# 基本用法
npm run example:basic

# 交互式 REPL
npm run example:repl

# 自定义工具示例
npm run example:custom-tool

# 多 Agent 协作示例
npm run example:multi-agent
```

## 项目结构

```
simple-agent/
├── src/
│   ├── agent/
│   │   ├── Agent.ts          # Agent 核心类
│   │   ├── LLMClient.ts      # OpenAI 客户端封装
│   │   └── types.ts          # 类型定义
│   ├── tools/
│   │   ├── Tool.ts           # Tool 接口定义
│   │   ├── BashTool.ts       # Bash 工具
│   │   ├── FileReadTool.ts   # 文件读取工具
│   │   ├── FileWriteTool.ts  # 文件写入工具
│   │   └── index.ts          # 工具注册
│   ├── state/
│   │   ├── StateStore.ts     # 状态管理
│   │   └── SessionStorage.ts # 会话持久化
│   ├── permissions/
│   │   ├── PermissionChecker.ts  # 权限检查
│   │   └── types.ts              # 权限类型
│   └── index.ts              # 统一导出
├── examples/
│   ├── basic-usage.ts        # 基本用法
│   ├── repl.ts               # 交互式 REPL
│   └── custom-tool.ts        # 自定义工具
├── tests/
│   └── agent.test.ts         # 测试文件
├── package.json
├── tsconfig.json
└── tsup.config.ts
```

## 核心功能

### 1. LLM 客户端

封装 OpenAI API，支持工具调用：

```typescript
import { LLMClient } from './agent/LLMClient.js'

const client = new LLMClient({
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
  maxTokens: 4096,
})
```

### 2. Agent 核心

```typescript
import { Agent } from './agent/Agent.js'
import { builtInTools } from './tools/index.js'

const agent = new Agent({
  cwd: process.cwd(),
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
  maxTokens: 4096,
  permissionMode: 'bypassPermissions',
})

agent.registerTools(builtInTools)
agent.addUserMessage('创建一个新的 TypeScript 项目')
const result = await agent.run()
```

### 3. 自定义工具

```typescript
import { buildTool } from './tools/Tool.js'
import { z } from 'zod'

const WeatherTool = buildTool({
  name: 'GetWeather',
  description: 'Get current weather for a city',
  inputSchema: z.object({
    city: z.string(),
  }),
  isConcurrencySafe: () => true,
  isReadOnly: () => true,
  async call(input, context) {
    return {
      content: `Weather in ${input.city}: sunny, 25°C`,
    }
  },
})
```

## 权限模式

| 模式 | 说明 |
|------|------|
| `default` | 默认：需要用户确认 |
| `bypassPermissions` | 跳过权限检查 |
| `dontAsk` | 自动拒绝 |
| `acceptEdits` | 自动允许只读操作 |
| `auto` | AI 自动分类 |

## 健壮性特性

SimpleAgent TypeScript 版本包含以下健壮性改进：

### 1. 配置验证
- **API 密钥验证**：初始化时检查 API 密钥是否为空
- **模型验证**：检查模型名称是否有效
- **参数范围验证**：`maxTokens` 必须为正数，`maxIterations` 必须为正数

### 2. 输入验证
- **工具输入验证**：使用 Zod 模式验证工具输入参数（双重验证：Agent 层面和工具层面）
- **友好的错误消息**：提供详细的验证错误信息，帮助调试

### 3. 超时与取消
- **全局超时**：通过 `timeoutMs` 配置项设置 Agent 执行超时时间
- **AbortSignal 支持**：支持标准的 `AbortSignal` 取消长时间运行的任务
- **工具执行超时**：单个工具执行超过指定时间会自动取消
- **LLM 请求超时**：OpenAI API 调用支持超时和取消

### 4. 错误处理
- **详细的错误分类**：区分工具未找到、权限拒绝、输入无效、执行错误、取消等
- **取消支持**：支持 `AbortError`，可优雅取消任务
- **最大迭代次数保护**：防止无限循环，默认 50 次，可配置
- **状态一致性**：确保在异常情况下正确重置处理状态

### 5. 类型安全
- **完整的 TypeScript 类型**：提供完整的类型定义和类型推断
- **Zod 模式集成**：工具输入使用 Zod 进行运行时类型验证

### 使用示例

```typescript
const controller = new AbortController()

const agent = new Agent({
  cwd: process.cwd(),
  apiKey: process.env.OPENAI_API_KEY!,
  model: 'gpt-4o',
  maxTokens: 4096,
  permissionMode: 'bypassPermissions',
  maxIterations: 20,      // 限制最大迭代次数
  timeoutMs: 30000,       // 30秒超时
  signal: controller.signal, // 可选的 AbortSignal
})

// 可以通过 controller.abort() 取消任务
```

## 构建

```bash
npm run build
```

## 测试

```bash
npm test
```

## 学习资源

- [第 08 篇：实战构建自己的 Agent](../../docs-site/agent-learning-guide/08-build-your-own-agent.md)
- [系列总览](../../docs-site/agent-learning-guide/README.md)

## License

MIT
