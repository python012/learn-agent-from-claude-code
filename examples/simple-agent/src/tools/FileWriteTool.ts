import { buildTool, ToolContext, ToolResult } from './Tool.js'
import { z } from 'zod'
import { writeFile, mkdir } from 'fs/promises'
import { dirname, join } from 'path'
import { existsSync } from 'fs'

const inputSchema = z.object({
  path: z.string().describe('Absolute or relative path to the file'),
  content: z.string().describe('Content to write to the file'),
  description: z.string().optional().describe('Why you need to write this file'),
})

export const FileWriteTool = buildTool({
  name: 'FileWrite',
  description: 'Write content to a file (creates new file or overwrites existing)',
  inputSchema,

  isConcurrencySafe: () => false,
  isReadOnly: () => false,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { path: inputPath, content } = input

    const resolvedPath = inputPath.startsWith('/')
      ? inputPath
      : join(context.cwd, inputPath)

    const normalizedPath = join(context.cwd, resolvedPath)
    if (!normalizedPath.startsWith(context.cwd)) {
      return {
        content: `Access denied: Path ${inputPath} is outside working directory`,
        isError: true,
        metadata: { blocked: true, reason: 'path_traversal' },
      }
    }

    const sensitivePatterns = [
      /\.env$/,
      /package\.json$/,
      /tsconfig\.json$/,
      /\.git\/config$/,
    ]

    for (const pattern of sensitivePatterns) {
      if (pattern.test(normalizedPath)) {
        return {
          content: `Writing to ${normalizedPath} requires explicit permission`,
          isError: true,
          metadata: { blocked: true, reason: 'sensitive_file' },
        }
      }
    }

    try {
      const dir = dirname(normalizedPath)
      if (!existsSync(dir)) {
        await mkdir(dir, { recursive: true })
      }

      await writeFile(normalizedPath, content, 'utf-8')

      return {
        content: `Successfully wrote ${content.length} bytes to ${normalizedPath}`,
        isError: false,
        metadata: {
          bytesWritten: content.length,
          path: normalizedPath,
          created: !existsSync(normalizedPath),
        },
      }
    } catch (error) {
      const writeError = error as Error
      return {
        content: `Error writing file: ${writeError.message}`,
        isError: true,
        metadata: { error: writeError.message },
      }
    }
  },
})
