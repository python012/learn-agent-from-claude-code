"""多 Agent 协作示例

演示如何创建多个 Agent 并让它们协作完成复杂任务。

场景：一个 Agent 负责规划，一个 Agent 负责编码，一个 Agent 负责审查代码。
每个 Agent 通过第一个消息中的角色设定来区分职责。
"""

import asyncio
import os
import sys
from typing import List

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent import Agent, AgentConfig, AgentResult
from src.tools import get_builtin_tools


# 角色设定模板
ROLE_PROMPTS = {
    "规划师": """你是一位经验丰富的技术规划师。你的任务是：
1. 分析用户需求
2. 设计项目结构和技术方案
3. 列出需要创建的文件清单

请用简洁的格式输出，便于后续 Agent 执行。""",

    "程序员": """你是一位高效的程序员。你的任务是：
1. 根据规划设计创建代码文件
2. 编写高质量、可运行的代码
3. 添加必要的注释和文档

请专注于实现功能，代码要简洁清晰。""",

    "审查员": """你是一位严格的代码审查员。你的任务是：
1. 检查代码质量和潜在问题
2. 提出改进建议
3. 确保代码符合最佳实践

请给出具体的修改意见，如果有严重问题要指出来。""",
}


class MultiAgentCoordinator:
    """多 Agent 协调器"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """初始化协调器

        Args:
            api_key: OpenAI API 密钥
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.model = model
        self.agents: dict[str, Agent] = {}
        self.results: dict[str, AgentResult] = {}

    def create_agent(self, name: str) -> Agent:
        """创建一个具有特定角色的 Agent

        Args:
            name: Agent 名称（必须是预定义的角色名）

        Returns:
            创建好的 Agent 实例
        """
        if name not in ROLE_PROMPTS:
            raise ValueError(f"未知角色：{name}。可用角色：{list(ROLE_PROMPTS.keys())}")

        config = AgentConfig(
            cwd=os.getcwd(),
            api_key=self.api_key,
            model=self.model,
            max_tokens=4096,
            permission_mode="bypass_permissions",
        )
        agent = Agent(config)
        agent.register_tools(get_builtin_tools())
        self.agents[name] = agent

        # 首先发送角色设定消息
        agent.add_user_message(f"从现在开始，请你扮演以下角色：\n\n{ROLE_PROMPTS[name]}")

        print(f"[协调器] 创建了 Agent: {name}")
        return agent

    async def run_agent(self, name: str, task: str) -> str:
        """运行指定的 Agent

        Args:
            name: Agent 名称
            task: 任务描述

        Returns:
            Agent 回复的主要内容
        """
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")

        agent = self.agents[name]
        agent.add_user_message(task)

        print(f"\n[协调器] 正在运行 {name}: {task[:50]}...")
        result = await agent.run()
        self.results[name] = result

        # 获取最后一条助手消息
        last_assistant_msg = None
        for msg in reversed(result.messages):
            if msg.type == "assistant" and msg.message.content:
                last_assistant_msg = msg.message.content
                break

        return last_assistant_msg or "No response"

    def get_context(self, agent_names: List[str], max_length: int = 1000) -> str:
        """获取多个 Agent 的执行上下文

        Args:
            agent_names: Agent 名称列表
            max_length: 每个结果的最大长度

        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        for name in agent_names:
            if name in self.results:
                result = self.results[name]
                content = ""
                for msg in reversed(result.messages):
                    if msg.type == "assistant" and msg.message.content:
                        content = msg.message.content
                        break

                if content:
                    context_parts.append(f"=== {name} 的执行结果 ===\n{content[:max_length]}")

        return "\n\n".join(context_parts)


async def main() -> None:
    """主函数 - 多 Agent 协作完成代码项目"""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("错误：请设置 OPENAI_API_KEY 环境变量")
        print("export OPENAI_API_KEY=your-api-key-here")
        return

    print("=" * 60)
    print("多 Agent 协作示例 - 代码项目生成")
    print("=" * 60)

    # 创建协调器
    coordinator = MultiAgentCoordinator(api_key)

    # 创建三个不同角色的 Agent
    planner = coordinator.create_agent("规划师")
    coder = coordinator.create_agent("程序员")
    reviewer = coordinator.create_agent("审查员")

    # 用户任务
    user_task = "创建一个 Python 命令行待办事项管理器，支持添加、删除、列表显示和标记完成功能"

    print(f"\n用户任务：{user_task}")
    print("\n" + "=" * 60)

    # 第 1 步：规划师设计
    print("\n[第 1 步] 规划师进行设计...")
    planner_result = await coordinator.run_agent(
        "规划师",
        f"请为以下任务设计项目结构和实现方案：\n{user_task}"
    )
    print(f"规划结果:\n{planner_result}")

    # 第 2 步：程序员编码（使用规划结果作为上下文）
    print("\n" + "=" * 60)
    print("[第 2 步] 程序员开始编码...")
    coder_result = await coordinator.run_agent(
        "程序员",
        f"请根据以下规划实现代码：\n\n{planner_result}\n\n请创建所有必要的文件。"
    )
    print(f"代码实现:\n{coder_result}")

    # 第 3 步：审查员审查（使用规划和编码结果作为上下文）
    print("\n" + "=" * 60)
    print("[第 3 步] 审查员审查代码...")
    context = coordinator.get_context(["规划师", "程序员"])
    reviewer_result = await coordinator.run_agent(
        "审查员",
        f"请审查以下项目的代码质量：\n\n{context}\n\n请指出问题和改进建议。"
    )
    print(f"审查结果:\n{reviewer_result}")

    # 总结
    print("\n" + "=" * 60)
    print("多 Agent 协作完成!")
    print("=" * 60)

    planner_result_data = coordinator.results.get("规划师")
    coder_result_data = coordinator.results.get("程序员")
    reviewer_result_data = coordinator.results.get("审查员")

    if planner_result_data:
        tu = planner_result_data.token_usage
        print(f"规划师 token 数：{tu['input_tokens'] + tu['output_tokens']}")
    if coder_result_data:
        tu = coder_result_data.token_usage
        print(f"程序员 token 数：{tu['input_tokens'] + tu['output_tokens']}")
    if reviewer_result_data:
        tu = reviewer_result_data.token_usage
        print(f"审查员 token 数：{tu['input_tokens'] + tu['output_tokens']}")


if __name__ == "__main__":
    asyncio.run(main())
