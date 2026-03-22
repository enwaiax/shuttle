# MCP Tools API Reference

Shuttle exposes 9 MCP tools that AI assistants call automatically. This page documents every tool's parameters, return format, and usage examples.

## ssh_execute

Run a shell command on a remote SSH node. Supports stateless and session-based (stateful) execution with 4-level security checks.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `command` | string | yes | — | Shell command to execute |
| `node` | string | no | — | Node name (required if no `session_id`) |
| `session_id` | string | no | — | Session ID for stateful execution |
| `timeout` | float | no | 30.0 | Command timeout in seconds |
| `confirm_token` | string | no | — | Token to confirm a CONFIRM-level command |
| `bypass_scope` | string | no | — | Bypass scope for session commands |

**Returns:** Command output (stdout), or an error/security message.

**Security flow:**

1. Command is evaluated against security rules
2. `block` → rejected immediately
3. `confirm` → returns a token; re-call with `confirm_token` to proceed
4. `warn` → executes with warning logged
5. `allow` → executes normally

**Example:**

```
AI → ssh_execute(node="gpu-server", command="nvidia-smi")
AI ← "Fri Mar 21 17:07:21 2026\n+---------------------+\n| NVIDIA-SMI 580.105 ..."
```

---

## ssh_list_nodes

List all configured SSH nodes with their connection status.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| *(none)* | — | — | — |

**Returns:** One line per node with status icon, name, host, port, and username.

```
[OK] gpu-server  (10.0.0.1:22, user=root)
[OK] staging     (staging.example.com:22, user=deploy)
[--] dev-box     (192.168.1.10:22, user=dev)
```

Status icons: `[OK]` = active, `[--]` = inactive, `[!!]` = error.

---

## ssh_session_start

Start a stateful SSH session on a node. Sessions preserve the working directory across commands.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `node` | string | yes | Node name |

**Returns:** Session ID and initial working directory.

```
Session started.
  session_id: a1b2c3d4
  node: gpu-server
  cwd: /home/root
```

---

## ssh_session_end

Close an active SSH session and release its resources.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | Session ID to close |

**Returns:** Confirmation message.

---

## ssh_session_list

List all active SSH sessions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| *(none)* | — | — | — |

**Returns:** One line per session with session ID, node, and current working directory.

```
  a1b2c3d4  node=gpu-server  cwd=/workspace/training
  e5f6g7h8  node=staging     cwd=/var/www/app
```

---

## ssh_upload

Upload a file to a remote node via SFTP.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `node` | string | yes | Node name |
| `local_path` | string | yes | Local file path |
| `remote_path` | string | yes | Remote destination path |

**Returns:** Confirmation or error message.

```
Uploaded /tmp/model.pt -> gpu-server:/workspace/model.pt
```

---

## ssh_download

Download a file from a remote node via SFTP.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `node` | string | yes | Node name |
| `remote_path` | string | yes | Remote file path |
| `local_path` | string | yes | Local destination path |

**Returns:** Confirmation or error message.

---

## ssh_add_node

Add a new SSH node to the Shuttle configuration. The node is registered in the database and connection pool.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | yes | — | Unique node name |
| `host` | string | yes | — | Hostname or IP |
| `port` | int | no | 22 | SSH port |
| `username` | string | no | "" | SSH username |
| `password` | string | no | — | Password auth (or use `private_key`) |
| `private_key` | string | no | — | Private key content |
| `jump_host` | string | no | — | Name of an existing node to use as jump host |
| `tags` | list[string] | no | — | Tags for categorization |

Either `password` or `private_key` must be provided. Credentials are encrypted at rest.

**Returns:** Confirmation with node ID.

---

## ssh_remove_node

Remove an SSH node from the configuration and close its connections.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Node name to remove |

**Returns:** Confirmation or error if node not found.
