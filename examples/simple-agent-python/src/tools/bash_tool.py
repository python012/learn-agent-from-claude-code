"""Bash 工具实现"""

from __future__ import annotations

import asyncio
import re
from pydantic import BaseModel, Field

from src.tools.base import Tool, ToolResult, ToolContext, FunctionalTool


class BashInput(BaseModel):
    """Bash 工具输入参数"""
    command: str = Field(description="要执行的 bash 命令")
    description: str | None = Field(default=None, description="执行此命令的原因")


# 危险命令模式列表
_DANGEROUS_PATTERNS = [
    r"rm\s+(-[rf]+\s+)?/",      # rm -rf /
    r"curl.*\|\s*(bash|sh)",    # curl | bash
    r"wget.*\|\s*(bash|sh)",    # wget | bash
    r":\(\)\{",                  # fork bomb
]


async def _execute_bash(input: BashInput, context: ToolContext) -> ToolResult:
    """执行 bash 命令

    Args:
        input: Bash 输入参数
        context: 工具执行上下文

    Returns:
        工具执行结果
    """
    command = input.command

    # 安全检查：拦截危险命令
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return ToolResult(
                content=f"Command blocked for security: {command}",
                is_error=True,
                metadata={"blocked": True, "reason": "dangerous_command"}
            )

    try:
        # 异步执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=context.cwd,
        )

        # 设置超时
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=60.0
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        result = stdout or stderr or "(no output)"

        return ToolResult(
            content=result,
            is_error=process.returncode != 0,
            metadata={
                "exit_code": process.returncode,
                "command_length": len(command),
            }
        )

    except asyncio.TimeoutError:
        return ToolResult(
            content=f"Command timed out after 60 seconds: {command}",
            is_error=True,
            metadata={"timeout": True}
        )
    except Exception as e:
        return ToolResult(
            content=f"Error executing command: {str(e)}",
            is_error=True,
            metadata={"error": str(e)}
        )


def BashTool() -> Tool:
    """创建 Bash 工具实例"""
    return FunctionalTool(
        name="Bash",
        description="Execute bash commands in the terminal",
        input_schema=BashInput,
        call_fn=_execute_bash,
        is_concurrency_safe_fn=lambda: False,
        is_read_only_fn=lambda: False,
    )