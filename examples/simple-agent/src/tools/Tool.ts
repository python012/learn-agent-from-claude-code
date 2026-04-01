import { z } from 'zod'

export type ToolContext = {
  cwd: string
  sessionId: string
  signal?: AbortSignal
}

export type ToolResult = {
  content: string
  isError?: boolean
  metadata?: Record<string, unknown>
}

export interface Tool {
  readonly name: string
  readonly description: string
  readonly inputSchema: z.ZodType
  readonly isConcurrencySafe: () => boolean
  readonly isReadOnly: () => boolean
  call(
    input: unknown,
    context: ToolContext,
  ): Promise<ToolResult>
  checkPermissions?(
    input: unknown,
    context: ToolContext,
  ): Promise<PermissionCheckResult>
}

export type PermissionCheckResult = {
  allowed: boolean
  reason?: string
  requiresUserConfirmation?: boolean
}

export function buildTool<T extends z.ZodType>(
  definition: {
    name: string
    description: string
    inputSchema: T
    isConcurrencySafe?: () => boolean
    isReadOnly?: () => boolean
    checkPermissions?: Tool['checkPermissions']
    call: (
      input: z.infer<T>,
      context: ToolContext,
    ) => Promise<ToolResult>
  },
): Tool {
  return {
    name: definition.name,
    description: definition.description,
    inputSchema: definition.inputSchema,
    isConcurrencySafe: definition.isConcurrencySafe ?? (() => false),
    isReadOnly: definition.isReadOnly ?? (() => false),
    checkPermissions: definition.checkPermissions,
    async call(input: unknown, context: ToolContext): Promise<ToolResult> {
      const parsedInput = definition.inputSchema.parse(input)
      return definition.call(parsedInput, context)
    },
  }
}
