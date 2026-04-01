import { buildTool, ToolContext, ToolResult } from './Tool.js'
import { z } from 'zod'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

const inputSchema = z.object({
  command: z.string().describe('The bash command to execute'),
  description: z.string().optional().describe('Why you want to run this command'),
})

export const BashTool = buildTool({
  name: 'Bash',
  description: 'Execute bash commands in the terminal',
  inputSchema,

  isConcurrencySafe: () => false,
  isReadOnly: () => false,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { command } = input

    const dangerousPatterns = [
      /rm\s+(-[rf]+\s+)?\//,
      /curl.*\|\s*(bash|sh)/,
      /wget.*\|\s*(bash|sh)/,
      /:\(\)\{/,
    ]

    for (const pattern of dangerousPatterns) {
      if (pattern.test(command)) {
        return {
          content: `Command blocked for security: ${command}`,
          isError: true,
          metadata: { blocked: true, reason: 'dangerous_command' },
        }
      }
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        cwd: context.cwd,
        timeout: 60000,
        maxBuffer: 10 * 1024 * 1024,
      })

      const result = stdout || stderr || '(no output)'

      return {
        content: result,
        isError: false,
        metadata: {
          exitCode: 0,
          commandLength: command.length,
        },
      }
    } catch (error) {
      const execError = error as Error & { code?: number; stdout?: string; stderr?: string }
      return {
        content: `Error executing command: ${execError.message}\n${execError.stderr || ''}`,
        isError: true,
        metadata: {
          exitCode: execError.code ?? 1,
          command,
        },
      }
    }
  },
})
