import { Tool } from '../tools/Tool.js'
import { ToolContext } from '../tools/Tool.js'
import { PermissionMode, PermissionRule, PermissionCheck } from './types.js'
import { permissionRuleValueFromString } from './types.js'

export class PermissionChecker {
  private mode: PermissionMode
  private allowRules: PermissionRule[]
  private denyRules: PermissionRule[]
  private askRules: PermissionRule[]

  constructor(options: {
    mode: PermissionMode
    allowRules?: string[]
    denyRules?: string[]
    askRules?: string[]
  }) {
    this.mode = options.mode
    this.allowRules = this.parseRules(options.allowRules ?? [])
    this.denyRules = this.parseRules(options.denyRules ?? [])
    this.askRules = this.parseRules(options.askRules ?? [])
  }

  private parseRules(rules: string[]): PermissionRule[] {
    return rules.map(ruleStr => {
      const { toolName, ruleContent } = permissionRuleValueFromString(ruleStr)
      return {
        type: 'allow',
        toolName,
        pattern: ruleContent,
      }
    })
  }

  async checkPermission(
    tool: Tool,
    input: unknown,
    context: ToolContext,
  ): Promise<PermissionCheck> {
    if (this.mode === 'bypassPermissions') {
      return {
        allowed: true,
        requiresConfirmation: false,
        reason: 'bypassPermissions mode',
        mode: this.mode,
      }
    }

    if (this.mode === 'dontAsk') {
      return {
        allowed: false,
        requiresConfirmation: false,
        reason: 'dontAsk mode',
        mode: this.mode,
      }
    }

    if (this.matchesRule(this.denyRules, tool.name, input)) {
      return {
        allowed: false,
        requiresConfirmation: false,
        reason: `Denied by rule: ${tool.name}`,
        mode: this.mode,
      }
    }

    if (this.matchesRule(this.allowRules, tool.name, input)) {
      return {
        allowed: true,
        requiresConfirmation: false,
        reason: `Allowed by rule: ${tool.name}`,
        mode: this.mode,
      }
    }

    if (this.mode === 'acceptEdits' && tool.isReadOnly()) {
      return {
        allowed: true,
        requiresConfirmation: false,
        reason: 'acceptEdits mode + read-only tool',
        mode: this.mode,
      }
    }

    if (this.mode === 'auto') {
      return {
        allowed: tool.isReadOnly(),
        requiresConfirmation: !tool.isReadOnly(),
        reason: 'auto mode classification',
        mode: this.mode,
      }
    }

    return {
      allowed: false,
      requiresConfirmation: true,
      reason: 'default: require user confirmation',
      mode: this.mode,
    }
  }

  private matchesRule(
    rules: PermissionRule[],
    toolName: string,
    input: unknown,
  ): boolean {
    for (const rule of rules) {
      if (rule.toolName !== toolName) {
        continue
      }

      if (!rule.pattern) {
        return true
      }

      const inputStr = typeof input === 'string' ? input : JSON.stringify(input)
      if (this.patternMatches(rule.pattern, inputStr)) {
        return true
      }
    }
    return false
  }

  private patternMatches(pattern: string, input: string): boolean {
    const regexPattern = pattern
      .replace(/[.+?^${}()|[\]\\]/g, '\\$&')
      .replace(/\*/g, '.*')
    const regex = new RegExp(`^${regexPattern}$`)
    return regex.test(input)
  }
}
