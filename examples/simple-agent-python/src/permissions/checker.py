"""权限检查器实现"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from src.tools.base import Tool, ToolContext
from src.permissions.types import PermissionMode, PermissionRule, PermissionCheck, parse_permission_rule


@dataclass
class PermissionChecker:
    """权限检查器

    负责检查工具调用是否有权限执行。
    """

    mode: PermissionMode = "default"
    allow_rules: list[PermissionRule] = field(default_factory=list)
    deny_rules: list[PermissionRule] = field(default_factory=list)
    ask_rules: list[PermissionRule] = field(default_factory=list)

    @classmethod
    def from_config(
        cls,
        mode: PermissionMode = "default",
        allow_rules: list[str] | None = None,
        deny_rules: list[str] | None = None,
        ask_rules: list[str] | None = None,
    ) -> "PermissionChecker":
        """从配置创建权限检查器

        Args:
            mode: 权限模式
            allow_rules: 允许规则字符串列表
            deny_rules: 拒绝规则字符串列表
            ask_rules: 询问规则字符串列表

        Returns:
            PermissionChecker 实例
        """
        return cls(
            mode=mode,
            allow_rules=cls._parse_rules(allow_rules or []),
            deny_rules=cls._parse_rules(deny_rules or []),
            ask_rules=cls._parse_rules(ask_rules or []),
        )

    @staticmethod
    def _parse_rules(rules: list[str]) -> list[PermissionRule]:
        """解析规则字符串列表"""
        result = []
        for rule_str in rules:
            tool_name, rule_content = parse_permission_rule(rule_str)
            result.append(PermissionRule(
                type="allow",  # 类型由调用方决定
                tool_name=tool_name,
                pattern=rule_content,
            ))
        return result

    async def check_permission(
        self,
        tool: Tool,
        input: dict,
        context: ToolContext,
    ) -> PermissionCheck:
        """检查工具调用权限

        Args:
            tool: 工具实例
            input: 工具输入参数
            context: 工具执行上下文

        Returns:
            PermissionCheck 权限检查结果
        """
        # 1. bypass_permissions 模式：总是允许
        if self.mode == "bypass_permissions":
            return PermissionCheck(
                allowed=True,
                requires_confirmation=False,
                reason="bypass_permissions mode",
                mode=self.mode,
            )

        # 2. dont_ask 模式：总是拒绝
        if self.mode == "dont_ask":
            return PermissionCheck(
                allowed=False,
                requires_confirmation=False,
                reason="dont_ask mode",
                mode=self.mode,
            )

        # 3. 检查拒绝规则
        if self._matches_rule(self.deny_rules, tool.name, input):
            return PermissionCheck(
                allowed=False,
                requires_confirmation=False,
                reason=f"Denied by rule: {tool.name}",
                mode=self.mode,
            )

        # 4. 检查允许规则
        if self._matches_rule(self.allow_rules, tool.name, input):
            return PermissionCheck(
                allowed=True,
                requires_confirmation=False,
                reason=f"Allowed by rule: {tool.name}",
                mode=self.mode,
            )

        # 5. 检查询问规则
        if self._matches_rule(self.ask_rules, tool.name, input):
            return PermissionCheck(
                allowed=False,
                requires_confirmation=True,
                reason=f"Requires confirmation: {tool.name}",
                mode=self.mode,
            )

        # 6. accept_edits 模式：只读工具自动允许
        if self.mode == "accept_edits" and tool.is_read_only():
            return PermissionCheck(
                allowed=True,
                requires_confirmation=False,
                reason="accept_edits mode + read-only tool",
                mode=self.mode,
            )

        # 7. auto 模式：根据工具类型决定
        if self.mode == "auto":
            return PermissionCheck(
                allowed=tool.is_read_only(),
                requires_confirmation=not tool.is_read_only(),
                reason="auto mode classification",
                mode=self.mode,
            )

        # 8. 默认：需要用户确认
        return PermissionCheck(
            allowed=False,
            requires_confirmation=True,
            reason="default: require user confirmation",
            mode=self.mode,
        )

    def _matches_rule(
        self,
        rules: list[PermissionRule],
        tool_name: str,
        input: dict,
    ) -> bool:
        """检查工具是否匹配规则"""
        for rule in rules:
            if rule.tool_name != tool_name:
                continue

            # 没有模式，直接匹配工具名
            if not rule.pattern:
                return True

            # 有模式，进行模式匹配
            input_str = json.dumps(input, ensure_ascii=False)
            if self._pattern_matches(rule.pattern, input_str):
                return True

        return False

    @staticmethod
    def _pattern_matches(pattern: str, input: str) -> bool:
        """检查输入是否匹配模式（支持通配符 *）"""
        # 转义正则特殊字符，但保留 * 作为通配符
        regex_pattern = re.escape(pattern).replace(r"\*", ".*")
        regex = re.compile(f"^{regex_pattern}$")
        return bool(regex.match(input))