export type PermissionMode =
  | 'default'
  | 'plan'
  | 'acceptEdits'
  | 'bypassPermissions'
  | 'dontAsk'
  | 'auto'

export type RuleType = 'allow' | 'deny' | 'ask'

export type PermissionRule = {
  type: RuleType
  toolName: string
  pattern?: string
  description?: string
}

export type PermissionCheck = {
  allowed: boolean
  requiresConfirmation: boolean
  reason?: string
  mode: PermissionMode
}

export function permissionRuleValueFromString(
  value: string,
): { toolName: string; ruleContent?: string } {
  const match = value.match(/^(\w+)(?:\((.*)\))?$/)
  if (match) {
    return {
      toolName: match[1]!,
      ruleContent: match[2],
    }
  }
  return { toolName: value }
}
