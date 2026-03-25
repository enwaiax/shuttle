# Shuttle MCP — SSH Gateway for AI Assistants

Use this skill when the user wants to execute commands on remote SSH servers, manage SSH nodes, or work with the Shuttle MCP tools.

## What is Shuttle

Shuttle is a secure SSH gateway that lets AI assistants operate remote servers through the MCP protocol. It provides connection pooling, session isolation, command safety rules, and a web control panel.

## Available MCP Tools

| Tool                | Purpose                                                | Key Parameters                                                                       |
| ------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `ssh_execute`       | Run a command on a remote node                         | `command`, `node` (name), `timeout`, `session_id`, `confirm_token`                   |
| `ssh_list_nodes`    | List all configured SSH nodes                          | (none)                                                                               |
| `ssh_add_node`      | Add a new SSH node                                     | `name`, `host`, `port`, `username`, `password` or `private_key`, `jump_host`, `tags` |
| `ssh_remove_node`   | Remove a node                                          | `name`                                                                               |
| `ssh_session_start` | Start a stateful session (preserves working directory) | `node`                                                                               |
| `ssh_session_end`   | End a session                                          | `session_id`                                                                         |
| `ssh_session_list`  | List active sessions                                   | (none)                                                                               |
| `ssh_upload`        | Upload a file via SFTP                                 | `node`, `local_path`, `remote_path`                                                  |
| `ssh_download`      | Download a file via SFTP                               | `node`, `remote_path`, `local_path`                                                  |

## How to Use

### Basic command execution

```
ssh_execute(command="nvidia-smi", node="gpu-server")
```

### Stateful session (working directory persists)

```
session = ssh_session_start(node="gpu-server")
ssh_execute(command="cd /opt/project", session_id=session.id)
ssh_execute(command="python train.py", session_id=session.id)  # runs in /opt/project
ssh_session_end(session_id=session.id)
```

### Adding a node via MCP

```
ssh_add_node(name="dev-box", host="10.0.0.1", port=22, username="root", password="secret")
```

## Security Rules

Commands are checked against 4 security levels before execution:

| Level       | Behavior                                                      | Example                        |
| ----------- | ------------------------------------------------------------- | ------------------------------ |
| **block**   | Rejected, never executes                                      | `rm -rf /`, `mkfs`, fork bomb  |
| **confirm** | Returns a token, must re-call with `confirm_token` to execute | `sudo *`, `rm -rf`, `shutdown` |
| **warn**    | Executes but logged with warning                              | `pip install`, `apt install`   |
| **allow**   | Normal execution                                              | Everything else                |

### Handling confirm responses

When a command hits a `confirm` rule, Shuttle returns a message like:

```
CONFIRMATION REQUIRED
Command: sudo apt update
Matched rule: Sudo commands

To execute, re-run with: ssh_execute(command="sudo apt update", node="gpu-server", confirm_token="abc123")
```

Show this to the user. If they approve, re-call with the provided `confirm_token`.

## Best Practices

1. **Use sessions for multi-step tasks** — `cd` + subsequent commands stay in the same directory
1. **Name nodes descriptively** — `gpu-prod-a100` not `server1`
1. **Check node list first** — call `ssh_list_nodes` before executing if unsure which nodes exist
1. **Respect confirm prompts** — always show confirm messages to the user, never auto-bypass
1. **Set reasonable timeouts** — default is 30s, increase for long-running commands (`timeout=300`)
1. **Use tags** — nodes can have tags like `["gpu", "prod"]` for organization

## Troubleshooting

| Error                    | Cause                              | Fix                                           |
| ------------------------ | ---------------------------------- | --------------------------------------------- |
| "No node named X"        | Node not configured                | `ssh_add_node` or `shuttle node add`          |
| "BLOCKED"                | Command matched a block rule       | Cannot be overridden, use a different command |
| "Per-node limit reached" | Too many concurrent connections    | Wait or increase `SHUTTLE_POOL_MAX_PER_NODE`  |
| Connection timeout       | Network issue or wrong credentials | Check host/port/credentials                   |
