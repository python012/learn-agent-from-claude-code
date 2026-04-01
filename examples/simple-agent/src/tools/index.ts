import { Tool } from './Tool.js'
import { BashTool } from './BashTool.js'
import { FileReadTool } from './FileReadTool.js'
import { FileWriteTool } from './FileWriteTool.js'

export const builtInTools: Tool[] = [
  BashTool,
  FileReadTool,
  FileWriteTool,
]

export function assembleToolPool(
  tools: Tool[],
  options?: {
    readOnlyOnly?: boolean
    excludeTools?: string[]
  },
): Tool[] {
  let filtered = tools

  if (options?.readOnlyOnly) {
    filtered = filtered.filter(tool => tool.isReadOnly())
  }

  if (options?.excludeTools) {
    const excludeSet = new Set(options.excludeTools)
    filtered = filtered.filter(tool => !excludeSet.has(tool.name))
  }

  return filtered
}

export function getDefaultToolPool(): Tool[] {
  return assembleToolPool(builtInTools)
}
