# 实战示例扩展

本目录包含两个额外的实战示例，展示更高级的 Agent 应用场景。

## 示例列表

### 1. 多 Agent 协作示例 (`multi_agent_collaboration.py` / `multi-agent.ts`)

演示如何创建多个具有不同角色的 Agent 并让它们协作完成复杂任务。

**场景**：
- **规划师**：分析需求并设计项目结构
- **程序员**：根据设计编写代码
- **审查员**：检查代码质量并提出改进建议

**核心概念**：
- 通过系统提示词定义 Agent 角色
- 协调器模式管理多个 Agent
- 传递上下文在 Agent 之间共享信息

**运行方式**：

```bash
# Python
export OPENAI_API_KEY=your-key
python examples/multi_agent_collaboration.py

# TypeScript
export OPENAI_API_KEY=your-key
npm run example:multi-agent
```

**输出示例**：
```
============================================================
多 Agent 协作示例 - 代码项目生成
============================================================

用户任务：创建一个 Python 命令行待办事项管理器

[第 1 步] 规划师进行设计...
规划结果:
项目结构:
- todo.py (主程序)
- storage.py (数据存储)
- README.md

[第 2 步] 程序员开始编码...
代码实现:
创建了以下文件:
- todo.py: 包含 Todo 类和命令行界面
- storage.py: JSON 文件存储实现

[第 3 步] 审查员审查代码...
审查结果:
代码质量良好，建议：
1. 添加类型注解
2. 增加单元测试
3. 添加错误处理
```

---

### 2. MCP 集成示例 (`mcp_integration.py`)

演示如何将 MCP (Model Context Protocol) 服务器集成到 Agent 中，扩展 Agent 的能力。

**场景**：
- 调用 GitHub MCP 工具搜索仓库
- 调用文件系统 MCP 工具读取文件
- 调用搜索 MCP 工具进行网络搜索

**核心概念**：
- MCP 协议基础
- 工具包装器模式
- 将外部服务转换为 Agent 可调用的工具

**运行方式**：

```bash
# Python
export OPENAI_API_KEY=your-key
python examples/mcp_integration.py
```

**MCP 服务器配置**：

实际使用时，在 `~/.claude/mcp.json` 配置：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"]
    },
    "serp": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-serp"]
    }
  }
}
```

**参考资源**：
- [MCP 官方仓库](https://github.com/modelcontextprotocol)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)

---

## 扩展阅读

- [第 07 篇：多 Agent 协作系统](../../docs-site/agent-learning-guide/07-multi-agent-collaboration-system.md)
- [第 06 篇：MCP 与外部集成](../../docs-site/agent-learning-guide/06-mcp-and-external-integration.md)

## 下一步

尝试修改这些示例：
1. 添加新的 Agent 角色（如测试员、文档员）
2. 连接真实的 MCP 服务器
3. 创建你自己的 MCP 工具包装器
