"""类型定义模块

定义 Agent 系统中使用的所有核心类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union, Any, Optional
from uuid import uuid4
import time


# =============================================================================
# 消息内容类型
# =============================================================================

@dataclass
class TextContent:
    """文本内容"""
    type: Literal["text"] = "text"
    text: str = ""


@dataclass
class ToolUseContent:
    """工具调用内容 - 模型请求调用的工具"""
    type: Literal["tool_use"] = "tool_use"
    id: str = ""              # 工具调用唯一标识
    name: str = ""            # 工具名称
    input: dict[str, Any] = field(default_factory=dict)  # 工具输入参数


@dataclass
class ToolResultContent:
    """工具结果内容 - 工具执行后的返回"""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""     # 对应的工具调用 ID
    content: str = ""         # 工具执行结果
    is_error: bool = False    # 是否为错误结果


# 消息内容联合类型
MessageContent = Union[TextContent, ToolUseContent, ToolResultContent]


# =============================================================================
# OpenAI API 消息格式
# =============================================================================

@dataclass
class UserMessageParam:
    """用户消息参数"""
    role: Literal["user"] = "user"
    content: str | list[dict[str, Any]] = ""


@dataclass
class ToolCall:
    """工具调用（OpenAI 格式）"""
    id: str
    type: Literal["function"] = "function"
    function: dict[str, str] = field(default_factory=dict)  # {name, arguments}


@dataclass
class AssistantMessageParam:
    """助手消息参数"""
    role: Literal["assistant"] = "assistant"
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ToolMessageParam:
    """工具结果消息参数"""
    role: Literal["tool"] = "tool"
    tool_call_id: str = ""
    content: str = ""


# =============================================================================
# 消息类型
# =============================================================================

@dataclass
class UserMessage:
    """用户消息"""
    type: Literal["user"] = "user"
    message: UserMessageParam = field(default_factory=UserMessageParam)
    uuid: str = field(default_factory=lambda: str(uuid4()))
    parent_uuid: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class AssistantMessage:
    """助手消息"""
    type: Literal["assistant"] = "assistant"
    message: AssistantMessageParam = field(default_factory=AssistantMessageParam)
    uuid: str = field(default_factory=lambda: str(uuid4()))
    parent_uuid: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class ToolMessage:
    """工具结果消息"""
    type: Literal["tool"] = "tool"
    message: ToolMessageParam = field(default_factory=ToolMessageParam)
    uuid: str = field(default_factory=lambda: str(uuid4()))
    parent_uuid: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class SystemMessage:
    """系统消息"""
    type: Literal["system"] = "system"
    subtype: str = ""
    content: str = ""
    uuid: str = field(default_factory=lambda: str(uuid4()))
    parent_uuid: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))


# 消息联合类型
Message = Union[UserMessage, AssistantMessage, ToolMessage, SystemMessage]