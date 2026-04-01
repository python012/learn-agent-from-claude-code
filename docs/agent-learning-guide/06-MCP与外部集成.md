# 第 6 篇：MCP 与外部集成

## 学习目标

- 理解 Model Context Protocol (MCP) 的设计原理
- 学习如何配置和连接 MCP 服务器
- 掌握 MCP 工具与内置工具的集成方式
- 了解 OAuth 认证和资源管理

---

## 6.1 MCP 概述

### 什么是 MCP？

Model Context Protocol (MCP) 是一个开放协议，用于连接 AI 模型与外部数据源和工具。它允许：

1. **工具发现** — 自动发现服务器提供的工具
2. **资源访问** — 访问外部数据源（文件、数据库、API）
3. **标准化接口** — 统一的 JSON-RPC 2.0 接口

### MCP 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code (Host)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ MCP Client  │  │ MCP Client  │  │ MCP Client          │  │
│  │ (stdio)     │  │ (SSE)       │  │ (WebSocket)         │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  MCP Server     │ │  MCP Server     │ │  MCP Server     │
│  (文件系统)      │ │  (GitHub)       │ │  (自定义)       │
│  stdio 传输      │ │  SSE 传输        │ │  WebSocket 传输  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 6.2 MCP 服务器配置

### 配置文件位置

```typescript
// MCP 配置文件：~/.claude/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "custom-api": {
      "url": "https://api.example.com/mcp",
      "type": "sse"
    }
  }
}
```

### 配置类型定义

```typescript
// 来自 src/services/mcp/types.ts

// 配置作用域
export type ConfigScope =
  | 'local'       // 本地配置
  | 'user'        // 用户配置
  | 'project'     // 项目配置
  | 'dynamic'     // 动态配置（Agent 定义）
  | 'enterprise'  // 企业配置
  | 'claudeai'    // Claude.ai 代理
  | 'managed'     // 托管配置

// 传输类型
export type Transport =
  | 'stdio'   // 标准输入输出
  | 'sse'     // Server-Sent Events
  | 'http'    // HTTP 流式
  | 'ws'      // WebSocket
  | 'sdk'     // SDK 内置

// stdio 服务器配置
export type McpStdioServerConfig = {
  type: 'stdio'
  command: string           // 启动命令
  args: string[]            // 参数
  env?: Record<string, string>
}

// SSE 服务器配置
export type McpSSEServerConfig = {
  type: 'sse'
  url: string
  headers?: Record<string, string>
  oauth?: {
    clientId?: string
    callbackPort?: number
    authServerMetadataUrl?: string
  }
}

// WebSocket 服务器配置
export type McpWebSocketServerConfig = {
  type: 'ws'
  url: string
  headers?: Record<string, string>
}
```

---

## 6.3 MCP 客户端连接

### 连接流程

```typescript
// 来自 src/services/mcp/client.ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js'

/**
 * 连接到 MCP 服务器
 */
export async function connectToServer(
  serverName: string,
  config: McpServerConfig,
): Promise<MCPServerConnection> {
  try {
    // 1. 创建传输层
    let transport: Transport
    switch (config.type) {
      case 'stdio':
        transport = new StdioClientTransport({
          command: config.command,
          args: config.args,
          env: { ...subprocessEnv(), ...config.env },
        })
        break

      case 'sse':
        transport = new SSEClientTransport({
          url: config.url,
          headers: config.headers,
        })
        break

      case 'ws':
        transport = new WebSocketTransport({
          url: config.url,
          headers: config.headers,
        })
        break

      default:
        throw new Error(`Unsupported transport type: ${config.type}`)
    }

    // 2. 创建 MCP 客户端
    const client = new Client({
      name: 'claude-code',
      version: VERSION,
    })

    // 3. 连接传输层
    await client.connect(transport)

    // 4. 获取服务器能力
    const capabilities = client.getServerCapabilities()

    return {
      name: serverName,
      type: 'connected',
      client,
      transport,
      capabilities,
      config,
    }
  } catch (error) {
    return {
      name: serverName,
      type: 'error',
      error: errorMessage(error),
      config,
    }
  }
}
```

### 获取工具列表

