# FastMCP工具输出格式指南

## 概述

本文档说明FastMCP工具的输出格式设计原则，确保SSH命令输出与本地执行完全一致。

## 设计原则

### 核心理念：原始输出优先

> **"有什么内容返回什么内容"** - 不添加额外格式包装，不定义复杂schema

SSH命令的核心价值在于提供与本地执行完全一致的体验。因此，我们的工具输出应该：

- ✅ 直接返回原始命令输出
- ✅ 保持原始格式（包括换行、空格、颜色码等）
- ✅ 简化错误消息格式
- ❌ 避免JSON包装
- ❌ 避免复杂的结构化schema

## FastMCP返回类型注解机制

### 关键发现

FastMCP根据函数的返回类型注解决定输出格式：

```python
# ❌ 有返回类型注解 - 会尝试创建结构化内容
@mcp.tool
def command() -> str:
    return "ls -la"
# 结果：{"result": "ls -la"} + TextContent

# ✅ 无返回类型注解 - 纯文本输出
@mcp.tool
def command():
    return "ls -la"
# 结果：仅 TextContent("ls -la")
```

### 自动包装规则

1. **有返回类型注解**：

   - `-> str`: 包装为 `{"result": "内容"}`
   - `-> dict`: 直接作为结构化内容
   - `-> list`: 包装为 `{"result": [...]}`

1. **无返回类型注解**：

   - 任何返回值：仅生成TextContent
   - 无结构化内容（structured_content=None）

## 实现方案

### 工具函数签名

```python
@mcp.tool("execute-command")
async def execute_command(
    cmdString: str,
    connectionName: str | None = None
):  # 注意：无返回类型注解
    """执行SSH命令"""
    try:
        result = await ssh_manager.execute_command(cmdString, connectionName)
        return result.strip() if result else ""
    except Exception as error:
        return f"Error: {str(error)}"
```

### 输出示例

**命令执行成功**：

```
$ ls -la
total 16
drwxr-xr-x 2 user user 4096 Aug  5 15:00 .
drwxr-xr-x 3 user user 4096 Aug  5 14:00 ..
-rw-r--r-- 1 user user  123 Aug  5 14:30 file.txt
```

**命令执行失败**：

```
Error: command not found: invalidcmd
```

**连接错误**：

```
Error: SSH connection [server1] failed: Permission denied
```

## 优势

### 1. 用户体验一致性

- SSH工具输出与本地终端完全一致
- 无需学习特殊格式或解析JSON
- 支持复制粘贴到本地终端重新执行

### 2. 技术实现简洁

- 避免FastMCP结构化内容的版本兼容性问题
- 减少错误处理复杂性
- 更好的性能（无JSON序列化开销）

### 3. 工具集成友好

- LLM可直接理解原始命令输出
- 支持现有脚本和工具链
- 便于调试和日志分析

## 与TypeScript版本兼容性

保持与原TypeScript实现的接口兼容：

- 相同的工具名称和参数
- 相同的错误消息格式
- 相同的输出内容（但格式更简洁）

## 最佳实践

1. **始终移除返回类型注解**
1. **返回原始字符串内容**
1. **使用简单的错误格式：`"Error: 描述"`**
1. **保持输出的可读性和可复制性**

## 注意事项

- 这种方法特定于FastMCP 2.11.1+的行为
- 如果FastMCP更新其包装逻辑，可能需要调整
- 测试时确保 `structured_content=None`
