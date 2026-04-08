# SimpleAgent Python

基于第 08 篇教程使用 Python 实现的轻量级 Agent 系统示例。

## 快速开始

### 1. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
pip install pytest pytest-asyncio  # 开发依赖
```

### 2. 无需 API Key 即可测试

```bash
# 运行 Mock 测试（无需 OpenAI API Key）
python examples/test_no_api_key.py

# 或运行单元测试
pytest tests/ -v
```

### 3. 使用真实 API

```bash
export OPENAI_API_KEY=your-api-key-here

# 基本用法
python examples/basic_usage.py

# 交互式 REPL
python examples/repl.py

# 自定义工具示例
python examples/custom_tool.py

# 多 Agent 协作示例
python examples/multi_agent_collaboration.py

# MCP 集成示例
python examples/mcp_integration.py
```

## 项目结构

```
simple-agent-python/
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py          # Agent 核心类
│   │   ├── llm_client.py     # OpenAI 客户端封装
│   │   └── types.py          # 类型定义
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py           # Tool 基类
│   │   ├── bash_tool.py      # Bash 工具
│   │   ├── file_read_tool.py # 文件读取工具
│   │   └── file_write_tool.py# 文件写入工具
│   ├── state/
│   │   ├── __init__.py
│   │   ├── store.py          # 状态管理
│   │   └── session.py        # 会话持久化
│   ├── permissions/
│   │   ├── __init__.py
│   │   ├── checker.py        # 权限检查
│   │   └── types.py          # 权限类型
│   └── __init__.py           # 统一导出
├── examples/
│   ├── basic_usage.py        # 基本用法
│   ├── repl.py               # 交互式 REPL
│   └── custom_tool.py        # 自定义工具
├── tests/
│   └── test_agent.py         # 测试文件
├── requirements.txt
└── README.md
```

## 核心功能

### 1. LLM 客户端

封装 OpenAI API，支持工具调用：

```python
from src.agent.llm_client import LLMClient

client = LLMClient(
    api_key="your-api-key",
    model="gpt-4o",
    max_tokens=4096,
)
```

### 2. Agent 核心

```python
from src.agent.agent import Agent
from src.tools import get_builtin_tools

agent = Agent(
    cwd=".",
    api_key="your-api-key",
    model="gpt-4o",
    max_tokens=4096,
    permission_mode="bypass_permissions",
)

agent.register_tools(get_builtin_tools())
agent.add_user_message("创建一个新的 Python 项目")
result = await agent.run()
```

### 3. 自定义工具

```python
from src.tools.base import Tool, ToolResult
from pydantic import BaseModel

class WeatherInput(BaseModel):
    city: str

async def get_weather(input: WeatherInput, context) -> ToolResult:
    return ToolResult(content=f"Weather in {input.city}: sunny, 25°C")

weather_tool = Tool(
    name="GetWeather",
    description="Get current weather for a city",
    input_schema=WeatherInput,
    is_read_only=True,
    call_fn=get_weather,
)
```

## 权限模式

| 模式 | 说明 |
|------|------|
| `default` | 默认：需要用户确认 |
| `bypass_permissions` | 跳过权限检查 |
| `dont_ask` | 自动拒绝 |
| `accept_edits` | 自动允许只读操作 |
| `auto` | AI 自动分类 |

## 测试

```bash
pytest tests/
```

## 学习资源

- [第 08 篇：实战构建自己的 Agent](../../docs-site/agent-learning-guide/08-build-your-own-agent.md)
- [系列总览](../../docs-site/agent-learning-guide/README.md)

## License

MIT