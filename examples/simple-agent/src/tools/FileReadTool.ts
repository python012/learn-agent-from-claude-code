import { buildTool, ToolContext, ToolResult } from './Tool.js'
import { z } from 'zod'
import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import { join } from 'path'

const inputSchema = z.object({
  path: z.string().describe('Absolute or relative path to the file'),
  description: z.string().optional().describe('Why you need to read this file'),
})

export const FileReadTool = buildTool({
  name: 'FileRead',
  description: 'Read content from a file',
  inputSchema,

  isConcurrencySafe: () => true,
  isReadOnly: () => true,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { path: inputPath } = input

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

    if (!existsSync(normalizedPath)) {
      return {
        content: `File not found: ${normalizedPath}`,
        isError: true,
        metadata: { notFound: true },
      }
    }

    try {
      const content = await readFile(normalizedPath, 'utf-8')

      const maxLines = 2000
      const lines = content.split('\n')
      const truncatedContent = lines.length > maxLines
        ? lines.slice(0, maxLines).join('\n') + `\n\n... (${lines.length - maxLines} more lines)`
        : content

      return {
        content: truncatedContent,
        isError: false,
        metadata: {
          totalLines: lines.length,
          fileSize: Buffer.byteLength(content, 'utf-8'),
          path: normalizedPath,
        },
      }
    } catch (error) {
      const readError = error as Error
      return {
        content: `Error reading file: ${readError.message}`,
        isError: true,
        metadata: { error: readError.message },
      }
    }
  },
})
