"""状态存储实现"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any
from uuid import uuid4

from src.agent.types import Message


@dataclass
class AppState:
    """应用状态

    包含会话的所有运行时状态。
    """
    session_id: str = field(default_factory=lambda: str(uuid4()))
    messages: list[Message] = field(default_factory=list)
    pending_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    is_processing: bool = False
    token_usage: dict[str, int] = field(default_factory=lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
    })


class StateStore:
    """状态存储

    实现简单的状态管理模式，支持订阅机制。
    """

    def __init__(self, initial_state: AppState | None = None) -> None:
        """初始化状态存储

        Args:
            initial_state: 初始状态，默认为新的 AppState
        """
        self._state = initial_state or AppState()
        self._listeners: list[Callable[[], None]] = []

    def get_state(self) -> AppState:
        """获取当前状态"""
        return self._state

    def set_state(self, updater: AppState | Callable[[AppState], AppState]) -> None:
        """更新状态

        Args:
            updater: 新状态或状态更新函数
        """
        old_state = self._state

        if callable(updater):
            new_state = updater(old_state)
        else:
            new_state = updater

        # 状态未变时不通知
        if old_state is new_state:
            return

        self._state = new_state

        # 通知所有监听器
        for listener in self._listeners:
            listener()

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """订阅状态变化

        Args:
            listener: 监听器函数

        Returns:
            取消订阅函数
        """
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe


def create_state_store(initial_state: AppState | None = None) -> StateStore:
    """创建状态存储的便捷函数

    Args:
        initial_state: 初始状态

    Returns:
        StateStore 实例
    """
    return StateStore(initial_state)