"""工具模块"""

from src.tools.base import Tool, ToolResult, ToolContext, build_tool
from src.tools.bash_tool import BashTool
from src.tools.file_read_tool import FileReadTool
from src.tools.file_write_tool import FileWriteTool

# 内置工具列表
_builtin_tools: list[Tool] | None = None


def get_builtin_tools() -> list[Tool]:
    """获取所有内置工具"""
    global _builtin_tools
    if _builtin_tools is None:
        _builtin_tools = [
            BashTool(),
            FileReadTool(),
            FileWriteTool(),
        ]
    return _builtin_tools


__all__ = [
    "Tool",
    "ToolResult",
    "ToolContext",
    "build_tool",
    "BashTool",
    "FileReadTool",
    "FileWriteTool",
    "get_builtin_tools",
]