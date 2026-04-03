"""权限类型定义"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import re


# 权限模式类型
PermissionMode = Literal[
    "default",              # 默认：需要用户确认
    "plan",                 # 计划模式
    "accept_edits",         # 接受编辑（自动允许文件修改）
    "bypass_permissions",   # 完全跳过权限检查
    "dont_ask",             # 不询问（自动拒绝）
    "auto",                 # AI 自动分类
]


@dataclass
class PermissionRule:
    """权限规则"""
    type: Literal["allow", "deny", "ask"]
    tool_name: str
    pattern: str | None = None
    description: str | None = None


@dataclass
class PermissionCheck:
    """权限检查结果"""
    allowed: bool
    requires_confirmation: bool
    reason: str | None = None
    mode: PermissionMode = "default"


def parse_permission_rule(value: str) -> tuple[str, str | None]:
    """解析权限规则字符串

    将 "Bash(git *)" 格式解析为 (tool_name, rule_content)

    Args:
        value: 权限规则字符串

    Returns:
        (工具名称, 规则内容) 元组
    """
    match = re.match(r"^(\w+)(?:\((.*)\))?$", value)
    if match:
        return match.group(1), match.group(2)
    return value, None