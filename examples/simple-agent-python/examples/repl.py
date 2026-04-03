"""交互式 REPL 示例

演示如何创建交互式命令行界面。
"""

import asyncio
import os
import sys

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from src.agent.agent import Agent, AgentConfig
from src.tools import get_builtin_tools


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
        permission_mode="accept_edits",  # 自动接受只读操作
    )
    agent = Agent(config)
    agent.register_tools(get_builtin_tools())

    print("SimpleAgent REPL - Type your message or 'quit' to exit")
    print("=" * 50)

    async def prompt() -> None:
        """提示用户输入并处理"""
        while True:
            try:
                user_input = input("> ")
            except EOFError:
                break

            if user_input.lower() in ("quit", "exit"):
                break

            if not user_input.strip():
                continue

            # 添加用户消息
            agent.add_user_message(user_input)

            try:
                # 运行 Agent
                result = await agent.run()

                # 输出最后一条助手消息
                for msg in reversed(result.messages):
                    if msg.type == "assistant" and msg.message.content:
                        print(msg.message.content)
                        break
            except Exception as e:
                print(f"Error: {e}")

    await prompt()


if __name__ == "__main__":
    asyncio.run(main())