```typescript
// 来自 src/services/mcp/client.ts
/**
 * 从 MCP 客户端获取工具
 */
export async function fetchToolsForClient(
  client: MCPServerConnection,
): Promise<Tool[]> {
  if (client.type !== 'connected') {
    return []
  }

  try {
    // 调用 MCP list_tools 方法
    const result = await client.client.request(
      { method: 'tools/list' },
      ListToolsResultSchema,
    )

    // 转换为内部 Tool 类型
    return result.tools.map(tool =>
      wrapAsMcpTool(tool, client.name, client.client),
    )
  } catch (error) {
    logMCPError(error, `Fetching tools from ${client.name}`)
    return []
  }
}

/**
 * 将 MCP 工具包装为内部 Tool 类型
 */
function wrapAsMcpTool(
  mcpTool: MCPTool,
  serverName: string,
  client: Client,
): Tool {
  return buildTool({
    name: `mcp__${serverName}__${mcpTool.name}`,
    mcpInfo: { serverName, toolName: mcpTool.name },
    description: () => Promise.resolve(mcpTool.description),
    inputJSONSchema: mcpTool.inputSchema,

    async call(input, context) {
      try {
        // 调用 MCP tool_call 方法
        const result = await client.request(
          {
            method: 'tools/call',
            params: {
              name: mcpTool.name,
              arguments: input,
            },
          },
          CallToolResultSchema,
        )

        // 处理结果
        return {
          data: result.content,
          mcpMeta: result._meta,
        }
      } catch (error) {
        if (error.code === 401) {
          throw new McpAuthError(serverName, 'Authentication required')
        }
        throw error
      }
    },

    // MCP 工具默认不是并发安全的
    isConcurrencySafe: () => false,

    // MCP 工具默认为只读（除非明确标注）
    isReadOnly: () => !mcpTool.annotations?.readOnlyHint === false,
  })
}
```

---

## 6.4 MCP 工具集成

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
  // 1. 获取内置工具
  const builtInTools = getTools(permissionContext)

  // 2. 过滤 MCP 工具（应用拒绝规则）
  const allowedMcpTools = filterToolsByDenyRules(mcpTools, permissionContext)

  // 3. 合并并去重（内置工具优先）
  const byName = (a: Tool, b: Tool) => a.name.localeCompare(b.name)
  return uniqBy(
    [...builtInTools].sort(byName).concat(allowedMcpTools.sort(byName)),
    'name',
  )
}
```

### MCP 工具命名

```typescript
// 来自 src/services/mcp/mcpStringUtils.ts
/**
 * 构建 MCP 工具显示名称
 * 格式：mcp__{serverName}__{toolName}
 */
export function buildMcpToolName(
  serverName: string,
  toolName: string,
): string {
  return `mcp__${serverName}__${toolName}`
}

/**
 * 从 MCP 工具名称解析服务器名和工具名
 */
export function mcpInfoFromString(
  name: string,
): { serverName: string; toolName: string } | null {
  if (!name.startsWith('mcp__')) {
    return null
  }

  const parts = name.split('__')
  if (parts.length < 3) {
    return null
  }

  return {
    serverName: parts[1],
    toolName: parts.slice(2).join('__'),
  }
}

/**
 * 获取用于权限检查的工具名称
 */
export function getToolNameForPermissionCheck(
  tool: Pick<Tool, 'name' | 'mcpInfo'>,
): string {
  // 对于 MCP 工具，使用完整名称进行匹配
  if (tool.mcpInfo) {
    return tool.name
  }
  return tool.name
}
```

---

## 6.5 OAuth 认证

### OAuth 流程

```typescript
// 来自 src/services/mcp/auth.ts
import { OAuthClientProvider } from '@modelcontextprotocol/sdk/client/auth.js'

/**
 * Claude AI OAuth 提供者
 */
export class ClaudeAuthProvider implements OAuthClientProvider {
  constructor(
    private serverName: string,
    private authServerMetadataUrl?: string,
  ) {}

  // 保存客户端信息
  async saveClientInfo(clientInfo: OAuthClientInfo): Promise<void> {
    const tokens = await getClaudeAIOAuthTokens()
    tokens[this.serverName] = clientInfo
    await saveOAuthTokens(tokens)
  }

