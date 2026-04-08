import { LLMClient } from './LLMClient.js'
import { Message, ToolUseContent, AssistantMessageParam, UserMessageParam, ToolMessageParam, UUID } from './types.js'
import { Tool, ToolContext } from '../tools/Tool.js'
import { PermissionChecker } from '../permissions/PermissionChecker.js'
import { PermissionMode } from '../permissions/types.js'
import { createStateStore, StateStore } from '../state/StateStore.js'
import { SessionStorage } from '../state/SessionStorage.js'
import { join } from 'path'

export type AgentConfig = {
  cwd: string
  apiKey: string
  model: string
  maxTokens: number
  temperature?: number
  permissionMode?: PermissionMode
  sessionDir?: string
  maxIterations?: number
  timeoutMs?: number
  signal?: AbortSignal
}

export type AgentResult = {
  messages: Message[]
  tokenUsage: {
    inputTokens: number
    outputTokens: number
  }
}

export class Agent {
  private llmClient: LLMClient
  private permissionChecker: PermissionChecker
  private state: StateStore
  private sessionStorage: SessionStorage | null
  private cwd: string
  private registeredTools: Map<string, Tool> = new Map()
  private maxIterations: number
  private timeoutMs: number | undefined
  private signal: AbortSignal | undefined

  constructor(config: AgentConfig) {
    this.cwd = config.cwd
    this.maxIterations = config.maxIterations ?? 50
    this.timeoutMs = config.timeoutMs
    this.signal = config.signal

    // 验证必要的配置
    if (!config.apiKey) {
      throw new Error('API key is required')
    }
    if (!config.model) {
      throw new Error('Model is required')
    }

    this.llmClient = new LLMClient({
      apiKey: config.apiKey,
      model: config.model,
      maxTokens: config.maxTokens,
      temperature: config.temperature,
      signal: config.signal,
      timeoutMs: config.timeoutMs,
    })
    this.permissionChecker = new PermissionChecker({
      mode: config.permissionMode ?? 'default',
    })
    this.state = createStateStore()
    this.sessionStorage = config.sessionDir
      ? new SessionStorage(config.sessionDir)
      : null
  }

  registerTools(tools: Tool[]): void {
    for (const tool of tools) {
      this.registeredTools.set(tool.name, tool)
    }
  }

