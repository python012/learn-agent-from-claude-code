"""Mock LLM 客户端

用于测试环境，无需真实 API key 即可运行。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from src.agent.types import Message, ToolUseContent
from src.tools.base import Tool


@dataclass
class MockResponse:
    """Mock 响应配置"""
    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class MockLLMClient:
    """Mock LLM 客户端

    模拟 LLM 响应，用于测试。根据用户消息内容自动决定调用哪个工具。

    Example:
        ```python
        # 使用 Mock 客户端创建 Agent
        from src.agent.agent import Agent, AgentConfig
        from src.agent.mock_client import MockLLMClient

        agent = Agent(AgentConfig(
            cwd=".",
            api_key="mock",  # 可以是任意值
            model="mock",
        ))
        agent.llm_client = MockLLMClient()

        # 现在可以运行 Agent，会得到模拟响应
        agent.add_user_message("读取 README.md 文件")
        result = await agent.run()
        ```
    """

    def __init__(self) -> None:
        """初始化 Mock 客户端"""
        self.call_count = 0
        self.conversation_history: list[str] = []

    async def chat(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
    ) -> dict[str, Any]:
        """模拟聊天请求

        根据用户消息内容自动决定响应。

        Args:
            messages: 消息历史
            tools: 可用工具列表

        Returns:
            模拟的 LLM 响应
        """
        self.call_count += 1

        # 获取最后一条用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.type == "user":
                user_message = msg.message.content if isinstance(msg.message.content, str) else ""
                break

        self.conversation_history.append(user_message)

        # 检查是否已有工具结果（第二轮对话）
        has_tool_result = any(msg.type == "tool" for msg in messages)

        if has_tool_result:
            # 工具执行后，返回总结响应
            return self._create_summary_response(messages)

        # 根据用户消息决定调用哪个工具
        return self._analyze_and_respond(user_message, tools)

    def _analyze_and_respond(
        self,
        user_message: str,
        tools: list[Tool] | None,
    ) -> dict[str, Any]:
        """分析用户消息并生成响应"""

        # 检查是否要读取文件
        read_match = re.search(r"读取|查看|显示|read\s+(\S+)", user_message, re.IGNORECASE)
        if read_match or "文件" in user_message and ("读取" in user_message or "查看" in user_message):
            filename = read_match.group(1) if read_match and read_match.group(1) else "README.md"
            if not filename.endswith((".md", ".txt", ".py", ".json", ".yaml", ".yml")):
                filename = "README.md"
            return self._create_tool_call_response("FileRead", {"path": filename})

        # 检查是否要写入文件
        write_match = re.search(r"创建|写入|新建|write\s+(\S+)", user_message, re.IGNORECASE)
        if write_match or ("创建" in user_message and ("文件" in user_message or "项目" in user_message)):
            # 创建一个简单的文件
            if "requirements" in user_message.lower() or "依赖" in user_message:
                return self._create_tool_call_response("FileWrite", {
                    "path": "requirements.txt",
                    "content": "# Project dependencies\nopenai>=1.0.0\npydantic>=2.0.0\n"
                })
            elif "readme" in user_message.lower():
                return self._create_tool_call_response("FileWrite", {
                    "path": "README.md",
                    "content": "# Project\n\nA sample project created by SimpleAgent.\n"
                })
            else:
                return self._create_tool_call_response("FileWrite", {
                    "path": "example.py",
                    "content": '"""Example file created by SimpleAgent"""\n\ndef hello():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    hello()\n'
                })

        # 检查是否要执行命令
        bash_match = re.search(r"运行|执行|run\s+(.+)|bash\s+(.+)", user_message, re.IGNORECASE)
        if bash_match or "命令" in user_message:
            command = bash_match.group(1) or bash_match.group(2) if bash_match else "ls -la"
            return self._create_tool_call_response("Bash", {"command": command.strip()})

        # 检查是否问天气（自定义工具示例）
        if "天气" in user_message or "weather" in user_message.lower():
            city_match = re.search(r"(\w+)[的]?天气", user_message)
            city = city_match.group(1) if city_match else "北京"
            return self._create_tool_call_response("GetWeather", {"city": city})

        # 默认：直接回复文本
        return {
            "content": f"我理解您的请求：{user_message}\n\n但是这是一个 Mock 客户端，我只能处理特定的测试场景：\n"
                       "- 读取文件：说 '读取 README.md' 或 '查看文件'\n"
                       "- 创建文件：说 '创建一个 requirements.txt' 或 '新建文件'\n"
                       "- 执行命令：说 '运行 ls' 或 '执行命令'\n"
                       "- 问天气：说 '北京天气怎么样'",
            "tool_calls": [],
            "usage": {"input_tokens": 50, "output_tokens": 100, "total_tokens": 150},
        }

    def _create_tool_call_response(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """创建工具调用响应"""
        return {
            "content": None,
            "tool_calls": [
                ToolUseContent(
                    type="tool_use",
                    id=f"call_{uuid4().hex[:8]}",
                    name=tool_name,
                    input=tool_input,
                )
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        }

    def _create_summary_response(self, messages: list[Message]) -> dict[str, Any]:
        """创建工具执行后的总结响应"""
        # 收集工具结果
        tool_results = []
        for msg in messages:
            if msg.type == "tool":
                tool_results.append(msg.message.content)

        if tool_results:
            summary = f"我已完成您请求的操作。结果如下：\n\n"
            for i, result in enumerate(tool_results[-3:], 1):  # 只显示最近 3 个结果
                summary += f"{i}. {result[:200]}{'...' if len(result) > 200 else ''}\n\n"
        else:
            summary = "操作已完成。"

        return {
            "content": summary,
            "tool_calls": [],
            "usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
        }