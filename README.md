# 参考 Claude Code 源代码学习 Agent 开发

[![GitHub Stars](https://img.shields.io/github/stars/python012/learn-agent-from-claude-code?style=flat-square&logo=github)](https://github.com/python012/learn-agent-from-claude-code/stargazers)
[![License](https://img.shields.io/github/license/python012/learn-agent-from-claude-code?style=flat-square&label=license)](LICENSE)

**在线阅读（最佳体验）：[python012.github.io/learn-agent-from-claude-code](https://python012.github.io/learn-agent-from-claude-code/)**

通过深入分析 Claude Code 源码，学习 AI Agent 开发。包含 9 篇循序渐进的教程，以及 TypeScript 和 Python 双版本的示例代码。

## 快速开始

**阅读教程** — 从[学习路线总览](https://python012.github.io/learn-agent-from-claude-code/agent-learning-guide/00-learning-roadmap/)开始

**运行示例** — 选择你熟悉的语言：

```bash
# TypeScript (examples/simple-agent/)
npm install && npm run example:basic

# Python (examples/simple-agent-python/)
pip install -r requirements.txt
python examples/basic_usage.py
```

> 示例需要设置 `OPENAI_API_KEY` 环境变量

## 仓库结构

| 目录 | 说明 |
|------|------|
| `docs-site/` | 教程文档（[在线阅读](https://python012.github.io/learn-agent-from-claude-code/)） |
| `examples/` | TypeScript 和 Python 版 SimpleAgent 示例代码 |
| `src/` | Claude Code 源码（只读参考，不可构建） |
| `AGENTS.md` | 从源码提取的代码风格指南 |

## License

MIT
