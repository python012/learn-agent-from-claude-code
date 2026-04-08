import { Agent } from '../src/agent/Agent.js'
import { builtInTools } from '../src/tools/index.js'

async function main() {
  const controller = new AbortController()

  const agent = new Agent({
    cwd: process.cwd(),
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4o',
    maxTokens: 4096,
    permissionMode: 'bypassPermissions',
    maxIterations: 20,            // 设置最大迭代次数
    timeoutMs: 30000,             // 设置超时时间（30秒）
    signal: controller.signal,    // 可选的 AbortSignal
  })

  agent.registerTools(builtInTools)

  agent.addUserMessage('创建一个简单的 TypeScript 项目，包含 package.json 和 tsconfig.json')

  const result = await agent.run()

  console.log('Token Usage:')
  console.log(`  Input:  ${result.tokenUsage.inputTokens}`)
  console.log(`  Output: ${result.tokenUsage.outputTokens}`)
  console.log('\nMessages:')
  for (const msg of result.messages) {
    if (msg.type !== 'system') {
      console.log(`[${msg.type}] ${JSON.stringify(msg.message).slice(0, 100)}...`)
    }
  }
}

main().catch(console.error)
