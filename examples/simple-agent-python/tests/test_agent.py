"""Agent 测试

使用 Mock 客户端测试，无需 API Key。
"""

import pytest
import asyncio
from pathlib import Path
from uuid import uuid4
import sys

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agent.types import (
    UserMessage,
    AssistantMessage,
    ToolMessage,
    UserMessageParam,
    AssistantMessageParam,
    ToolMessageParam,
    ToolUseContent,
)
from src.agent.agent import Agent, AgentConfig
from src.agent.mock_client import MockLLMClient
from src.tools.base import Tool, ToolResult, ToolContext, build_tool
from src.tools import get_builtin_tools
from src.permissions.checker import PermissionChecker
from src.permissions.types import PermissionMode
from src.state.store import create_state_store, AppState
from pydantic import BaseModel


# =============================================================================
# 测试工具
# =============================================================================

class EchoInput(BaseModel):
    """测试工具输入"""
    message: str


async def echo_fn(input: EchoInput, context: ToolContext) -> ToolResult:
    """回显工具"""
    return ToolResult(content=f"Echo: {input.message}")


EchoTool = build_tool(
    name="Echo",
    description="Echo back the message",
    input_schema=EchoInput,
    call_fn=echo_fn,
    is_read_only=True,
)


# =============================================================================
# 类型测试
# =============================================================================

def test_user_message():
    """测试用户消息创建"""
    msg = UserMessage(
        type="user",
        message=UserMessageParam(role="user", content="Hello"),
    )
    assert msg.type == "user"
    assert msg.message.content == "Hello"
    assert msg.uuid is not None
    assert msg.timestamp > 0


def test_assistant_message():
    """测试助手消息创建"""
    msg = AssistantMessage(
        type="assistant",
        message=AssistantMessageParam(role="assistant", content="Hi there!"),
    )
    assert msg.type == "assistant"
    assert msg.message.content == "Hi there!"


def test_tool_message():
    """测试工具结果消息创建"""
    msg = ToolMessage(
        type="tool",
        message=ToolMessageParam(
            role="tool",
            tool_call_id="call_123",
            content="Result",
        ),
    )
    assert msg.type == "tool"
    assert msg.message.tool_call_id == "call_123"


def test_tool_use_content():
    """测试工具调用内容"""
    tc = ToolUseContent(
        type="tool_use",
        id="call_abc",
        name="Bash",
        input={"command": "ls"},
    )
    assert tc.type == "tool_use"
    assert tc.name == "Bash"
    assert tc.input["command"] == "ls"


# =============================================================================
# 工具测试
# =============================================================================

@pytest.mark.asyncio
async def test_tool_creation():
    """测试工具创建"""
    assert EchoTool.name == "Echo"
    assert EchoTool.description == "Echo back the message"
    assert EchoTool.is_read_only() is True
    assert EchoTool.is_concurrency_safe() is False


@pytest.mark.asyncio
async def test_tool_execution():
    """测试工具执行"""
    context = ToolContext(cwd="/tmp", session_id="test")
    input = EchoInput(message="test message")
    result = await EchoTool.call(input, context)

    assert result.content == "Echo: test message"
    assert result.is_error is False


@pytest.mark.asyncio
async def test_builtin_tools():
    """测试内置工具"""
    tools = get_builtin_tools()
    tool_names = [t.name for t in tools]

    assert "Bash" in tool_names
    assert "FileRead" in tool_names
    assert "FileWrite" in tool_names


# =============================================================================
# 权限测试
# =============================================================================

def test_permission_bypass():
    """测试跳过权限模式"""
    checker = PermissionChecker.from_config(mode="bypass_permissions")
    check = asyncio.run(checker.check_permission(
        EchoTool,
        {"message": "test"},
        ToolContext(cwd="/tmp", session_id="test"),
    ))
    assert check.allowed is True


def test_permission_dont_ask():
    """测试不询问模式"""
    checker = PermissionChecker.from_config(mode="dont_ask")
    check = asyncio.run(checker.check_permission(
        EchoTool,
        {"message": "test"},
        ToolContext(cwd="/tmp", session_id="test"),
    ))
    assert check.allowed is False


def test_permission_auto_read_only():
    """测试自动模式的只读工具"""
    checker = PermissionChecker.from_config(mode="auto")
    check = asyncio.run(checker.check_permission(
        EchoTool,
        {"message": "test"},
        ToolContext(cwd="/tmp", session_id="test"),
    ))
    # 只读工具在 auto 模式下应该允许
    assert check.allowed is True


