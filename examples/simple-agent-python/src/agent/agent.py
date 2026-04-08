"""Agent 核心实现"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from src.agent.llm_client import LLMClient
from src.agent.types import (
    Message,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    UserMessageParam,
    AssistantMessageParam,
    ToolMessageParam,
    ToolCall,
    ToolUseContent,
)
from src.tools.base import Tool, ToolContext
from src.permissions.checker import PermissionChecker
from src.permissions.types import PermissionMode
from src.state.store import StateStore, AppState, create_state_store
from src.state.session import SessionStorage


# =============================================================================
# 配置和结果类型
# =============================================================================

@dataclass
class AgentConfig:
    """Agent 配置"""
    cwd: str                                    # 工作目录
    api_key: str                                # OpenAI API Key
    model: str = "gpt-4o"                       # 模型名称
    max_tokens: int = 4096                      # 最大输出 token
    temperature: float = 0.7                    # 温度参数
    permission_mode: PermissionMode = "default" # 权限模式
    session_dir: str | None = None              # 会话存储目录
    max_iterations: int = 50                    # 最大迭代次数
    timeout_ms: int | None = None               # 超时时间（毫秒）
    # signal 可以通过 asyncio 任务取消实现


@dataclass
class AgentResult:
    """Agent 运行结果"""
    messages: list[Message]
    token_usage: dict[str, int]


# =============================================================================
# Agent 核心类
# =============================================================================

class Agent:
    """Agent 核心类

    实现完整的 Agent 循环：
    1. 接收用户消息
    2. 调用 LLM
    3. 处理工具调用
    4. 返回结果
    """

    def __init__(self, config: AgentConfig) -> None:
        """初始化 Agent

        Args:
            config: Agent 配置
        """
        # 验证配置
        if not config.api_key:
            raise ValueError("API key is required")
        if not config.model:
            raise ValueError("Model is required")
        if config.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if config.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

        self.cwd = config.cwd
        self.max_iterations = config.max_iterations
        self.timeout_ms = config.timeout_ms

        # 初始化 LLM 客户端
        self.llm_client = LLMClient(
            api_key=config.api_key,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            timeout_ms=config.timeout_ms,
        )

        # 初始化权限检查器
        self.permission_checker = PermissionChecker.from_config(
            mode=config.permission_mode
        )

        # 初始化状态存储
        self.state = create_state_store()

        # 初始化会话存储（可选）
        self.session_storage: SessionStorage | None = None
        if config.session_dir:
            self.session_storage = SessionStorage(config.session_dir)

        # 注册的工具映射
        self._registered_tools: dict[str, Tool] = {}

    def register_tools(self, tools: list[Tool]) -> None:
        """注册工具列表

        Args:
            tools: 工具列表
        """
        for tool in tools:
            self._registered_tools[tool.name] = tool

    def add_user_message(self, content: str) -> None:
        """添加用户消息

        Args:
            content: 消息内容
        """
        state = self.state.get_state()
        parent_uuid = state.messages[-1].uuid if state.messages else None

        message = UserMessage(
            type="user",
            message=UserMessageParam(role="user", content=content),
            uuid=str(uuid4()),
            parent_uuid=parent_uuid,
            timestamp=int(time.time() * 1000),
        )

        self.state.set_state(lambda s: AppState(
            session_id=s.session_id,
            messages=s.messages + [message],
            pending_tool_calls=s.pending_tool_calls,
            is_processing=s.is_processing,
            token_usage=s.token_usage,
        ))

    def _add_assistant_message(
        self,
        content: str | None,
        tool_calls: list[ToolUseContent] | None = None,
    ) -> None:
        """添加助手消息"""
        state = self.state.get_state()
        parent_uuid = state.messages[-1].uuid if state.messages else None

        # 转换工具调用格式
        tc_list: list[ToolCall] = []
        if tool_calls:
            for tc in tool_calls:
                tc_list.append(ToolCall(
                    id=tc.id,
                    type="function",
                    function={
                        "name": tc.name,
                        "arguments": json.dumps(tc.input),
                    },
                ))

        message = AssistantMessage(
            type="assistant",
            message=AssistantMessageParam(
                role="assistant",
                content=content,
                tool_calls=tc_list,
            ),
            uuid=str(uuid4()),
            parent_uuid=parent_uuid,
            timestamp=int(time.time() * 1000),
        )

        self.state.set_state(lambda s: AppState(
            session_id=s.session_id,
            messages=s.messages + [message],
            pending_tool_calls=s.pending_tool_calls,
            is_processing=s.is_processing,
            token_usage=s.token_usage,
        ))

    def _add_tool_result_message(
        self,
        tool_call_id: str,
        content: str,
        is_error: bool = False,
    ) -> None:
        """添加工具结果消息"""
        state = self.state.get_state()
        parent_uuid = state.messages[-1].uuid if state.messages else None

        message = ToolMessage(
            type="tool",
            message=ToolMessageParam(
                role="tool",
                tool_call_id=tool_call_id,
                content=content,
            ),
            uuid=str(uuid4()),
            parent_uuid=parent_uuid,
            timestamp=int(time.time() * 1000),
        )

        self.state.set_state(lambda s: AppState(
            session_id=s.session_id,
            messages=s.messages + [message],
            pending_tool_calls=s.pending_tool_calls,
            is_processing=s.is_processing,
            token_usage=s.token_usage,
        ))

    async def run(self) -> AgentResult:
        """运行 Agent 主循环

        Returns:
            Agent 运行结果
        """
        # 设置处理状态
        self.state.set_state(lambda s: AppState(
            session_id=s.session_id,
            messages=s.messages,
            pending_tool_calls=s.pending_tool_calls,
            is_processing=True,
            token_usage=s.token_usage,
        ))

        try:
            tool_list = list(self._registered_tools.values())
            iteration = 0

            while iteration < self.max_iterations:
                iteration += 1

                # 检查是否已取消
                try:
                    asyncio.current_task().cancelled()  # 触发 CancelledError 如果已取消
                except asyncio.CancelledError:
                    raise

                # 获取当前消息
                messages = self.state.get_state().messages

                # 调用 LLM（带超时检查）
                response = await self.llm_client.chat(messages, tool_list)

                # 更新 token 使用统计
                self.state.set_state(lambda s: AppState(
                    session_id=s.session_id,
                    messages=s.messages,
                    pending_tool_calls=s.pending_tool_calls,
                    is_processing=s.is_processing,
                    token_usage={
                        "input_tokens": s.token_usage["input_tokens"] + response.usage["input_tokens"],
                        "output_tokens": s.token_usage["output_tokens"] + response.usage["output_tokens"],
                    },
                ))

                # 添加助手消息
                if response.content:
                    self._add_assistant_message(response.content)

                # 处理工具调用
                if response.tool_calls:
                    self._add_assistant_message(None, response.tool_calls)

                    for tool_call in response.tool_calls:
                        # 检查是否已取消
                        try:
                            asyncio.current_task().cancelled()
                        except asyncio.CancelledError:
                            raise

                        result = await self._execute_tool_call(tool_call)
                        self._add_tool_result_message(
                            tool_call.id,
                            result["content"],
                            result["is_error"],
                        )

                    # 继续循环，让 LLM 处理工具结果
                    continue

                # 没有工具调用，结束循环
                break

            # 检查是否达到最大迭代次数
            if iteration >= self.max_iterations:
                raise RuntimeError(f"Max iterations ({self.max_iterations}) reached")

            # 保存会话
            await self._save_session()

            final_state = self.state.get_state()
            return AgentResult(
                messages=final_state.messages,
                token_usage=final_state.token_usage,
            )

        except asyncio.CancelledError:
            # 任务被取消，转换为更友好的错误消息
            raise RuntimeError("Agent execution cancelled")
        finally:
            # 重置处理状态
            self.state.set_state(lambda s: AppState(
                session_id=s.session_id,
                messages=s.messages,
                pending_tool_calls=s.pending_tool_calls,
                is_processing=False,
                token_usage=s.token_usage,
            ))

    async def _execute_tool_call(
        self,
        tool_call: ToolUseContent,
    ) -> dict[str, Any]:
        """执行工具调用

        Args:
            tool_call: 工具调用请求

        Returns:
            执行结果 {"content": str, "is_error": bool}
        """
        # 查找工具
        tool = self._registered_tools.get(tool_call.name)
        if not tool:
            return {
                "content": f"Tool not found: {tool_call.name}",
                "is_error": True,
            }

        # 构建工具上下文
        state = self.state.get_state()
        context = ToolContext(
            cwd=self.cwd,
            session_id=state.session_id,
        )

        # 权限检查
        permission_check = await self.permission_checker.check_permission(
            tool,
            tool_call.input,
            context,
        )

        if not permission_check.allowed:
            return {
                "content": f"Permission denied: {permission_check.reason}",
                "is_error": True,
            }

        # 解析输入参数
        try:
            parsed_input = tool.input_schema(**tool_call.input)
        except Exception as e:
            return {
                "content": f"Invalid input for tool {tool.name}: {str(e)}",
                "is_error": True,
            }

        # 执行工具（带超时）
        try:
            coro = tool.call(parsed_input, context)
            if self.timeout_ms:
                result = await asyncio.wait_for(coro, timeout=self.timeout_ms / 1000.0)
            else:
                result = await coro
            return {
                "content": result.content,
                "is_error": result.is_error,
            }
        except asyncio.TimeoutError:
            return {
                "content": f"Tool execution timeout after {self.timeout_ms}ms",
                "is_error": True,
            }
        except asyncio.CancelledError:
            return {
                "content": "Tool execution cancelled",
                "is_error": True,
            }
        except Exception as e:
            return {
                "content": f"Tool execution error for {tool.name}: {str(e)}",
                "is_error": True,
            }

    async def _save_session(self) -> None:
        """保存会话到磁盘"""
        if not self.session_storage:
            return

        state = self.state.get_state()
        messages = state.messages

        for message in messages:
            await self.session_storage.append_message(state.session_id, message)

        title = self.session_storage.extract_title(messages) or "Untitled Session"
        await self.session_storage.save_metadata({
            "session_id": state.session_id,
            "title": title,
            "created_at": messages[0].timestamp if messages else int(time.time() * 1000),
            "updated_at": messages[-1].timestamp if messages else int(time.time() * 1000),
            "project_dir": self.cwd,
        })

    def get_state(self) -> AppState:
        """获取当前状态"""
        return self.state.get_state()

    def subscribe_state(self, listener: callable) -> callable:
        """订阅状态变化

        Args:
            listener: 监听器函数

        Returns:
            取消订阅函数
        """
        return self.state.subscribe(listener)