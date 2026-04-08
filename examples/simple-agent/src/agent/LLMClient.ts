import OpenAI from 'openai'
import { Message, AssistantMessageParam, UserMessageParam, ToolMessageParam, ToolUseContent } from './types.js'
import { Tool } from '../tools/Tool.js'
import { z } from 'zod'

export type OpenAITool = {
  type: 'function'
  function: {
    name: string
    description: string
    parameters: Record<string, unknown>
  }
}

export type LLMResponse = {
  content: string | null
  toolCalls: ToolUseContent[]
  usage: {
    inputTokens: number
    outputTokens: number
    totalTokens: number
  }
}

export type LLMClientConfig = {
  apiKey: string
  model: string
  maxTokens: number
  temperature?: number
  signal?: AbortSignal
  timeoutMs?: number
}

export class LLMClient {
  private client: OpenAI
  private config: LLMClientConfig
  private signal: AbortSignal | undefined
  private timeoutMs: number | undefined

  constructor(config: LLMClientConfig) {
    // 验证配置
    if (!config.apiKey) {
      throw new Error('API key is required for LLMClient')
    }
    if (!config.model) {
      throw new Error('Model is required for LLMClient')
    }
    if (config.maxTokens <= 0) {
      throw new Error('maxTokens must be positive')
    }

    this.config = config
    this.signal = config.signal
    this.timeoutMs = config.timeoutMs
    this.client = new OpenAI({
      apiKey: config.apiKey,
    })
  }

  private convertTools(tools: Tool[]): OpenAITool[] {
    return tools.map(tool => {
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

  private zodSchemaToJsonSchema(schema: any): Record<string, unknown> {
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

    return { type: 'string' }
  }

  private convertMessages(messages: Message[]): (UserMessageParam | AssistantMessageParam | ToolMessageParam)[] {
    const openaiMessages: (UserMessageParam | AssistantMessageParam | ToolMessageParam)[] = []

    for (const msg of messages) {
      if (msg.type === 'user') {
        openaiMessages.push(msg.message)
      } else if (msg.type === 'assistant' && msg.message.tool_calls?.length) {
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

  async chat(
    messages: Message[],
    tools: Tool[] = [],
  ): Promise<LLMResponse> {
    // 检查是否已取消
    if (this.signal?.aborted) {
      const error = new Error('Request cancelled')
      error.name = 'AbortError'
      throw error
    }

    const openaiMessages = this.convertMessages(messages) as any
    const openaiTools = this.convertTools(tools)

    // 准备请求选项
    const requestOptions: any = {
      model: this.config.model,
      messages: openaiMessages,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature ?? 0.7,
      tools: openaiTools.length > 0 ? openaiTools : undefined,
      tool_choice: openaiTools.length > 0 ? 'auto' : undefined,
    }

    // 添加超时和AbortSignal
    if (this.timeoutMs) {
      requestOptions.timeout = this.timeoutMs
    }
    if (this.signal) {
      requestOptions.signal = this.signal
    }

    const response = await this.client.chat.completions.create(requestOptions)

    const choice = response.choices[0]
    if (!choice) {
      throw new Error('No response from OpenAI')
    }

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
