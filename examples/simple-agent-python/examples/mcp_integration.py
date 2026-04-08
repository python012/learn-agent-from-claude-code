"""MCP 集成示例

演示如何将 MCP (Model Context Protocol) 服务器集成到 Agent 中。

MCP 允许 Agent 调用外部工具和服务，如 GitHub、文件系统、数据库等。

本示例展示：
1. 如何配置 MCP 客户端
2. 如何调用 MCP 工具
3. 如何将 MCP 工具与内置工具结合使用
"""

import asyncio
import os
import sys
import json
from typing import Any

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent import Agent, AgentConfig
from src.tools import get_builtin_tools
from src.tools.base import Tool, ToolResult, ToolContext
from pydantic import BaseModel


# =============================================================================
# 模拟 MCP 工具 - 实际使用时应连接到真实的 MCP 服务器
# =============================================================================

class McpToolInput(BaseModel):
    """MCP 工具输入基类"""
    pass


async def call_mcp_server(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """调用 MCP 服务器工具

    实际使用时，这里应该：
    1. 通过 stdio 或 SSE 连接到 MCP 服务器
    2. 发送工具调用请求
    3. 等待响应并解析结果

    本示例使用模拟实现。

    Args:
        server_name: MCP 服务器名称
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    print(f"  [MCP] 调用 {server_name}/{tool_name}")
    print(f"  [MCP] 参数：{json.dumps(arguments, indent=2)}")

    # 模拟不同服务器的响应
    if server_name == "github":
        return await _mock_github_tool(tool_name, arguments)
    elif server_name == "filesystem":
        return await _mock_filesystem_tool(tool_name, arguments)
    elif server_name == "serp":
        return await _mock_search_tool(tool_name, arguments)
    else:
        return {
            "content": f"未知 MCP 服务器：{server_name}",
            "is_error": True,
        }


async def _mock_github_tool(tool_name: str, args: dict) -> dict:
    """模拟 GitHub MCP 工具"""
    if tool_name == "search_repositories":
        return {
            "content": json.dumps({
                "total_count": 2,
                "items": [
                    {"name": "learn-agent-from-claude-code", "full_name": "python012/learn-agent-from-claude-code", "stargazers_count": 100},
                    {"name": "simple-agent", "full_name": "python012/simple-agent", "stargazers_count": 50},
                ]
            }, ensure_ascii=False, indent=2),
            "is_error": False,
        }
    elif tool_name == "get_repository":
        return {
            "content": json.dumps({
                "name": args.get("repo", "unknown"),
                "description": "一个 Agent 学习项目",
                "language": "Python",
            }, ensure_ascii=False, indent=2),
            "is_error": False,
        }
    return {"content": f"Unknown GitHub tool: {tool_name}", "is_error": True}


async def _mock_filesystem_tool(tool_name: str, args: dict) -> dict:
    """模拟文件系统 MCP 工具"""
    if tool_name == "read_file":
        path = args.get("path", "unknown")
        return {
            "content": f"模拟读取文件：{path}\n这是文件内容示例...",
            "is_error": False,
        }
    elif tool_name == "list_directory":
        path = args.get("path", ".")
        return {
            "content": json.dumps(["src/", "docs/", "README.md", "requirements.txt"], indent=2),
            "is_error": False,
        }
    return {"content": f"Unknown filesystem tool: {tool_name}", "is_error": True}


async def _mock_search_tool(tool_name: str, args: dict) -> dict:
    """模拟搜索 MCP 工具"""
    if tool_name == "search":
        query = args.get("query", "")
        return {
            "content": json.dumps([
                {"title": f"搜索结果 1: {query}", "url": "https://example.com/1"},
                {"title": f"搜索结果 2: {query}", "url": "https://example.com/2"},
            ], ensure_ascii=False, indent=2),
            "is_error": False,
        }
    return {"content": f"Unknown search tool: {tool_name}", "is_error": True}


# =============================================================================
# MCP 工具包装器 - 将 MCP 工具转换为 Agent 可调用的 Tool
# =============================================================================

def create_mcp_tool(
    server_name: str,
    tool_name: str,
    description: str,
    input_schema: type[BaseModel],
) -> Tool:
    """创建 MCP 工具包装器

    Args:
        server_name: MCP 服务器名称
        tool_name: 工具名称
        description: 工具描述
        input_schema: 输入参数 Schema

    Returns:
        包装后的 Tool
    """

    async def call_fn(input: BaseModel, context: ToolContext) -> ToolResult:
        """调用 MCP 工具"""
        input_dict = input.model_dump()
        result = await call_mcp_server(server_name, tool_name, input_dict)
        return ToolResult(
            content=result["content"],
            is_error=result.get("is_error", False),
        )

    return Tool(
        name=f"{server_name}_{tool_name}",
        description=f"[MCP:{server_name}] {description}",
        input_schema=input_schema,
        is_read_only=True,
        is_concurrency_safe=True,
        call_fn=call_fn,
    )


# =============================================================================
# 定义 MCP 工具输入 Schema
# =============================================================================

class GitHubSearchInput(BaseModel):
    """GitHub 搜索输入"""
    query: str
    sort: str = "stars"
    order: str = "desc"


class GitHubRepoInput(BaseModel):
    """GitHub 仓库输入"""
    owner: str
    repo: str


class FileSystemReadInput(BaseModel):
    """文件系统读取输入"""
    path: str


class SearchInput(BaseModel):
    """搜索输入"""
    query: str
    num_results: int = 5


# =============================================================================
# 创建 MCP 工具集合
# =============================================================================

def get_mcp_tools() -> list[Tool]:
    """获取所有 MCP 工具"""
    return [
        # GitHub MCP 工具
        create_mcp_tool(
            "github",
            "search_repositories",
            "搜索 GitHub 仓库",
            GitHubSearchInput,
        ),
        create_mcp_tool(
            "github",
            "get_repository",
            "获取仓库详情",
            GitHubRepoInput,
        ),
        # 文件系统 MCP 工具
        create_mcp_tool(
            "filesystem",
            "read_file",
            "读取文件内容",
            FileSystemReadInput,
        ),
        create_mcp_tool(
            "filesystem",
            "list_directory",
            "列出目录内容",
            FileSystemReadInput,
        ),
        # 搜索 MCP 工具
        create_mcp_tool(
            "serp",
            "search",
            "网络搜索",
            SearchInput,
        ),
    ]


# =============================================================================
# 主函数 - 演示 MCP 工具使用
# =============================================================================

async def main() -> None:
    """主函数 - 演示 MCP 工具集成"""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("提示：请设置 OPENAI_API_KEY 环境变量以使用真实 Agent")
        print("export OPENAI_API_KEY=your-api-key-here")
        print("\n按 Enter 继续（使用 Mock 模式）...")
        input()

    print("=" * 60)
    print("MCP 集成示例 - 调用外部工具")
    print("=" * 60)

    # 创建 Agent
    config = AgentConfig(
        cwd=os.getcwd(),
        api_key=api_key or "mock-key",
        model="gpt-4o",
        max_tokens=4096,
        permission_mode="bypass_permissions",
    )

    agent = Agent(config)

    # 注册内置工具和 MCP 工具
    builtin_tools = get_builtin_tools()
    mcp_tools = get_mcp_tools()

    print(f"\n注册工具:")
    print(f"  内置工具：{len(builtin_tools)} 个")
    print(f"  MCP 工具：{len(mcp_tools)} 个")

    agent.register_tools(builtin_tools + mcp_tools)

    # 演示任务
    tasks = [
        "搜索 GitHub 上与 'agent' 相关的热门仓库，列出前 5 个",
        "读取当前目录下的 README.md 文件",
        "搜索关于 'AI Agent 开发' 的最新信息",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n{'=' * 60}")
        print(f"[任务 {i}] {task}")
        print("=" * 60)

        agent.add_user_message(task)

        if api_key:
            result = await agent.run()
            print(f"\nToken 使用：{result.token_usage['input_tokens']} input, {result.token_usage['output_tokens']} output")
        else:
            print("\n[Mock 模式] 跳过实际执行")
            print("设置 OPENAI_API_KEY 后可以看到完整输出")

    print("\n" + "=" * 60)
    print("MCP 集成示例完成!")
    print("=" * 60)
    print("""
实际使用时，你需要：
1. 安装 MCP 服务器（如 @modelcontextprotocol/server-github）
2. 配置 MCP 连接（stdio 或 SSE）
3. 将模拟函数替换为真实的 MCP 调用

参考：https://github.com/modelcontextprotocol/servers
""")


if __name__ == "__main__":
    asyncio.run(main())
