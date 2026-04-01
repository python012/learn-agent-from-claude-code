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

## 构建

```bash
npm run build
```

## 测试

```bash
npm test
```

## 学习资源

- [第 08 篇：实战构建自己的 Agent](../../docs/agent-learning-guide/08-实战构建自己的 Agent.md)
- [系列总览](../../docs/agent-learning-guide/README.md)

## License

MIT
