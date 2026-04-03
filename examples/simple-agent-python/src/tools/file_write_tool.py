"""文件写入工具实现"""

from __future__ import annotations

import os
import re
from pathlib import Path
from pydantic import BaseModel, Field

from src.tools.base import Tool, ToolResult, ToolContext, FunctionalTool


class FileWriteInput(BaseModel):
    """文件写入工具输入参数"""
    path: str = Field(description="要写入的文件路径（绝对或相对）")
    content: str = Field(description="要写入的内容")
    description: str | None = Field(default=None, description="写入此文件的原因")


# 敏感文件模式列表
_SENSITIVE_PATTERNS = [
    r"\.env$",
    r"package\.json$",
    r"pyproject\.toml$",
    r"\.git[\\/]config$",
]


async def _write_file(input: FileWriteInput, context: ToolContext) -> ToolResult:
    """写入文件内容

    Args:
        input: 文件写入输入参数
        context: 工具执行上下文

    Returns:
        工具执行结果
    """
    input_path = input.path
    content = input.content

    # 解析路径
    cwd_path = Path(context.cwd).resolve()
    if os.path.isabs(input_path):
        resolved_path = Path(input_path)
    else:
        resolved_path = (cwd_path / input_path).resolve()

    # 安全检查：防止路径遍历攻击
    try:
        resolved_path.relative_to(cwd_path)
    except ValueError:
        return ToolResult(
            content=f"Access denied: Path {input_path} is outside working directory",
            is_error=True,
            metadata={"blocked": True, "reason": "path_traversal"}
        )

    # 安全检查：敏感文件保护
    path_str = str(resolved_path)
    for pattern in _SENSITIVE_PATTERNS:
        if re.search(pattern, path_str):
            return ToolResult(
                content=f"Writing to {resolved_path} requires explicit permission",
                is_error=True,
                metadata={"blocked": True, "reason": "sensitive_file"}
            )

    try:
        # 确保目录存在
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查文件是否已存在
        file_existed = resolved_path.exists()

        # 写入文件
        resolved_path.write_text(content, encoding="utf-8")

        return ToolResult(
            content=f"Successfully wrote {len(content)} bytes to {resolved_path}",
            is_error=False,
            metadata={
                "bytes_written": len(content.encode("utf-8")),
                "path": str(resolved_path),
                "created": not file_existed,
            }
        )

    except Exception as e:
        return ToolResult(
            content=f"Error writing file: {str(e)}",
            is_error=True,
            metadata={"error": str(e)}
        )


def FileWriteTool() -> Tool:
    """创建文件写入工具实例"""
    return FunctionalTool(
        name="FileWrite",
        description="Write content to a file (creates new file or overwrites existing)",
        input_schema=FileWriteInput,
        call_fn=_write_file,
        is_concurrency_safe_fn=lambda: False,
        is_read_only_fn=lambda: False,
    )