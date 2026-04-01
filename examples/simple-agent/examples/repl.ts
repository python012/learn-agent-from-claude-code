import * as readline from 'readline'
import { Agent } from '../src/agent/Agent.js'
import { builtInTools } from '../src/tools/index.js'

async function main() {
  const agent = new Agent({
    cwd: process.cwd(),
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4o',
    maxTokens: 4096,
    permissionMode: 'acceptEdits',
  })

  agent.registerTools(builtInTools)

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  })

  console.log('SimpleAgent REPL - Type your message or "quit" to exit')
  console.log('='.repeat(50))

  const prompt = () => {
    rl.question('> ', async (input) => {
      if (input.toLowerCase() === 'quit' || input.toLowerCase() === 'exit') {
        rl.close()
        return
      }

      if (input.trim()) {
        agent.addUserMessage(input)

        try {
          const result = await agent.run()
          const lastMessage = result.messages[result.messages.length - 1]
          if (lastMessage?.type === 'assistant') {
            const content = lastMessage.message.content
            console.log(typeof content === 'string' ? content : JSON.stringify(content))
          }
        } catch (error) {
          console.error('Error:', error)
        }
      }

      prompt()
    })
  }

  prompt()
}

main().catch(console.error)
