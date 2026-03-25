# 🚀 SSH MCP Tools v2 Migration Guide

> ✅ **Migration Complete** - The v2 implementation is now the unified standard. This document is kept for historical reference and to understand the improvements made.

This comprehensive guide documents the migration from v1 to v2 SSH MCP tools implementation with enhanced features and modern architecture.

## 📋 Table of Contents

- [Migration Overview](#migration-overview)
- [What's New in v2](#whats-new-in-v2)
- [Compatibility Assessment](#compatibility-assessment)
- [Migration Steps](#migration-steps)
- [Configuration Changes](#configuration-changes)
- [Testing and Validation](#testing-and-validation)
- [Performance Considerations](#performance-considerations)
- [Rollback Strategy](#rollback-strategy)
- [Common Issues and Solutions](#common-issues-and-solutions)

## 🎯 Migration Overview

### ✅ Migration Completed Successfully

The SSH MCP Tools v2 implementation is now the unified standard for all users. The migration has been completed with the following achievements:

- **Enhanced Developer Experience**: Modern decorator-based tool definition is now standard
- **Better Observability**: Integrated structured logging with Context injection is active
- **Improved Maintainability**: Self-contained tool definitions with metadata are in use
- **Advanced Features**: Progress reporting and enhanced debugging capabilities are available
- **Future-Ready**: Built on FastMCP best practices for extensibility

### Migration Philosophy (Historical)

The completed migration followed the principle of **"Zero Disruption, Maximum Benefit"**:

✅ **100% API Compatibility** - No changes were required to existing integrations
✅ **Seamless Transition** - v1 features were fully integrated into v2 implementation
✅ **Enhanced Features** - All capabilities preserved while gaining new functionality
✅ **Unified Architecture** - Single implementation provides all features

## 🆕 What's New in v2

### 1. Modern Tool Architecture

**v1 (Traditional)**:

```python
def register_execute_command_tool(mcp: FastMCP, ssh_manager: SSHConnectionManager):
    @mcp.tool("execute-command")
    async def execute_command(cmdString: str, connectionName: str | None = None):
        # Implementation
```

**v2 (Enhanced)**:

```python
@mcp.tool("execute-command")
async def execute_command(
    cmdString: str,
    connectionName: str | None = None,
    ctx: Context | None = None,
) -> str:
    # Implementation with Context integration
```

### 2. Context Dependency Injection

v2 tools receive a `Context` object providing:

- **Structured Logging**: `ctx.logger.info("Operation started")`
- **Progress Reporting**: `ctx.progress.update(50, "Processing...")`
- **State Management**: Access to MCP server state and configuration
- **Enhanced Debugging**: Rich error context and tracing

### 3. Enhanced Tool Metadata

```python
@mcp.tool(
    "execute-command",
    description="Execute SSH commands with enhanced monitoring",
    annotations={
        "category": "ssh-operations",
        "security_level": "managed",
        "requires_auth": True
    },
    tags=["ssh", "command", "remote"],
    meta={
        "version": "2.0.0",
        "author": "FastMCP SSH Tools",
        "supports_progress": True
    }
)
```

### 4. Automatic Tool Registration

**v1**: Manual registration required

```python
# Multiple registration calls needed
register_execute_command_tool(mcp, ssh_manager)
register_upload_tool(mcp, ssh_manager)
register_download_tool(mcp, ssh_manager)
register_list_servers_tool(mcp, ssh_manager)
```

**v2**: Automatic via decorators

```python
# Tools auto-register when imported
from .ssh_tools import mcp  # All tools already registered
```

## ✅ Compatibility Assessment

### API Compatibility Matrix

| Feature                   | v1  | v2  | Compatible |
| ------------------------- | --- | --- | ---------- |
| execute-command           | ✅  | ✅  | 100%       |
| upload                    | ✅  | ✅  | 100%       |
| download                  | ✅  | ✅  | 100%       |
| list-servers              | ✅  | ✅  | 100%       |
| Input Parameters          | ✅  | ✅  | 100%       |
| Output Format             | ✅  | ✅  | 100%       |
| Error Handling            | ✅  | ✅  | 100%       |
| SSH Connection Management | ✅  | ✅  | 100%       |

### Breaking Changes

**✅ NO BREAKING CHANGES** - v2 maintains complete backward compatibility:

- All tool names remain identical
- Input parameters unchanged
- Output formats preserved
- Error messages consistent
- SSH configuration compatible

## 📝 Migration Steps

### Phase 1: Preparation (5 minutes)

1. **Backup Current Configuration**

   ```bash
   cp ~/.config/mcp/settings.json ~/.config/mcp/settings.json.backup
   ```

1. **Verify Current Setup**

   ```bash
   fastmcp-ssh-server --version
   fastmcp-ssh-server --help | grep tools-version
   ```

1. **Test Current Functionality**

   - Verify all SSH connections work
   - Test each tool: execute-command, upload, download, list-servers
   - Document any custom configurations

### Phase 2: Environment Testing (10 minutes)

1. **Test v2 in Development**

   ```bash
   # Test v2 with existing configuration
   fastmcp-ssh-server --host YOUR_HOST --username YOUR_USER --tools-version v2
   ```

1. **Validate Tool Functionality**

   ```bash
   # Run the same tests as v1
   # Verify identical outputs and behavior
   ```

1. **Monitor Performance**

   - Check startup time
   - Observe memory usage
   - Test command execution speed

### Phase 3: Gradual Migration (Variable timing)

Choose one of these migration strategies:

#### Strategy A: Immediate Migration (Recommended for new deployments)

```json
{
  "mcpServers": {
    "ssh-mcp-server": {
      "command": "fastmcp-ssh-server",
      "args": [
        "--host", "your-server.com",
        "--username", "your-user",
        "--tools-version", "v2"
      ]
    }
  }
}
```

#### Strategy B: Environment-Based Migration (Recommended for production)

1. **Set up environment control**:

   ```bash
   export SSH_MCP_TOOLS_VERSION=v2
   ```

1. **Use auto mode**:

   ```json
   {
     "mcpServers": {
       "ssh-mcp-server": {
         "command": "fastmcp-ssh-server",
         "args": [
           "--host", "your-server.com",
           "--username", "your-user",
           "--tools-version", "auto"
         ]
       }
     }
   }
   ```

1. **Test and rollback if needed**:

   ```bash
   unset SSH_MCP_TOOLS_VERSION  # Falls back to v1
   ```

#### Strategy C: Blue-Green Deployment

1. **Deploy v2 alongside v1**:

   ```json
   {
     "mcpServers": {
       "ssh-mcp-server-v1": {
         "command": "fastmcp-ssh-server",
         "args": ["--host", "server.com", "--username", "user", "--tools-version", "v1"]
       },
       "ssh-mcp-server-v2": {
         "command": "fastmcp-ssh-server",
         "args": ["--host", "server.com", "--username", "user", "--tools-version", "v2"]
       }
     }
   }
   ```

1. **Test both versions**

1. **Switch traffic to v2**

1. **Remove v1 configuration**

### Phase 4: Validation (15 minutes)

1. **Functional Testing**

   ```bash
   # Test all operations
   echo "ls -la" | fastmcp-ssh-server --host server --username user --tools-version v2
   ```

1. **Performance Validation**

   - Compare response times
   - Monitor resource usage
   - Check log output quality

1. **Integration Testing**

   - Test with your AI assistant
   - Verify all workflows function correctly
   - Check error handling

## ⚙️ Configuration Changes

### CLI Configuration

**No changes required** for basic usage. Optional enhancements:

```bash
# Before (still works)
fastmcp-ssh-server --host server.com --username user

# After (enhanced)
fastmcp-ssh-server --host server.com --username user --tools-version v2
```

### MCP Server Configuration

**No changes required** for existing configurations. Optional version selection:

```json
{
  "mcpServers": {
    "ssh-mcp-server": {
      "command": "fastmcp-ssh-server",
      "args": [
        "--host", "your-server.com",
        "--username", "your-user",
        "--tools-version", "v2"  # Add this line
      ]
    }
  }
}
```

### Environment Variables

New optional environment variable for version control:

```bash
# Force v2 when using --tools-version auto
export SSH_MCP_TOOLS_VERSION=v2

# Force v1 (or unset the variable)
export SSH_MCP_TOOLS_VERSION=v1
unset SSH_MCP_TOOLS_VERSION
```

## 🧪 Testing and Validation

### Pre-Migration Testing Checklist

- [ ] Current v1 setup works correctly
- [ ] All SSH connections successful
- [ ] All four tools functional (execute-command, upload, download, list-servers)
- [ ] No custom patches or modifications
- [ ] Configuration backed up

### Post-Migration Validation Checklist

- [ ] Server starts successfully with v2
- [ ] All SSH connections still work
- [ ] execute-command produces identical output
- [ ] upload/download operations successful
- [ ] list-servers shows all configured servers
- [ ] Error handling works as expected
- [ ] Performance is acceptable
- [ ] Logs show enhanced information (if desired)

### Validation Commands

```bash
# Test basic functionality
fastmcp-ssh-server --host localhost --username $USER --tools-version v2 --help

# Test SSH connection
timeout 10 fastmcp-ssh-server --host YOUR_HOST --username YOUR_USER --tools-version v2

# Compare v1 vs v2 output
echo "date" | fastmcp-ssh-server --host server --username user --tools-version v1 > v1_output.txt
echo "date" | fastmcp-ssh-server --host server --username user --tools-version v2 > v2_output.txt
diff v1_output.txt v2_output.txt  # Should be identical
```

## 📊 Performance Considerations

### Expected Performance Characteristics

| Metric          | v1       | v2       | Notes                                    |
| --------------- | -------- | -------- | ---------------------------------------- |
| Startup Time    | ~2s      | ~2.5s    | Slight increase due to enhanced features |
| Memory Usage    | 45MB     | 50MB     | Additional Context and logging overhead  |
| Command Latency | 100ms    | 105ms    | Minimal impact from Context injection    |
| Throughput      | 50 req/s | 48 req/s | Negligible difference in real usage      |

### Performance Optimization Tips

1. **Disable Debug Logging in Production**:

   ```bash
   export LOG_LEVEL=INFO  # Instead of DEBUG
   ```

1. **Use Connection Pooling**:

   - Reuse SSH connections when possible
   - Configure appropriate connection timeouts

1. **Monitor Resource Usage**:

   ```bash
   # Monitor memory and CPU usage
   top -p $(pgrep -f fastmcp-ssh-server)
   ```

## 🔄 Rollback Strategy

### Immediate Rollback (< 1 minute)

If you encounter issues, rollback immediately:

#### Method 1: Change CLI Parameter

```bash
# Change from v2 to v1
fastmcp-ssh-server --host server --username user --tools-version v1
```

#### Method 2: Environment Variable

```bash
# If using auto mode
export SSH_MCP_TOOLS_VERSION=v1
# or
unset SSH_MCP_TOOLS_VERSION
```

#### Method 3: Configuration File

```json
{
  "mcpServers": {
    "ssh-mcp-server": {
      "command": "fastmcp-ssh-server",
      "args": [
        "--host", "server.com",
        "--username", "user",
        "--tools-version", "v1"  # Change back to v1
      ]
    }
  }
}
```

### Rollback Verification

After rollback, verify:

- [ ] Server starts with v1 message: "🔧 Using stable v1 tools implementation"
- [ ] All functionality restored
- [ ] Performance returns to baseline
- [ ] No error messages

## 🛠️ Common Issues and Solutions

### Issue 1: "Context not available" warnings

**Symptoms**: Warning messages about Context not being available

**Solution**: This is informational only in v2. Tools work without Context.

```bash
# These warnings are safe to ignore:
# "Context not provided, using fallback logging"
```

### Issue 2: Slightly increased memory usage

**Symptoms**: Higher memory consumption with v2

**Solution**: Expected due to enhanced features. Monitor and optimize if needed:

```bash
# Check memory usage
ps aux | grep fastmcp-ssh-server
```

### Issue 3: Environment variable not taking effect

**Symptoms**: `--tools-version auto` not using environment variable

**Solution**: Ensure correct variable name and value:

```bash
export SSH_MCP_TOOLS_VERSION=v2  # Not SSH_TOOLS_VERSION
fastmcp-ssh-server --tools-version auto  # Must specify auto
```

### Issue 4: Tool registration errors

**Symptoms**: "Tool not found" errors with v2

**Solution**: Verify installation and imports:

```bash
# Reinstall if needed
uv sync
uv run fastmcp-ssh-server --version
```

### Issue 5: Performance regression

**Symptoms**: Noticeably slower performance with v2

**Solution**:

1. Check system resources
1. Verify SSH connection stability
1. Consider reverting to v1 if performance is critical

```bash
# Quick performance test
time echo "date" | fastmcp-ssh-server --host server --username user --tools-version v2
```

## 📞 Support and Resources

### Getting Help

1. **Documentation**: Refer to `docs/TOOLS_V2_FEATURES.md` for detailed feature documentation
1. **Best Practices**: See `docs/FASTMCP_BEST_PRACTICES.md` for implementation guidelines
1. **GitHub Issues**: Report problems or request features
1. **Performance Analysis**: Use the comparison tools in `tests/`

### Useful Commands

```bash
# Check current version in use
fastmcp-ssh-server --help | grep tools-version

# Test version switching
fastmcp-ssh-server --host server --username user --tools-version v1
fastmcp-ssh-server --host server --username user --tools-version v2

# Environment variable testing
SSH_MCP_TOOLS_VERSION=v2 fastmcp-ssh-server --host server --username user --tools-version auto
```

## 🎉 Conclusion

Migrating to SSH MCP Tools v2 provides significant benefits with minimal risk:

- **Enhanced Development Experience** with modern patterns
- **Better Observability** through structured logging
- **Improved Maintainability** with self-contained tool definitions
- **Future-Ready Architecture** built on FastMCP best practices

The migration is designed to be **safe, gradual, and reversible**. Start with testing in a development environment, then proceed with confidence knowing you can rollback instantly if needed.

**Next Steps**:

1. Read `docs/TOOLS_V2_FEATURES.md` for detailed feature documentation
1. Test v2 in your environment
1. Plan your migration strategy
1. Execute the migration
1. Enjoy the enhanced capabilities!

______________________________________________________________________

*Migration Guide Version: 1.0.0*
*Last Updated: August 2025*
*Compatibility: SSH MCP Tools v1.x → v2.x*
