"""基本用法示例

演示如何创建 Agent 并执行简单任务。
"""

import asyncio
import os
import sys

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent import Agent, AgentConfig
from src.tools import get_builtin_tools


async def main() -> None:
    """主函数"""
    # 检查环境变量
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set")
        return

    # 创建 Agent 配置
    config = AgentConfig(
        cwd=os.getcwd(),
        api_key=api_key,
        model="gpt-4o",
        max_tokens=4096,
        permission_mode="bypass_permissions",  # 跳过权限检查
        max_iterations=20,                     # 设置最大迭代次数
        timeout_ms=30000,                      # 设置超时时间（30秒）
    )

    # 创建 Agent 实例
    agent = Agent(config)

    # 注册内置工具
    agent.register_tools(get_builtin_tools())

    # 添加用户消息
    agent.add_user_message("创建一个简单的 Python 项目，包含 requirements.txt 和 README.md")

    # 运行 Agent
    print("Running agent...")
    result = await agent.run()

    # 输出结果
    print("\n" + "=" * 50)
    print("Token Usage:")
    print(f"  Input:  {result.token_usage['input_tokens']}")
    print(f"  Output: {result.token_usage['output_tokens']}")
    print("\nMessages:")
    for msg in result.messages:
        if msg.type == "user":
            content = msg.message.content
            if isinstance(content, str):
                print(f"[user] {content[:100]}...")
        elif msg.type == "assistant":
            content = msg.message.content
            if content:
                print(f"[assistant] {content[:100]}...")
            elif msg.message.tool_calls:
                print(f"[assistant] (called {len(msg.message.tool_calls)} tools)")
        elif msg.type == "tool":
            print(f"[tool] {msg.message.content[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())