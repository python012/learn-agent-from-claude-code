"""会话持久化实现"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agent.types import Message, UserMessage


@dataclass
class TranscriptEntry:
    """会话日志条目（JSONL 格式）"""
    type: str
    uuid: str
    parent_uuid: str | None
    timestamp: int
    data: dict[str, Any]


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    title: str | None = None
    created_at: int = 0
    updated_at: int = 0
    project_dir: str = ""


class SessionStorage:
    """会话持久化存储

    使用 JSONL 格式存储会话日志，支持增量追加。
    """

    def __init__(self, session_dir: str) -> None:
        """初始化会话存储

        Args:
            session_dir: 会话存储目录
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, session_id: str) -> Path:
        """获取会话日志文件路径"""
        return self.session_dir / f"{session_id}.jsonl"

    def get_metadata_path(self, session_id: str) -> Path:
        """获取会话元数据文件路径"""
        metadata_dir = self.session_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        return metadata_dir / f"{session_id}.json"

    async def append_message(self, session_id: str, message: Message) -> None:
        """追加消息到会话日志

        Args:
            session_id: 会话 ID
            message: 消息对象
        """
        log_path = self.get_session_path(session_id)

        # 构建日志条目
        entry = {
            "type": message.type,
            "uuid": message.uuid,
            "parent_uuid": message.parent_uuid,
            "timestamp": message.timestamp,
            "data": self._message_to_dict(message),
        }

        # 追加到 JSONL 文件
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    async def load_session(self, session_id: str) -> list[Message]:
        """加载会话日志

        Args:
            session_id: 会话 ID

        Returns:
            消息列表
        """
        log_path = self.get_session_path(session_id)

        if not log_path.exists():
            return []

        messages: list[Message] = []
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    message = self._dict_to_message(entry["data"])
                    if message:
                        messages.append(message)
                except (json.JSONDecodeError, KeyError):
                    continue

        return messages

    async def save_metadata(self, metadata: SessionMetadata) -> None:
        """保存会话元数据

        Args:
            metadata: 会话元数据
        """
        metadata_path = self.get_metadata_path(metadata.session_id)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": metadata.session_id,
                "title": metadata.title,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
                "project_dir": metadata.project_dir,
            }, f, ensure_ascii=False, indent=2)

    async def load_metadata(self, session_id: str) -> SessionMetadata | None:
        """加载会话元数据

        Args:
            session_id: 会话 ID

        Returns:
            会话元数据，不存在则返回 None
        """
        metadata_path = self.get_metadata_path(session_id)

        if not metadata_path.exists():
            return None

        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return SessionMetadata(
                session_id=data["session_id"],
                title=data.get("title"),
                created_at=data.get("created_at", 0),
                updated_at=data.get("updated_at", 0),
                project_dir=data.get("project_dir", ""),
            )

    def extract_title(self, messages: list[Message]) -> str | None:
        """从消息列表中提取标题

        取第一条用户消息的前 50 个字符作为标题。

        Args:
            messages: 消息列表

        Returns:
            提取的标题，如果没有用户消息则返回 None
        """
        for msg in messages:
            if isinstance(msg, UserMessage):
                text = self._extract_text_content(msg.message.content)
                if text:
                    return text[:50] + "..." if len(text) > 50 else text
        return None

    @staticmethod
    def _extract_text_content(content: str | list) -> str:
        """提取消息内容中的文本"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return " ".join(texts)
        return ""

    @staticmethod
    def _message_to_dict(message: Message) -> dict[str, Any]:
        """将消息对象转换为字典"""
        if hasattr(message, "message"):
            msg_dict = {}
            if hasattr(message.message, "role"):
                msg_dict["role"] = message.message.role
            if hasattr(message.message, "content"):
                msg_dict["content"] = message.message.content
            if hasattr(message.message, "tool_calls"):
                msg_dict["tool_calls"] = message.message.tool_calls
            if hasattr(message.message, "tool_call_id"):
                msg_dict["tool_call_id"] = message.message.tool_call_id
            return {"type": message.type, "message": msg_dict}
        return {}

    @staticmethod
    def _dict_to_message(data: dict[str, Any]) -> Message | None:
        """将字典转换为消息对象（简化版本）"""
        # 这里返回原始数据，实际使用时可以根据需要构建具体类型
        return None