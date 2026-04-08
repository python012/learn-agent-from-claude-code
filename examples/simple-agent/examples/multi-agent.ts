/**
 * 多 Agent 协作示例
 *
 * 演示如何创建多个 Agent 并让它们协作完成复杂任务。
 *
 * 场景：一个 Agent 负责规划，一个 Agent 负责编码，一个 Agent 负责审查代码。
 * 每个 Agent 通过第一个消息中的角色设定来区分职责。
 */

import { Agent } from '../src/agent/Agent.js'
import { AgentConfig, AgentResult } from '../src/agent/types.js'
import { builtInTools } from '../src/tools/index.js'

interface Message {
  type: 'user' | 'assistant' | 'tool' | 'system'
  message: {
    content?: string
    tool_calls?: any[]
  }
}

// 角色设定模板
const ROLE_PROMPTS: Record<string, string> = {
  '规划师': `你是一位经验丰富的技术规划师。你的任务是：
1. 分析用户需求
2. 设计项目结构和技术方案
3. 列出需要创建的文件清单

请用简洁的格式输出，便于后续 Agent 执行。`,

  '程序员': `你是一位高效的程序员。你的任务是：
1. 根据规划设计创建代码文件
2. 编写高质量、可运行的代码
3. 添加必要的注释和文档

请专注于实现功能，代码要简洁清晰。`,

  '审查员': `你是一位严格的代码审查员。你的任务是：
1. 检查代码质量和潜在问题
2. 提出改进建议
3. 确保代码符合最佳实践

请给出具体的修改意见，如果有严重问题要指出来。`,
}

class MultiAgentCoordinator {
  private agents: Map<string, Agent> = new Map()
  private results: Map<string, AgentResult> = new Map()
  private apiKey: string
  private model: string

  constructor(apiKey: string, model: string = 'gpt-4o') {
    this.apiKey = apiKey
    this.model = model
  }

  createAgent(name: string): Agent {
    /** 创建一个具有特定角色的 Agent */
    const rolePrompt = ROLE_PROMPTS[name]
    if (!rolePrompt) {
      throw new Error(`未知角色：${name}。可用角色：${Object.keys(ROLE_PROMPTS).join(', ')}`)
    }

    const config: AgentConfig = {
      cwd: process.cwd(),
      apiKey: this.apiKey,
      model: this.model,
      maxTokens: 4096,
      permissionMode: 'bypassPermissions',
    }

    const agent = new Agent(config)
    agent.registerTools(builtInTools)
    this.agents.set(name, agent)

    // 首先发送角色设定消息
    agent.addUserMessage(`从现在开始，请你扮演以下角色：\n\n${rolePrompt}`)

    console.log(`[协调器] 创建了 Agent: ${name}`)
    return agent
  }

  async runAgent(name: string, task: string): Promise<string> {
    /** 运行指定的 Agent */
    const agent = this.agents.get(name)
    if (!agent) {
      throw new Error(`Agent '${name}' not found`)
    }

    agent.addUserMessage(task)

    console.log(`\n[协调器] 正在运行 ${name}: ${task.slice(0, 50)}...`)
    const result = await agent.run()
    this.results.set(name, result)

    // 获取最后一条助手消息
    const lastAssistantMsg = [...result.messages].reverse().find(
      msg => msg.type === 'assistant' && msg.message.content
    )

    return lastAssistantMsg?.message.content || 'No response'
  }

  getContext(agentNames: string[], maxLength: number = 1000): string {
    /** 获取多个 Agent 的执行上下文 */
    const contextParts: string[] = []

    for (const name of agentNames) {
      const result = this.results.get(name)
      if (result) {
        let content = ''
        for (const msg of [...result.messages].reverse()) {
          if (msg.type === 'assistant' && msg.message.content) {
            content = msg.message.content
            break
          }
        }

        if (content) {
          contextParts.push(`=== ${name} 的执行结果 ===\n${content.slice(0, maxLength)}`)
        }
      }
    }

    return contextParts.join('\n\n')
  }

  getResult(name: string): AgentResult | undefined {
    return this.results.get(name)
  }
}

async function main() {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) {
    console.error('错误：请设置 OPENAI_API_KEY 环境变量')
    console.error('export OPENAI_API_KEY=your-api-key-here')
    return
  }

  console.log('='.repeat(60))
  console.log('多 Agent 协作示例 - 代码项目生成')
  console.log('='.repeat(60))

  // 创建协调器
  const coordinator = new MultiAgentCoordinator(apiKey)

  // 创建三个不同角色的 Agent
  const planner = coordinator.createAgent('规划师')
  const coder = coordinator.createAgent('程序员')
  const reviewer = coordinator.createAgent('审查员')

  // 用户任务
  const userTask = '创建一个 TypeScript 命令行工具，用于管理 Git 别名'

  console.log(`\n用户任务：${userTask}`)
  console.log('\n' + '='.repeat(60))

  // 第 1 步：规划师设计
  console.log('\n[第 1 步] 规划师进行设计...')
  const plannerResult = await coordinator.runAgent(
    '规划师',
    `请为以下任务设计项目结构和实现方案：\n${userTask}`
  )
  console.log(`规划结果:\n${plannerResult}`)

  // 第 2 步：程序员编码（使用规划结果作为上下文）
  console.log('\n' + '='.repeat(60))
  console.log('[第 2 步] 程序员开始编码...')
  const coderResult = await coordinator.runAgent(
    '程序员',
    `请根据以下规划实现代码：\n\n${plannerResult}\n\n请创建所有必要的文件。`
  )
  console.log(`代码实现:\n${coderResult}`)

  // 第 3 步：审查员审查（使用规划和编码结果作为上下文）
  console.log('\n' + '='.repeat(60))
  console.log('[第 3 步] 审查员审查代码...')
  const context = coordinator.getContext(['规划师', '程序员'])
  const reviewerResult = await coordinator.runAgent(
    '审查员',
    `请审查以下项目的代码质量：\n\n${context}\n\n请指出问题和改进建议。`
  )
  console.log(`审查结果:\n${reviewerResult}`)

  // 总结
  console.log('\n' + '='.repeat(60))
  console.log('多 Agent 协作完成!')
  console.log('='.repeat(60))

  const plannerTokens = coordinator.getResult('规划师')?.tokenUsage
  const coderTokens = coordinator.getResult('程序员')?.tokenUsage
  const reviewerTokens = coordinator.getResult('审查员')?.tokenUsage

  console.log(`规划师 token 数：${plannerTokens ? plannerTokens.inputTokens + plannerTokens.outputTokens : 'N/A'}`)
  console.log(`程序员 token 数：${coderTokens ? coderTokens.inputTokens + coderTokens.outputTokens : 'N/A'}`)
  console.log(`审查员 token 数：${reviewerTokens ? reviewerTokens.inputTokens + reviewerTokens.outputTokens : 'N/A'}`)
}

main().catch(console.error)
