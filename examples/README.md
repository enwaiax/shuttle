# {{RIPER-5:

# Action: "Added"

# Task_ID: "3702898f-86db-43bb-aae0-0161b6a8eedf"

# Timestamp: "2025-08-05T21:23:20+08:00"

# Authoring_Role: "LD"

# Principle_Applied: "文档即代码 + 示例驱动学习"

# Quality_Check: "实用的使用示例，涵盖各种场景，易于理解和复制"

# }}

# {{START_MODIFICATIONS}}

# FastMCP SSH Server - Usage Examples

This directory contains practical examples for using the FastMCP SSH Server in various scenarios.

## 📁 Examples Overview

### Basic Usage

- **[single_connection.sh](basic/single_connection.sh)** - Simple single server connection
- **[multiple_connections.sh](basic/multiple_connections.sh)** - Connecting to multiple servers
- **[private_key_auth.sh](basic/private_key_auth.sh)** - Using private key authentication

### Security Configuration

- **[restrictive_security.sh](security/restrictive_security.sh)** - Production-ready security setup
- **[development_security.sh](security/development_security.sh)** - Development environment setup
- **[pattern_examples.sh](security/pattern_examples.sh)** - Advanced regex patterns

### MCP Client Examples

- **[python_client.py](mcp_clients/python_client.py)** - Python MCP client example
- **[node_client.js](mcp_clients/node_client.js)** - Node.js MCP client example
- **[batch_operations.py](mcp_clients/batch_operations.py)** - Batch operations example

### Deployment

- **[systemd_service.sh](deployment/systemd_service.sh)** - SystemD service setup
- **[docker_deployment/](deployment/docker_deployment/)** - Docker deployment example
- **[monitoring_setup.py](deployment/monitoring_setup.py)** - Basic monitoring setup

### Advanced Scenarios

- **[ci_cd_integration.py](advanced/ci_cd_integration.py)** - CI/CD pipeline integration
- **[backup_automation.py](advanced/backup_automation.py)** - Automated backup scripts
- **[log_analysis.py](advanced/log_analysis.py)** - Log analysis and reporting

## 🚀 Quick Start Examples

### 1. Single Server Connection

```bash
# Basic connection with password
fastmcp-ssh-server \
    --host example.com \
    --username myuser \
    --password mypass

# With private key
fastmcp-ssh-server \
    --host example.com \
    --username myuser \
    --private-key ~/.ssh/id_rsa
```

### 2. Multiple Servers

```bash
# Multiple servers with global security
fastmcp-ssh-server \
    --whitelist "ls,pwd,git.*" \
    --blacklist "rm.*,sudo.*" \
    user1@server1.com:22 \
    user2@server2.com:2222
```

### 3. MCP Client Usage

```python
import asyncio
from mcp import ClientSession

async def example():
    async with ClientSession("fastmcp-ssh-server") as session:
        # Execute command
        result = await session.call_tool(
            "execute-command",
            cmdString="uptime",
            serverName="production"
        )
        print(result["stdout"])

asyncio.run(example())
```

## 📋 Example Categories

### By Use Case

| Use Case        | Examples        | Description            |
| --------------- | --------------- | ---------------------- |
| **Development** | `development_*` | Local dev environments |
| **Staging**     | `staging_*`     | Testing and QA         |
| **Production**  | `production_*`  | Live systems           |
| **CI/CD**       | `ci_cd_*`       | Automated deployments  |
| **Monitoring**  | `monitoring_*`  | System monitoring      |
| **Backup**      | `backup_*`      | Data backup automation |

### By Complexity

| Level            | Examples                    | Description                     |
| ---------------- | --------------------------- | ------------------------------- |
| **Beginner**     | `basic/`                    | Simple, single-purpose examples |
| **Intermediate** | `security/`, `mcp_clients/` | Real-world scenarios            |
| **Advanced**     | `advanced/`, `deployment/`  | Complex integrations            |

## 🔧 Running Examples

### Prerequisites

```bash
# From repository root
uv sync
```

### Environment Setup

```bash
# Copy environment template
cp examples/.env.template .env

# Edit with your SSH details
vim .env
```

### Example Environment File

```bash
# .env.template
SSH_HOST=example.com
SSH_PORT=22
SSH_USERNAME=myuser
SSH_PASSWORD=mypass
SSH_PRIVATE_KEY=~/.ssh/id_rsa
SSH_PASSPHRASE=

# Security settings
WHITELIST_COMMANDS="ls,pwd,echo.*,git.*"
BLACKLIST_COMMANDS="rm.*,sudo.*,chmod.*"

# Optional settings
TIMEOUT=30
LOG_LEVEL=info
```

