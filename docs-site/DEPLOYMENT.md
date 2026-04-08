# 部署文档到 GitHub Pages 指南

本文档说明如何将本项目的文档发布到 GitHub Pages。

## 前提条件

1. **GitHub 仓库设置**
   - 确认仓库为 `python012/learn-agent-from-claude-code`
   - 你具有管理员或写入权限

2. **启用 GitHub Pages**
   - 进入仓库 Settings → Pages
   - Source 选择 "GitHub Actions"

## 部署方式

### 方式 1：自动部署（推荐）

已配置 GitHub Actions 工作流，当满足以下条件时自动部署：

- 推送到 `main` 分支
- 修改了 `docs-site/` 目录或 `mkdocs.yml`

**触发部署：**
```bash
# 提交并推送更改
git add .
git commit -m "docs: 更新文档"
git push origin main
```

之后可以在 Actions 标签页查看部署进度。

### 方式 2：手动部署

```bash
# 1. 安装 MkDocs 依赖
pip install mkdocs mkdocs-material

# 2. 构建站点
mkdocs build

# 3. 部署到 GitHub Pages
mkdocs gh-deploy --remote-repository git@github.com:python012/learn-agent-from-claude-code.git
```

## 访问文档

部署成功后，文档可通过以下地址访问：

```
https://python012.github.io/learn-agent-from-claude-code/
```

## 自定义域名（可选）

如果想使用自定义域名：

1. 在仓库 Settings → Pages → Custom domain 中输入域名
2. 在域名 DNS 提供商处添加 CNAME 记录

## 故障排除

### 部署失败

1. 检查 Actions 日志
2. 确认 `mkdocs.yml` 语法正确
3. 确认所有导航链接指向的文件存在

### 本地构建测试

在推送前建议本地测试：

```bash
# 严格模式构建（检测错误）
mkdocs build --strict

# 本地预览
mkdocs serve
```

### 中文搜索不工作

确保安装了最新版 `mkdocs-material`：

```bash
pip install --upgrade mkdocs-material
```

## 文件结构

```
learn-agent-from-claude-code/
├── docs-site/                 # 文档源文件
│   ├── README.md              # 文档首页
│   └── agent-learning-guide/  # 学习指南目录
├── mkdocs.yml                 # MkDocs 配置
└── .github/workflows/
    └── deploy-docs.yml        # 部署工作流
```

## 更新文档后

每次修改文档后：

1. 本地预览确认无误：`mkdocs serve`
2. 提交更改并推送
3. GitHub Actions 自动部署
4. 约 1-2 分钟后访问网站查看更新

## 参考资源

- [MkDocs 官方文档](https://www.mkdocs.org/)
- [Material for MkDocs 主题](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages 文档](https://pages.github.com/)
