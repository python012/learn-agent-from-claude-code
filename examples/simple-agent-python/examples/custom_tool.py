"""自定义工具示例

演示如何创建和使用自定义工具。
"""

import asyncio
import os
import sys
import random

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pydantic import BaseModel, Field

from src.agent.agent import Agent, AgentConfig
from src.tools.base import Tool, ToolResult, ToolContext, build_tool
from src.tools import get_builtin_tools


# =============================================================================
# 定义自定义工具
# =============================================================================

class WeatherInput(BaseModel):
    """天气工具输入参数"""
    city: str = Field(description="城市名称")


async def get_weather(input: WeatherInput, context: ToolContext) -> ToolResult:
    """获取天气信息（模拟）

    Args:
        input: 天气输入参数
        context: 工具执行上下文

    Returns:
        工具执行结果
    """
    # 模拟天气数据
    weather_options = ["sunny", "cloudy", "rainy", "windy", "snowy"]
    weather = random.choice(weather_options)
    temperature = random.randint(10, 35)

    return ToolResult(
        content=f"The weather in {input.city} is {weather}, temperature: {temperature}°C",
        is_error=False,
        metadata={"city": input.city, "weather": weather, "temperature": temperature},
    )


# 使用 build_tool 创建工具实例
WeatherTool = build_tool(
    name="GetWeather",
    description="Get current weather for a city",
    input_schema=WeatherInput,
    call_fn=get_weather,
    is_read_only=True,
)


# =============================================================================
# 主函数
# =============================================================================

async def main() -> None:
    """主函数"""
    # 检查环境变量
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set")
        return

    # 创建 Agent
    config = AgentConfig(
        cwd=os.getcwd(),
        api_key=api_key,
        model="gpt-4o",
        max_tokens=4096,
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)

    # 注册内置工具和自定义工具
    agent.register_tools(get_builtin_tools() + [WeatherTool])

    # 添加用户消息
    agent.add_user_message("北京今天的天气怎么样？")

    # 运行 Agent
    print("Running agent...")
    result = await agent.run()

    # 输出结果
    print("\n" + "=" * 50)
    print("Messages:")
    for msg in result.messages:
        if msg.type == "user":
            print(f"[user] {msg.message.content}")
        elif msg.type == "assistant":
            if msg.message.content:
                print(f"[assistant] {msg.message.content}")
            elif msg.message.tool_calls:
                for tc in msg.message.tool_calls:
                    print(f"[assistant] Called tool: {tc.function.get('name', 'unknown')}")
        elif msg.type == "tool":
            print(f"[tool] {msg.message.content}")


if __name__ == "__main__":
    asyncio.run(main())