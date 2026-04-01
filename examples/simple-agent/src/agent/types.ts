import { z } from 'zod'

export type UUID = string

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

export type MessageContent = TextContent | ToolUseContent | ToolResultContent

export type UserMessageParam = {
  role: 'user'
  content: string | MessageContent[]
}

export type AssistantMessageParam = {
  role: 'assistant'
  content: string | null
  tool_calls?: ToolCall[]
}

export type ToolCall = {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

export type ToolMessageParam = {
  role: 'tool'
  tool_call_id: string
  content: string
}

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