### Running Shell Examples

```bash
# Make scripts executable
chmod +x examples/basic/*.sh

# Run basic example
./examples/basic/single_connection.sh

# Run with environment variables
source .env && ./examples/security/restrictive_security.sh
```

### Running Python Examples

```bash
# Set Python path
export PYTHONPATH=src

# Run Python example
python examples/mcp_clients/python_client.py

# Run with specific configuration
SSH_HOST=myserver.com python examples/advanced/backup_automation.py
```

## 📝 Creating Custom Examples

### Example Template

```bash
#!/bin/bash
# {{RIPER-5:
#   Action: "Added"
#   Task_ID: "your-task-id"
#   Timestamp: "$(date -Iseconds)"
#   Authoring_Role: "User"
#   Principle_Applied: "Example-driven learning"
#   Quality_Check: "Tested and documented example"
# }}

# Description: [What this example demonstrates]
# Usage: ./your_example.sh [optional arguments]

set -e  # Exit on any error

# Configuration
HOST=${SSH_HOST:-"example.com"}
USER=${SSH_USERNAME:-"user"}
PASS=${SSH_PASSWORD:-"pass"}

# Your example code here
fastmcp-ssh-server \
    --host "$HOST" \
    --username "$USER" \
    --password "$PASS" \
    --whitelist "your,commands" \
    --blacklist "dangerous.*"

echo "✅ Example completed successfully"
```

### Python Example Template

```python
#!/usr/bin/env python3
"""
FastMCP SSH Server - Example Template

Description: [What this example demonstrates]
Usage: python your_example.py [arguments]
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ssh_mcp.server import SSHMCPServer
from ssh_mcp.models import SSHConfig

async def main():
    """Main example function."""
    # Configuration from environment
    config = SSHConfig(
        name="example_server",
        host=os.getenv("SSH_HOST", "example.com"),
        username=os.getenv("SSH_USERNAME", "user"),
        password=os.getenv("SSH_PASSWORD", "pass"),
        command_whitelist=["ls", "pwd", "echo.*"],
        command_blacklist=["rm.*", "sudo.*"]
    )

    # Your example logic here
    print("✅ Example completed successfully")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🧪 Testing Examples

### Validation Script

```bash
#!/bin/bash
# examples/validate_examples.sh

echo "🧪 Validating FastMCP SSH Server Examples"
echo "=" * 50

# Test basic examples
for example in examples/basic/*.sh; do
    echo "Testing: $example"
    bash -n "$example" && echo "✅ Syntax OK" || echo "❌ Syntax Error"
done

# Test Python examples
for example in examples/*/*.py; do
    echo "Testing: $example"
    python -m py_compile "$example" && echo "✅ Syntax OK" || echo "❌ Syntax Error"
done

echo "🎉 Example validation completed"
```

## 📚 Learning Path

### For Beginners

1. Start with **[basic/single_connection.sh](basic/single_connection.sh)**
1. Try **[basic/multiple_connections.sh](basic/multiple_connections.sh)**
1. Learn security with **[security/development_security.sh](security/development_security.sh)**
1. Use MCP clients with **[mcp_clients/python_client.py](mcp_clients/python_client.py)**

### For Intermediate Users

1. **[security/restrictive_security.sh](security/restrictive_security.sh)** - Production security
1. **[mcp_clients/batch_operations.py](mcp_clients/batch_operations.py)** - Batch operations
1. **[deployment/systemd_service.sh](deployment/systemd_service.sh)** - Service deployment

### For Advanced Users

1. **[advanced/ci_cd_integration.py](advanced/ci_cd_integration.py)** - CI/CD integration
1. **[deployment/docker_deployment/](deployment/docker_deployment/)** - Containerization
1. **[advanced/monitoring_setup.py](deployment/monitoring_setup.py)** - Monitoring

## 🤝 Contributing Examples

We welcome contributions of new examples! Please:

1. **Follow the template** format above
1. **Test thoroughly** before submitting
1. **Document clearly** what the example demonstrates
1. **Include error handling** where appropriate
1. **Use environment variables** for configuration

### Submission Process

1. Create your example in the appropriate directory
1. Test with the validation script
1. Update this README with your example
1. Submit a pull request

## 📞 Support

- **Issues**: [Report example issues](https://github.com/your-username/fastmcp-ssh-server/issues)
- **Discussions**: [Ask questions](https://github.com/your-username/fastmcp-ssh-server/discussions)
- **Documentation**: [Main docs](../docs/)

______________________________________________________________________

**Happy coding with FastMCP SSH Server!** 🚀

# {{END_MODIFICATIONS}}
