"""OpenAI 客户端封装"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.agent.types import Message, ToolUseContent
from src.tools.base import Tool


# =============================================================================
# 类型定义
# =============================================================================

@dataclass
class OpenAITool:
    """OpenAI 工具格式"""
    type: str = "function"
    function: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM 响应结果"""
    content: str | None = None
    tool_calls: list[ToolUseContent] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    })


# =============================================================================
# LLM 客户端
# =============================================================================

class LLMClient:
    """OpenAI API 客户端封装

    封装 OpenAI Chat Completion API，支持工具调用。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        base_url: str | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        """初始化 LLM 客户端

        Args:
            api_key: OpenAI API Key
            model: 模型名称
            max_tokens: 最大输出 token 数
            temperature: 温度参数
            base_url: API 基础 URL（可选，用于自定义端点）
            timeout_ms: 超时时间（毫秒）
        """
        # 验证配置
        if not api_key:
            raise ValueError("API key is required")
        if not model:
            raise ValueError("Model is required")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_ms = timeout_ms

        # 初始化 OpenAI 客户端
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if timeout_ms:
            client_kwargs["timeout"] = timeout_ms / 1000.0  # 转换为秒
        self.client = AsyncOpenAI(**client_kwargs)

    async def chat(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
    ) -> LLMResponse:
        """发送聊天请求

        Args:
            messages: 消息历史
            tools: 可用工具列表

        Returns:
            LLM 响应结果
        """
        # 转换消息格式
        openai_messages = self._convert_messages(messages)

        # 转换工具格式
        openai_tools = self._convert_tools(tools) if tools else None

        # 构建 API 请求参数
        request_params: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if openai_tools:
            request_params["tools"] = openai_tools
            request_params["tool_choice"] = "auto"

        # 调用 API
        response = await self.client.chat.completions.create(**request_params)

        # 提取响应内容
        choice = response.choices[0]
        if not choice:
            raise ValueError("No response from OpenAI")

        # 提取工具调用
        tool_calls: list[ToolUseContent] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolUseContent(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))

        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """将内部消息格式转换为 OpenAI 格式"""
        openai_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.type == "user":
                openai_messages.append({
                    "role": "user",
                    "content": msg.message.content,
                })
            elif msg.type == "assistant":
                if msg.message.tool_calls:
                    openai_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.get("name", ""),
                                    "arguments": tc.function.get("arguments", "{}"),
                                }
                            }
                            for tc in msg.message.tool_calls
                        ],
                    })
                else:
                    openai_messages.append({
                        "role": "assistant",
                        "content": msg.message.content,
                    })
            elif msg.type == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.message.tool_call_id,
                    "content": msg.message.content,
                })

        return openai_messages

    def _convert_tools(self, tools: list[Tool]) -> list[dict[str, Any]]:
        """将内部工具格式转换为 OpenAI 格式"""
        openai_tools: list[dict[str, Any]] = []

        for tool in tools:
            # 将 Pydantic Schema 转换为 JSON Schema
            schema = tool.input_schema.model_json_schema()
            # 移除不需要的字段
            schema.pop("title", None)

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                },
            })

        return openai_tools