  // 获取保存的令牌
  async tokens(): Promise<OAuthTokens | null> {
    const tokens = await getClaudeAIOAuthTokens()
    return tokens[this.serverName] || null
  }

  // 重定向到授权页面
  async redirectToAuthorization(authUrl: URL): Promise<void> {
    // 打开浏览器进行授权
    await openBrowser(authUrl.toString())
  }

  // 处理授权回调
  async redirectUri(): Promise<string> {
    return 'http://localhost:7777/callback'
  }
}

/**
 * 检查并刷新 OAuth 令牌
 */
export async function checkAndRefreshOAuthTokenIfNeeded(
  serverName: string,
  client: Client,
): Promise<boolean> {
  const provider = new ClaudeAuthProvider(serverName)
  const tokens = await provider.tokens()

  if (!tokens) {
    return false  // 没有令牌，需要授权
  }

  // 检查令牌是否过期
  if (isTokenExpired(tokens)) {
    try {
      // 刷新令牌
      const newTokens = await refreshOAuthToken(tokens.refresh_token)
      await provider.saveClientInfo(newTokens)
      return true
    } catch (error) {
      logError(`Failed to refresh OAuth token: ${error.message}`)
      return false
    }
  }

  return true
}
```

### 处理 401 错误

```typescript
// 来自 src/utils/auth.ts
/**
 * 处理 OAuth 401 错误
 */
export async function handleOAuth401Error(
  serverName: string,
  error: Error,
): Promise<boolean> {
  if (error instanceof UnauthorizedError) {
    logForDebugging(`MCP server ${serverName} returned 401, attempting to re-authenticate`)

    // 清除缓存的令牌
    await clearOAuthTokenCache(serverName)

    // 触发重新认证
    const authTool = createMcpAuthTool(serverName)
    // 认证流程会打开浏览器...

    return true
  }

  return false
}
```

---

## 6.6 资源管理

### 资源类型

```typescript
// 来自 src/services/mcp/types.ts
export type ServerResource = {
  uri: string
  name: string
  description?: string
  mimeType?: string
}

export type MCPServerConnection =
  | {
      name: string
      type: 'connected'
      client: Client
      transport: Transport
      capabilities: ServerCapabilities
      tools: Tool[]
      resources: ServerResource[]
      config: McpServerConfig
    }
  | {
      name: string
      type: 'connecting'
      config: McpServerConfig
    }
  | {
      name: string
      type: 'disconnected'
      config: McpServerConfig
    }
  | {
      name: string
      type: 'error'
      error: string
      config: McpServerConfig
    }
  | {
      name: string
      type: 'needs-auth'
      authUrl?: string
      config: McpServerConfig
    }
```

### 资源获取

```typescript
// 来自 src/services/mcp/client.ts
/**
 * 获取 MCP 服务器的资源列表
 */
export async function fetchResourcesForClient(
  client: MCPServerConnection,
): Promise<ServerResource[]> {
  if (client.type !== 'connected') {
    return []
  }

  try {
    const result = await client.client.request(
      { method: 'resources/list' },
      ListResourcesResultSchema,
    )

    return result.resources
  } catch (error) {
    logMCPError(error, `Fetching resources from ${client.name}`)
    return []
  }
}

/**
 * 读取 MCP 资源内容
 */
export async function readMcpResource(
  client: Client,
  uri: string,
): Promise<string> {
  const result = await client.request(
    {
      method: 'resources/read',
      params: { uri },
    },
    ReadResourceResultSchema,
  )

  // 合并所有内容块
  return result.contents.map(c => c.text).join('\n')
}
```

### 资源工具

```typescript
// 来自 src/tools/ListMcpResourcesTool/ListMcpResourcesTool.ts
export const ListMcpResourcesTool = buildTool({
  name: 'ListMcpResourcesTool',
  description: () => 'List available resources from connected MCP servers',

  async call(input, context) {
    const appState = context.getAppState()
    const resources: Array<{ server: string; uri: string; name: string }> = []

    for (const client of appState.mcp.clients) {
      if (client.type === 'connected') {
        for (const resource of client.resources) {
          resources.push({
            server: client.name,
            uri: resource.uri,
            name: resource.name,
          })
        }
      }
    }

    return {
      data: {
        resources,
        total: resources.length,
      },
    }
  },
})

