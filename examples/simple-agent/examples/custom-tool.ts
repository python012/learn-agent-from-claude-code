import { buildTool, ToolContext, ToolResult } from '../src/tools/Tool.js'
import { z } from 'zod'
import { Agent } from '../src/agent/Agent.js'
import { builtInTools } from '../src/tools/index.js'

const inputSchema = z.object({
  city: z.string().describe('City name'),
})

const WeatherTool = buildTool({
  name: 'GetWeather',
  description: 'Get current weather for a city',
  inputSchema,

  isConcurrencySafe: () => true,
  isReadOnly: () => true,

  async call(
    input: z.infer<typeof inputSchema>,
    context: ToolContext,
  ): Promise<ToolResult> {
    const { city } = input
    const weather = ['sunny', 'cloudy', 'rainy', 'windy'][
      Math.floor(Math.random() * 4)
    ]
    const temperature = Math.floor(Math.random() * 30) + 10

    return {
      content: `The weather in ${city} is ${weather}, temperature: ${temperature}°C`,
      isError: false,
      metadata: { city, weather, temperature },
    }
  },
})

async function main() {
  const agent = new Agent({
    cwd: process.cwd(),
    apiKey: process.env.OPENAI_API_KEY!,
    model: 'gpt-4o',
    maxTokens: 4096,
    permissionMode: 'bypassPermissions',
  })

  agent.registerTools([
    ...builtInTools,
    WeatherTool,
  ])

  agent.addUserMessage('北京今天的天气怎么样？')

  const result = await agent.run()
  console.log(JSON.stringify(result, null, 2))
}

main().catch(console.error)
