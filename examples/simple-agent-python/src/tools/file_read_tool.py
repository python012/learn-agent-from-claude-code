"""文件读取工具实现"""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field

from src.tools.base import Tool, ToolResult, ToolContext, FunctionalTool


class FileReadInput(BaseModel):
    """文件读取工具输入参数"""
    path: str = Field(description="要读取的文件路径（绝对或相对）")
    description: str | None = Field(default=None, description="读取此文件的原因")


async def _read_file(input: FileReadInput, context: ToolContext) -> ToolResult:
    """读取文件内容

    Args:
        input: 文件读取输入参数
        context: 工具执行上下文

    Returns:
        工具执行结果
    """
    input_path = input.path

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

    # 检查文件是否存在
    if not resolved_path.exists():
        return ToolResult(
            content=f"File not found: {resolved_path}",
            is_error=True,
            metadata={"not_found": True}
        )

    # 检查是否为文件
    if not resolved_path.is_file():
        return ToolResult(
            content=f"Path is not a file: {resolved_path}",
            is_error=True,
            metadata={"not_a_file": True}
        )

    try:
        # 读取文件内容
        content = resolved_path.read_text(encoding="utf-8")

        # 限制返回行数
        max_lines = 2000
        lines = content.split("\n")
        if len(lines) > max_lines:
            truncated_content = "\n".join(lines[:max_lines])
            truncated_content += f"\n\n... ({len(lines) - max_lines} more lines)"
        else:
            truncated_content = content

        return ToolResult(
            content=truncated_content,
            is_error=False,
            metadata={
                "total_lines": len(lines),
                "file_size": len(content.encode("utf-8")),
                "path": str(resolved_path),
            }
        )

    except Exception as e:
        return ToolResult(
            content=f"Error reading file: {str(e)}",
            is_error=True,
            metadata={"error": str(e)}
        )


def FileReadTool() -> Tool:
    """创建文件读取工具实例"""
    return FunctionalTool(
        name="FileRead",
        description="Read content from a file",
        input_schema=FileReadInput,
        call_fn=_read_file,
        is_concurrency_safe_fn=lambda: True,   # 读取是并发安全的
        is_read_only_fn=lambda: True,          # 读取是只读操作
    )