// 来自 src/tools/ReadMcpResourceTool/ReadMcpResourceTool.ts
export const ReadMcpResourceTool = buildTool({
  name: 'ReadMcpResourceTool',
  description: () => 'Read content from an MCP resource URI',

  get inputSchema() {
    return z.object({
      uri: z.string().describe('The resource URI to read'),
    })
  },

  async call({ uri }, context) {
    const appState = context.getAppState()

    // 找到包含该资源的客户端
    for (const client of appState.mcp.clients) {
      if (client.type === 'connected') {
        const resource = client.resources.find(r => r.uri === uri)
        if (resource) {
          const content = await readMcpResource(client.client, uri)
          return { data: { uri, content } }
        }
      }
    }

    throw new Error(`Resource not found: ${uri}`)
  },
})
```

---

## 6.7 Agent 特定的 MCP 服务器

### Agent 定义中的 MCP 配置

```typescript
// 来自 src/tools/AgentTool/runAgent.ts
/**
 * 初始化 Agent 特定的 MCP 服务器
 * Agent 可以定义自己的 MCP 服务器，这些服务器会添加到父级 MCP 客户端中
 */
async function initializeAgentMcpServers(
  agentDefinition: AgentDefinition,
  parentClients: MCPServerConnection[],
): Promise<{
  clients: MCPServerConnection[]
  tools: Tools
  cleanup: () => Promise<void>
}> {
  // 如果 Agent 没有定义 MCP 服务器，返回父级客户端
  if (!agentDefinition.mcpServers?.length) {
    return {
      clients: parentClients,
      tools: [],
      cleanup: async () => {},
    }
  }

  const agentClients: MCPServerConnection[] = []
  const newlyCreatedClients: MCPServerConnection[] = []
  const agentTools: Tool[] = []

  for (const spec of agentDefinition.mcpServers) {
    let config: ScopedMcpServerConfig | null = null
    let name: string
    let isNewlyCreated = false

    if (typeof spec === 'string') {
      // 引用已有的 MCP 服务器
      name = spec
      config = getMcpConfigByName(spec)
    } else {
      // 内联定义新服务器
      const entries = Object.entries(spec)
      const [serverName, serverConfig] = entries[0]!
      name = serverName
      config = {
        ...serverConfig,
        scope: 'dynamic' as const,
      }
      isNewlyCreated = true
    }

    // 连接到服务器
    const client = await connectToServer(name, config)
    agentClients.push(client)
    if (isNewlyCreated) {
      newlyCreatedClients.push(client)
    }

    // 获取工具
    if (client.type === 'connected') {
      const tools = await fetchToolsForClient(client)
      agentTools.push(...tools)
    }
  }

  // 清理函数：只清理新创建的客户端
  const cleanup = async () => {
    for (const client of newlyCreatedClients) {
      if (client.type === 'connected') {
        await client.client.close()
      }
    }
  }

  return {
    clients: [...parentClients, ...agentClients],
    tools: agentTools,
    cleanup,
  }
}
```

---

## 6.8 错误处理

### MCP 错误类型

```typescript
// 来自 src/services/mcp/client.ts
/**
 * MCP 认证错误
 */
export class McpAuthError extends Error {
  serverName: string
  constructor(serverName: string, message: string) {
    super(message)
    this.name = 'McpAuthError'
    this.serverName = serverName
  }
}

/**
 * MCP 会话过期错误
 */
class McpSessionExpiredError extends Error {
  constructor(serverName: string) {
    super(`MCP server "${serverName}" session expired`)
    this.name = 'McpSessionExpiredError'
  }
}

/**
 * MCP 工具调用错误
 */
export class McpToolCallError extends Error {
  mcpMeta?: { _meta?: Record<string, unknown> }

  constructor(
    message: string,
    telemetryMessage: string,
    mcpMeta?: { _meta?: Record<string, unknown> },
  ) {
    super(message, telemetryMessage)
    this.name = 'McpToolCallError'
    this.mcpMeta = mcpMeta
  }
}

