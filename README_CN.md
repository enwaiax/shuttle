<div align="center">

# 🚀 Shuttle

**面向 AI 助手的安全 SSH 网关**

[![CI](https://img.shields.io/github/actions/workflow/status/enwaiax/shuttle/test.yml?style=flat-square&label=CI)](https://github.com/enwaiax/shuttle/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/shuttle-mcp?style=flat-square&color=76B900)](https://pypi.org/project/shuttle-mcp)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Docs](https://img.shields.io/badge/docs-enwaiax.github.io%2Fshuttle-76B900?style=flat-square)](https://enwaiax.github.io/shuttle/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

Shuttle 让 AI 助手（Claude Code、Cursor 等）安全地在你的远程 SSH 服务器上执行命令 — 支持连接池、会话隔离、命令安全规则和 Web 审计面板。

[快速开始](#快速开始) · [MCP 工具](#mcp-工具) · [Web 面板](#web-面板) · [安全规则](#安全规则) · [文档](https://enwaiax.github.io/shuttle/) · [English](README.md)

</div>

---

## 为什么选择 Shuttle？

当 AI 编程助手需要操作远程服务器（在 GPU 机器上跑训练、部署到 staging、查看日志）时，它需要一个安全的桥梁。Shuttle 提供：

- **🔐 4 级命令安全** — 阻止危险命令、确认高风险命令、警告安装命令、放行其余
- **🔄 连接池** — SSH 连接复用，避免重复握手
- **📦 会话隔离** — 每个 AI 对话拥有独立的工作目录上下文
- **🌐 Web 审计面板** — 查看 AI 在每台服务器上执行的每条命令及完整输出
- **🛡️ 节点级规则** — 生产服务器和开发服务器可以有不同的安全策略
- **⚡ 跳板机支持** — 通过 Jump Host 连接内网服务器

## 快速开始

### 1. 安装

```bash
# 推荐：用 uv 安装 CLI 一次（可执行文件在 PATH）
uv tool install shuttle-mcp
shuttle --help

# 或不安装，单次运行（stdio）
uvx shuttle-mcp --help

# 旧版 PyPI 若没有 `shuttle-mcp` 入口：uvx --from shuttle-mcp shuttle --help
```

### 2. 添加第一个节点

```bash
shuttle node add
# 按提示输入：名称、主机、用户名、密码/密钥
```

### 3. 连接 AI 助手

**Claude Code / Cursor（stdio 模式）：**

```json
// .mcp.json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"]
    }
  }
}
```

**Service 模式（带 Web UI）：**

```bash
# 启动服务
shuttle serve

# 然后用 URL 配置 AI 客户端
```

```json
// .mcp.json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

就这样。你的 AI 助手现在可以在远程服务器上执行命令了。

## 两种运行模式

| 模式 | 命令 | MCP 传输 | Web UI | 适用场景 |
|------|------|---------|--------|---------|
| **CLI** | `shuttle` | stdio | ❌ | 快速使用，AI 客户端管理生命周期 |
| **Service** | `shuttle serve` | streamable-http | ✅ http://localhost:9876 | 审计日志、管理规则、云端部署 |

两种模式共享同一个 SQLite 数据库 — CLI 模式记录的命令，在 Service 模式的 Web UI 中同样可见。

## MCP 工具

AI 助手自动获得以下工具：

| 工具 | 说明 |
|------|------|
| `ssh_execute` | 在远程节点上执行命令 |
| `ssh_upload` | 通过 SFTP 上传文件 |
| `ssh_download` | 通过 SFTP 下载文件 |
| `ssh_list_nodes` | 列出所有配置的节点 |
| `ssh_add_node` | 添加新的 SSH 节点 |
| `ssh_remove_node` | 删除节点 |
| `ssh_session_start` | 开始有状态会话（保持工作目录） |
| `ssh_session_end` | 结束会话 |
| `ssh_session_list` | 列出活跃会话 |

### 对话示例

```
你：查一下训练服务器的 GPU 使用情况
AI：→ ssh_execute(node="gpu-server", command="nvidia-smi")
AI：你的 GPU 服务器有 7 块 A100-80GB，全部空闲，利用率 0%。

你：开始训练
AI：→ ssh_session_start(node="gpu-server")
AI：→ ssh_execute(session_id="abc123", command="cd /workspace && python train.py")
AI：训练已启动。Epoch 1/10...
```

## 安全规则

命令通过 4 级安全系统进行评估：

| 级别 | 行为 | 示例 |
|------|------|------|
| 🔴 **block** | 立即拒绝 | `rm -rf /`、`mkfs`、fork 炸弹 |
| 🟡 **confirm** | 需要用户确认 | `sudo`、`rm -rf`、`shutdown` |
| 🟠 **warn** | 执行但记录警告 | `apt install`、`pip install` |
| 🟢 **allow** | 正常执行 | 其他所有命令 |

首次启动时自动生成默认规则。可通过 Web UI 或数据库自定义。

### 节点级覆盖

不同服务器可以有不同规则：

```
全局：sudo .* → confirm（需确认）
GPU 服务器：sudo .* → allow（信任环境，无需确认）
生产服务器：DROP TABLE → block（额外保护）
```

## Web 面板

运行 `shuttle serve` 后打开 `http://localhost:9876`：

- **Overview** — 节点卡片概览，快速统计
- **Activity** — 按节点查看命令日志（终端风格，含 stdout/stderr）
- **Security Rules** — 管理全局默认规则和节点级覆盖
- **Settings** — 连接池和清理策略配置

Web UI 需要 Bearer Token 认证（运行 `shuttle serve` 时会显示 token）。

## CLI 命令参考

```bash
# MCP 服务
shuttle                      # 启动 MCP 服务（stdio 模式）
shuttle serve                # 启动 Service 模式（MCP + Web）
shuttle serve --port 8080    # 自定义端口
shuttle serve --host 0.0.0.0 # 绑定所有网卡（云端部署）
shuttle serve --db-url <url> # 自定义数据库

# 节点管理
shuttle node add             # 交互式添加节点
shuttle node list            # 列出所有节点
shuttle node test <name>     # 测试 SSH 连接
shuttle node edit <name>     # 编辑节点
shuttle node remove <name>   # 删除节点

# 配置
shuttle config show          # 显示当前配置
```

## 配置项

所有配置均可通过环境变量覆盖（前缀 `SHUTTLE_`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SHUTTLE_DB_URL` | `sqlite+aiosqlite:///~/.shuttle/shuttle.db` | 数据库 URL |
| `SHUTTLE_WEB_PORT` | `9876` | Web 面板端口 |
| `SHUTTLE_POOL_MAX_TOTAL` | `50` | 最大 SSH 连接总数 |
| `SHUTTLE_POOL_MAX_PER_NODE` | `5` | 每节点最大连接数 |
| `SHUTTLE_POOL_IDLE_TIMEOUT` | `300` | 空闲连接超时（秒） |

### 使用 PostgreSQL

```bash
SHUTTLE_DB_URL=postgresql+asyncpg://user:pass@host:5432/shuttle shuttle serve
```

需要额外安装驱动：`uv pip install asyncpg`（或在本项目中 `uv add asyncpg`）

## 开发

```bash
# 克隆并安装
git clone https://github.com/enwaiax/shuttle.git
cd shuttle
uv sync

# 运行测试
uv run pytest tests/ -v

# 代码检查
uv run ruff check src/ tests/

# 前端开发（热更新）
cd web && npm install && npm run dev
# 后端：uv run shuttle serve（另一个终端）
```

## 架构

```
开发者 ↔ AI 助手 ↔ Shuttle (MCP) ↔ SSH ↔ 远程服务器
                        │
              ┌─────────┴──────────┐
              │     核心引擎        │
              │  ├ 连接池           │
              │  ├ 会话管理器       │
              │  ├ 命令安全守卫     │
              │  └ SQLAlchemy ORM  │
              └────────────────────┘
```

**Service 模式：** 单个 ASGI 应用，在同一端口同时提供 MCP（`/mcp/`）和 Web UI（`/`）。

## 许可证

[MIT](LICENSE)

---

<div align="center">
  <sub>为让 AI 帮你 SSH 而生。</sub>
</div>
