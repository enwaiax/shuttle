# FastMCP SSH工具最佳实践示例

这个目录展示了如何使用FastMCP最佳实践实现SSH MCP工具。

## 文件说明

- `ssh_tools_optimized.py` - 优化的工具实现
- `server_optimized.py` - 优化的服务器实现
- `README.md` - 本说明文件

## 主要特性

### 1. 直接装饰器模式

```python
# ✅ 使用直接装饰器模式
@mcp.tool(name="execute-command", ...)
async def execute_command(...):
    pass
```

### 2. Context依赖注入

```python
# ✅ 使用Context依赖注入
async def execute_command(cmdString: str, ctx: Context = None):
    if ctx:
        await ctx.info(f"Executing: {cmdString}")

# ❌ 旧方式：闭包依赖
def register_tool(mcp, ssh_manager):  # ssh_manager通过闭包传递
    async def execute_command(cmdString: str):
        pass
```

### 3. 丰富的工具元数据

```python
# ✅ 新方式：完整元数据
@mcp.tool(
    annotations=ToolAnnotations(
        title="SSH Command Executor",
        readOnlyHint=False,
        destructiveHint=True
    ),
    tags={"ssh", "remote", "command"},
    meta={"version": "2.0", "category": "remote-execution"}
)
```

### 4. 结构化日志和进度报告

```python
# ✅ 新方式：结构化日志
await ctx.info("Command executed", extra={
    "command": cmdString,
    "connection": connectionName,
    "duration": execution_time
})

await ctx.report_progress(50, 100, "Processing...")
```

## 使用方法

```python
from ssh_tools_optimized import mcp, initialize_server

# 初始化服务器
server = await initialize_server(ssh_configs)

# 运行服务器（工具自动注册）
await server.run()
```

## 优势对比

| 特性       | 当前实现 | 最佳实践 |
| ---------- | -------- | -------- |
| 代码行数   | 多       | 少50%    |
| 注册方式   | 手动     | 自动     |
| 日志记录   | 无       | 结构化   |
| 进度报告   | 无       | 支持     |
| 工具元数据 | 基础     | 丰富     |
| 错误处理   | 简单     | 详细     |
| 维护性     | 复杂     | 简单     |

## 迁移建议

1. **创建优化版本**：先创建基于最佳实践的新版本
1. **功能测试**：确保所有功能正常工作
1. **逐步替换**：逐个替换现有工具
1. **清理代码**：移除旧的注册函数

这种方法能显著提升代码质量、可维护性和调试体验。