/**
 * 检测 MCP 会话过期错误
 * MCP 规范：服务器在会话 ID 无效时返回 404 + JSON-RPC code -32001
 */
export function isMcpSessionExpiredError(error: Error): boolean {
  const httpStatus = 'code' in error ? (error as any).code : undefined
  if (httpStatus !== 404) {
    return false
  }

  // SDK 将响应体嵌入错误消息
  // MCP 服务器返回：{"error":{"code":-32001,"message":"Session not found"},...}
  return error.message.includes('-32001') || error.message.includes('Session not found')
}
```

### 重试逻辑

```typescript
// 来自 src/services/mcp/client.ts
/**
 * 带重试的 MCP 调用
 */
export async function callMcpToolWithRetry(
  client: Client,
  toolName: string,
  args: Record<string, unknown>,
  maxRetries: number = 3,
): Promise<any> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await client.request(
        {
          method: 'tools/call',
          params: { name: toolName, arguments: args },
        },
        CallToolResultSchema,
      )
    } catch (error) {
      // 会话过期：清除缓存并重新连接
      if (isMcpSessionExpiredError(error)) {
        await clearMcpClientCache()
        continue
      }

      // 认证错误：尝试刷新令牌
      if (error instanceof UnauthorizedError) {
        const refreshed = await refreshOAuth()
        if (refreshed) continue
      }

      // 其他错误：达到最大重试次数则抛出
      if (attempt === maxRetries) {
        throw new McpToolCallError(
          `Tool ${toolName} failed after ${maxRetries} attempts`,
          error.message,
        )
      }

      // 等待后重试
      await sleep(1000 * attempt)
    }
  }
}
```

---

## 6.9 实战：编写自定义 MCP 服务器

### 使用 Python 编写 MCP 服务器

```python
# 示例：简单的天气 MCP 服务器
# 使用 mcp SDK: pip install mcp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("weather-server")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_weather",
            description="获取指定城市的天气",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_weather":
        city = arguments["city"]
        # 调用天气 API
        weather = await fetch_weather(city)
        return [TextContent(type="text", text=f"{city}的天气：{weather}")]
    raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run(stdio_server()))
```

### 在 Claude Code 中配置

```json
// ~/.claude/mcp.json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["/path/to/weather_server.py"]
    }
  }
}
```

---

## 6.10 关键代码位置索引

| 功能 | 文件路径 | 关键函数/类型 |
|------|----------|---------------|
| MCP 类型 | `src/services/mcp/types.ts` | `MCPServerConnection`, `McpServerConfig` |
| 客户端连接 | `src/services/mcp/client.ts` | `connectToServer`, `fetchToolsForClient` |
| MCP 认证 | `src/services/mcp/auth.ts` | `ClaudeAuthProvider` |
| MCP 工具 | `src/tools/MCPTool/MCPTool.ts` | `wrapAsMcpTool` |
| 资源列表 | `src/tools/ListMcpResourcesTool/` | `ListMcpResourcesTool` |
| 资源读取 | `src/tools/ReadMcpResourceTool/` | `ReadMcpResourceTool` |
| MCP 配置 | `src/services/mcp/config.ts` | `getAllMcpConfigs`, `getMcpConfigByName` |
| MCP 认证工具 | `src/tools/McpAuthTool/McpAuthTool.ts` | `createMcpAuthTool` |

---

## 课后练习

1. **阅读代码**：
   - 打开 `src/services/mcp/client.ts`，查看 `connectToServer` 函数
   - 打开 `src/tools/MCPTool/MCPTool.ts`，查看 MCP 工具包装逻辑
   - 打开 `src/services/mcp/types.ts`，了解 MCP 配置类型

2. **实践配置**：
   - 配置一个官方 MCP 服务器（如 filesystem）
   - 尝试编写一个简单的 Python MCP 服务器

3. **思考问题**：
   - MCP 协议相比直接调用 API 有什么优势？
   - 如何处理 MCP 服务器的认证和令牌刷新？
   - Agent 特定的 MCP 服务器如何实现隔离？

---

**下一步**：[第 7 篇 — 多 Agent 协作系统](./07-多 Agent 协作系统.md)