  addUserMessage(content: string): void {
    this.state.setState(prev => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          uuid: crypto.randomUUID(),
          parentUuid: prev.messages.length > 0
            ? prev.messages[prev.messages.length - 1].uuid
            : null,
          timestamp: Date.now(),
          type: 'user',
          message: {
            role: 'user',
            content,
          },
        },
      ],
    }))
  }

  addAssistantMessage(content: string, toolCalls?: ToolUseContent[]): void {
    this.state.setState(prev => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          uuid: crypto.randomUUID(),
          parentUuid: prev.messages.length > 0
            ? prev.messages[prev.messages.length - 1].uuid
            : null,
          timestamp: Date.now(),
          type: 'assistant',
          message: {
            role: 'assistant',
            content: content || null,
            tool_calls: toolCalls?.map(tc => ({
              id: tc.id,
              type: 'function' as const,
              function: {
                name: tc.name,
                arguments: JSON.stringify(tc.input),
              },
            })),
          },
        },
      ],
    }))
  }

  addToolResultMessage(toolUseId: string, content: string, isError = false): void {
    this.state.setState(prev => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          uuid: crypto.randomUUID(),
          parentUuid: prev.messages.length > 0
            ? prev.messages[prev.messages.length - 1].uuid
            : null,
          timestamp: Date.now(),
          type: 'tool',
          message: {
            role: 'tool',
            tool_call_id: toolUseId,
            content,
          },
        },
      ],
    }))
  }

  async run(): Promise<AgentResult> {
    // 检查是否已取消
    if (this.signal?.aborted) {
      throw new Error('Agent execution cancelled before start')
    }

    this.state.setState(prev => ({ ...prev, isProcessing: true }))

    try {
      const toolList = Array.from(this.registeredTools.values())
      let iteration = 0

      while (iteration < this.maxIterations) {
        iteration++

        // 检查是否已取消
        if (this.signal?.aborted) {
          throw new Error('Agent execution cancelled')
        }

        const messages = this.state.getState().messages
        const response = await this.llmClient.chat(messages, toolList)

        this.state.setState(prev => ({
          ...prev,
          tokenUsage: {
            inputTokens: prev.tokenUsage.inputTokens + response.usage.inputTokens,
            outputTokens: prev.tokenUsage.outputTokens + response.usage.outputTokens,
          },
        }))

        if (response.content) {
          this.addAssistantMessage(response.content)
        }

        if (response.toolCalls.length > 0) {
          this.addAssistantMessage('', response.toolCalls)

          for (const toolCall of response.toolCalls) {
            // 检查是否已取消
            if (this.signal?.aborted) {
              throw new Error('Agent execution cancelled during tool execution')
            }

            const result = await this.executeToolCall(toolCall)
            this.addToolResultMessage(toolCall.id, result.content, result.isError)
          }

          continue
        }

        break
      }

      // 检查是否达到最大迭代次数
      if (iteration >= this.maxIterations) {
        throw new Error(`Max iterations (${this.maxIterations}) reached`)
      }

      await this.saveSession()

      const finalState = this.state.getState()
      return {
        messages: finalState.messages,
        tokenUsage: finalState.tokenUsage,
      }
    } catch (error) {
      // 将错误转换为更友好的消息
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Agent execution cancelled')
      }
      throw error
    } finally {
      this.state.setState(prev => ({ ...prev, isProcessing: false }))
    }
  }

  private async executeToolCall(toolCall: ToolUseContent): Promise<{ content: string; isError: boolean }> {
    const tool = this.registeredTools.get(toolCall.name)
    if (!tool) {
      return {
        content: `Tool not found: ${toolCall.name}`,
        isError: true,
      }
    }

    const toolContext: ToolContext = {
      cwd: this.cwd,
      sessionId: this.state.getState().sessionId,
      signal: this.signal,
    }

    // 权限检查
    const permissionCheck = await this.permissionChecker.checkPermission(
      tool,
      toolCall.input,
      toolContext,
    )

    if (!permissionCheck.allowed) {
      return {
        content: `Permission denied: ${permissionCheck.reason}`,
        isError: true,
      }
    }

    // 输入验证
    let parsedInput: unknown
    try {
      parsedInput = tool.inputSchema.parse(toolCall.input)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      return {
        content: `Invalid input for tool ${tool.name}: ${errorMessage}`,
        isError: true,
      }
    }

    // 执行工具（带超时）
    try {
      let resultPromise = tool.call(parsedInput, toolContext)

      if (this.timeoutMs) {
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error(`Tool execution timeout after ${this.timeoutMs}ms`)), this.timeoutMs)
        })
        resultPromise = Promise.race([resultPromise, timeoutPromise])
      }

      const result = await resultPromise
      return {
        content: result.content,
        isError: result.isError ?? false,
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return {
          content: 'Tool execution cancelled',
          isError: true,
        }
      }
      const errorMessage = error instanceof Error ? error.message : String(error)
      return {
        content: `Tool execution error for ${tool.name}: ${errorMessage}`,
        isError: true,
      }
    }
  }

  private async saveSession(): Promise<void> {
    if (!this.sessionStorage) return

    const state = this.state.getState()
    const messages = state.messages

    for (const message of messages) {
      await this.sessionStorage.appendMessage(state.sessionId, message)
    }

    const title = this.sessionStorage.extractTitle(messages) || 'Untitled Session'
    await this.sessionStorage.saveMetadata({
      sessionId: state.sessionId,
      title,
      createdAt: messages[0]?.timestamp ?? Date.now(),
      updatedAt: messages[messages.length - 1]?.timestamp ?? Date.now(),
      projectDir: this.cwd,
    })
  }

  getState() {
    return this.state.getState()
  }

  subscribeState(listener: () => void) {
    return this.state.subscribe(listener)
  }
}
