"""无 API Key 测试示例

使用 Mock 客户端测试 Agent，无需 OpenAI API Key。
"""

import asyncio
import os
import sys

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from src.agent.agent import Agent, AgentConfig
from src.agent.mock_client import MockLLMClient
from src.tools import get_builtin_tools


async def test_file_read() -> None:
    """测试文件读取功能"""
    print("\n" + "=" * 50)
    print("测试 1: 文件读取")
    print("=" * 50)

    config = AgentConfig(
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        api_key="mock-key",
        model="mock",
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)
    agent.llm_client = MockLLMClient()  # 使用 Mock 客户端
    agent.register_tools(get_builtin_tools())

    # 请求读取 README.md
    agent.add_user_message("读取 README.md 文件")
    result = await agent.run()

    print(f"\nToken 使用: 输入 {result.token_usage['input_tokens']}, 输出 {result.token_usage['output_tokens']}")
    print("\n消息历史:")
    for msg in result.messages:
        if msg.type == "user":
            print(f"  [用户] {msg.message.content}")
        elif msg.type == "assistant":
            if msg.message.content:
                print(f"  [助手] {msg.message.content[:100]}...")
            elif msg.message.tool_calls:
                for tc in msg.message.tool_calls:
                    print(f"  [助手] 调用工具: {tc.function.get('name')}")
        elif msg.type == "tool":
            print(f"  [工具] {msg.message.content[:100]}...")


async def test_file_write() -> None:
    """测试文件创建功能"""
    print("\n" + "=" * 50)
    print("测试 2: 文件创建")
    print("=" * 50)

    config = AgentConfig(
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        api_key="mock-key",
        model="mock",
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)
    agent.llm_client = MockLLMClient()
    agent.register_tools(get_builtin_tools())

    # 请求创建文件
    agent.add_user_message("创建一个 requirements.txt 文件")
    result = await agent.run()

    print(f"\nToken 使用: 输入 {result.token_usage['input_tokens']}, 输出 {result.token_usage['output_tokens']}")
    print("\n消息历史:")
    for msg in result.messages:
        if msg.type == "user":
            print(f"  [用户] {msg.message.content}")
        elif msg.type == "assistant":
            if msg.message.content:
                print(f"  [助手] {msg.message.content[:100]}...")
            elif msg.message.tool_calls:
                for tc in msg.message.tool_calls:
                    print(f"  [助手] 调用工具: {tc.function.get('name')}")
        elif msg.type == "tool":
            print(f"  [工具] {msg.message.content[:100]}...")


async def test_bash_command() -> None:
    """测试命令执行功能"""
    print("\n" + "=" * 50)
    print("测试 3: 命令执行")
    print("=" * 50)

    config = AgentConfig(
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        api_key="mock-key",
        model="mock",
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)
    agent.llm_client = MockLLMClient()
    agent.register_tools(get_builtin_tools())

    # 请求执行命令
    agent.add_user_message("运行 ls 命令查看文件列表")
    result = await agent.run()

    print(f"\nToken 使用: 输入 {result.token_usage['input_tokens']}, 输出 {result.token_usage['output_tokens']}")
    print("\n消息历史:")
    for msg in result.messages:
        if msg.type == "user":
            print(f"  [用户] {msg.message.content}")
        elif msg.type == "assistant":
            if msg.message.content:
                print(f"  [助手] {msg.message.content[:100]}...")
            elif msg.message.tool_calls:
                for tc in msg.message.tool_calls:
                    print(f"  [助手] 调用工具: {tc.function.get('name')}")
        elif msg.type == "tool":
            print(f"  [工具] {msg.message.content[:100]}...")


async def test_interactive_repl() -> None:
    """测试交互式 REPL"""
    print("\n" + "=" * 50)
    print("测试 4: 交互式 REPL (Mock)")
    print("=" * 50)

    config = AgentConfig(
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        api_key="mock-key",
        model="mock",
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)
    agent.llm_client = MockLLMClient()
    agent.register_tools(get_builtin_tools())

    # 模拟多轮对话
    conversations = [
        "读取 README.md",
        "创建一个 example.py 文件",
    ]

    for user_input in conversations:
        print(f"\n> {user_input}")
        agent.add_user_message(user_input)
        result = await agent.run()

        # 输出最后一条助手消息
        for msg in reversed(result.messages):
            if msg.type == "assistant" and msg.message.content:
                print(f"< {msg.message.content[:200]}...")
                break
            elif msg.type == "assistant" and msg.message.tool_calls:
                tools = [tc.function.get("name") for tc in msg.message.tool_calls]
                print(f"< [调用工具: {', '.join(tools)}]")
                break


async def main() -> None:
    """主函数"""
    print("=" * 50)
    print("SimpleAgent Python 测试套件 (无 API Key)")
    print("=" * 50)

    await test_file_read()
    await test_file_write()
    await test_bash_command()
    await test_interactive_repl()

    print("\n" + "=" * 50)
    print("所有测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())