def test_permission_default():
    """测试默认权限模式"""
    checker = PermissionChecker.from_config(mode="default")
    check = asyncio.run(checker.check_permission(
        EchoTool,
        {"message": "test"},
        ToolContext(cwd="/tmp", session_id="test"),
    ))
    # 默认模式需要确认
    assert check.requires_confirmation is True


# =============================================================================
# 状态存储测试
# =============================================================================

def test_state_store_creation():
    """测试状态存储创建"""
    store = create_state_store()
    state = store.get_state()

    assert state.session_id is not None
    assert state.messages == []
    assert state.is_processing is False


def test_state_store_update():
    """测试状态更新"""
    store = create_state_store()

    # 添加消息
    msg = UserMessage(
        type="user",
        message=UserMessageParam(role="user", content="test"),
    )
    store.set_state(lambda s: AppState(
        session_id=s.session_id,
        messages=[msg],
        pending_tool_calls=s.pending_tool_calls,
        is_processing=s.is_processing,
        token_usage=s.token_usage,
    ))

    state = store.get_state()
    assert len(state.messages) == 1
    assert state.messages[0].message.content == "test"


def test_state_subscribe():
    """测试状态订阅"""
    store = create_state_store()
    call_count = [0]

    def listener():
        call_count[0] += 1

    unsubscribe = store.subscribe(listener)

    # 更新状态，应该触发监听器
    store.set_state(lambda s: AppState(
        session_id=s.session_id,
        messages=s.messages,
        pending_tool_calls=s.pending_tool_calls,
        is_processing=True,
        token_usage=s.token_usage,
    ))

    assert call_count[0] == 1

    # 取消订阅
    unsubscribe()

    # 再次更新，不应该触发
    store.set_state(lambda s: AppState(
        session_id=s.session_id,
        messages=s.messages,
        pending_tool_calls=s.pending_tool_calls,
        is_processing=False,
        token_usage=s.token_usage,
    ))

    assert call_count[0] == 1


# =============================================================================
# Mock 客户端测试
# =============================================================================

@pytest.mark.asyncio
async def test_mock_client_file_read():
    """测试 Mock 客户端文件读取"""
    mock_client = MockLLMClient()

    # 创建用户消息
    messages = [
        UserMessage(
            type="user",
            message=UserMessageParam(role="user", content="读取 README.md"),
        )
    ]

    response = await mock_client.chat(messages, [])

    assert response["tool_calls"]
    assert response["tool_calls"][0].name == "FileRead"
    assert "README.md" in response["tool_calls"][0].input["path"]


@pytest.mark.asyncio
async def test_mock_client_file_write():
    """测试 Mock 客户端文件写入"""
    mock_client = MockLLMClient()

    messages = [
        UserMessage(
            type="user",
            message=UserMessageParam(role="user", content="创建一个 requirements.txt 文件"),
        )
    ]

    response = await mock_client.chat(messages, [])

    assert response["tool_calls"]
    assert response["tool_calls"][0].name == "FileWrite"


@pytest.mark.asyncio
async def test_mock_client_bash():
    """测试 Mock 客户端命令执行"""
    mock_client = MockLLMClient()

    messages = [
        UserMessage(
            type="user",
            message=UserMessageParam(role="user", content="运行 ls 命令"),
        )
    ]

    response = await mock_client.chat(messages, [])

    assert response["tool_calls"]
    assert response["tool_calls"][0].name == "Bash"


# =============================================================================
# Agent 集成测试（使用 Mock 客户端）
# =============================================================================

@pytest.mark.asyncio
async def test_agent_with_mock():
    """测试 Agent 与 Mock 客户端集成"""
    config = AgentConfig(
        cwd="/tmp",
        api_key="mock-key",
        model="mock",
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)
    agent.llm_client = MockLLMClient()
    agent.register_tools(get_builtin_tools())

    agent.add_user_message("读取 README.md 文件")
    result = await agent.run()

    assert len(result.messages) > 0
    assert result.token_usage["input_tokens"] > 0


@pytest.mark.asyncio
async def test_agent_multiple_turns():
    """测试 Agent 多轮对话"""
    config = AgentConfig(
        cwd="/tmp",
        api_key="mock-key",
        model="mock",
        permission_mode="bypass_permissions",
    )
    agent = Agent(config)
    agent.llm_client = MockLLMClient()
    agent.register_tools(get_builtin_tools())

    # 第一轮
    agent.add_user_message("读取 README.md")
    result1 = await agent.run()
    assert len(result1.messages) > 0

    # 第二轮
    agent.add_user_message("创建一个 test.py 文件")
    result2 = await agent.run()
    assert len(result2.messages) > len(result1.messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])