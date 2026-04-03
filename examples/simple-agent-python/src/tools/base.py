"""工具基类模块

定义工具接口和构建器。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional
from pydantic import BaseModel


# =============================================================================
# 工具上下文和结果
# =============================================================================

@dataclass
class ToolContext:
    """工具执行上下文"""
    cwd: str                    # 当前工作目录
    session_id: str             # 会话 ID


@dataclass
class ToolResult:
    """工具执行结果"""
    content: str                                # 结果内容
    is_error: bool = False                      # 是否为错误
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据


# =============================================================================
# 权限检查结果
# =============================================================================

@dataclass
class PermissionCheckResult:
    """权限检查结果"""
    allowed: bool = False                       # 是否允许
    reason: str = ""                            # 原因说明
    requires_user_confirmation: bool = False    # 是否需要用户确认


# =============================================================================
# 工具接口
# =============================================================================

class Tool(ABC):
    """工具抽象基类

    所有工具都需要实现这个接口。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（用于系统提示）"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        """输入 Schema（Pydantic 模型）"""
        pass

    @abstractmethod
    async def call(self, input: BaseModel, context: ToolContext) -> ToolResult:
        """执行工具调用"""
        pass

    def is_concurrency_safe(self) -> bool:
        """是否可以并发执行，默认 False"""
        return False

    def is_read_only(self) -> bool:
        """是否为只读操作，默认 False"""
        return False

    async def check_permissions(
        self,
        input: BaseModel,
        context: ToolContext
    ) -> PermissionCheckResult:
        """自定义权限检查，默认允许"""
        return PermissionCheckResult(allowed=True)


# =============================================================================
# 工具构建器
# =============================================================================

class FunctionalTool(Tool):
    """基于函数的工具实现

    允许通过函数快速定义工具，无需创建完整类。
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: type[BaseModel],
        call_fn: Callable[[BaseModel, ToolContext], Awaitable[ToolResult]],
        is_concurrency_safe_fn: Callable[[], bool] | None = None,
        is_read_only_fn: Callable[[], bool] | None = None,
        check_permissions_fn: Callable[[BaseModel, ToolContext], Awaitable[PermissionCheckResult]] | None = None,
    ) -> None:
        """初始化工具

        Args:
            name: 工具名称
            description: 工具描述
            input_schema: 输入 Schema（Pydantic 模型类）
            call_fn: 异步执行函数
            is_concurrency_safe_fn: 是否并发安全判断函数
            is_read_only_fn: 是否只读判断函数
            check_permissions_fn: 权限检查函数
        """
        self._name = name
        self._description = description
        self._input_schema = input_schema
        self._call_fn = call_fn
        self._is_concurrency_safe_fn = is_concurrency_safe_fn
        self._is_read_only_fn = is_read_only_fn
        self._check_permissions_fn = check_permissions_fn

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> type[BaseModel]:
        return self._input_schema

    async def call(self, input: BaseModel, context: ToolContext) -> ToolResult:
        return await self._call_fn(input, context)

    def is_concurrency_safe(self) -> bool:
        if self._is_concurrency_safe_fn:
            return self._is_concurrency_safe_fn()
        return False

    def is_read_only(self) -> bool:
        if self._is_read_only_fn:
            return self._is_read_only_fn()
        return False

    async def check_permissions(
        self,
        input: BaseModel,
        context: ToolContext
    ) -> PermissionCheckResult:
        if self._check_permissions_fn:
            return await self._check_permissions_fn(input, context)
        return PermissionCheckResult(allowed=True)


def build_tool(
    name: str,
    description: str,
    input_schema: type[BaseModel],
    call_fn: Callable[[BaseModel, ToolContext], Awaitable[ToolResult]],
    is_concurrency_safe: bool = False,
    is_read_only: bool = False,
    check_permissions_fn: Callable[[BaseModel, ToolContext], Awaitable[PermissionCheckResult]] | None = None,
) -> Tool:
    """构建工具的便捷函数

    Args:
        name: 工具名称
        description: 工具描述
        input_schema: 输入 Schema（Pydantic 模型类）
        call_fn: 异步执行函数，接收 (input, context) 返回 ToolResult
        is_concurrency_safe: 是否并发安全
        is_read_only: 是否只读
        check_permissions_fn: 可选的权限检查函数

    Returns:
        Tool 实例

    Example:
        ```python
        from pydantic import BaseModel

        class WeatherInput(BaseModel):
            city: str

        async def get_weather(input: WeatherInput, ctx: ToolContext) -> ToolResult:
            return ToolResult(content=f"Weather in {input.city}: sunny")

        weather_tool = build_tool(
            name="GetWeather",
            description="Get current weather",
            input_schema=WeatherInput,
            call_fn=get_weather,
            is_read_only=True,
        )
        ```
    """
    return FunctionalTool(
        name=name,
        description=description,
        input_schema=input_schema,
        call_fn=call_fn,
        is_concurrency_safe_fn=lambda: is_concurrency_safe,
        is_read_only_fn=lambda: is_read_only,
        check_permissions_fn=check_permissions_fn,
    )