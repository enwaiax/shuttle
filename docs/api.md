# MCP Tools API Reference

Shuttle exposes 5 MCP tools that AI assistants call automatically. This page documents every tool's parameters, return format, and usage examples.

## ssh_run

Run a shell command on a remote SSH node. Sessions are managed automatically: working directory is preserved across calls to the same node. 4-level security checks are applied before execution.

| Parameter       | Type   | Required | Default | Description                                       |
| --------------- | ------ | -------- | ------- | ------------------------------------------------- |
| `command`       | string | yes      | —       | Shell command to execute                          |
| `node`          | string | no       | —       | Node name (auto-selected if only one node exists) |
| `timeout`       | float  | no       | 30.0    | Command timeout in seconds                        |
| `confirm_token` | string | no       | —       | Token to confirm a CONFIRM-level command          |
| `bypass_scope`  | string | no       | —       | Bypass scope for session commands                 |

**Returns:** Command output (stdout), or an error/security message.

**Session management:** Sessions are implicit. The first call to a node auto-creates a session; subsequent calls reuse it, preserving the working directory.

**Security flow:**

1. Command is evaluated against security rules
1. `block` → rejected immediately
1. `confirm` → returns a token; re-call with `confirm_token` to proceed
1. `warn` → executes with warning logged
1. `allow` → executes normally

**Example:**

```
AI → ssh_run(node="gpu-server", command="nvidia-smi")
AI ← "Fri Mar 21 17:07:21 2026\n+---------------------+\n| NVIDIA-SMI 580.105 ..."

AI → ssh_run(node="gpu-server", command="cd /workspace && pwd")
AI ← "/workspace"   # working directory preserved for next call
```

______________________________________________________________________

## ssh_list_nodes

List all configured SSH nodes with their connection status.

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| *(none)*  | —    | —        | —           |

**Returns:** One line per node with status icon, name, host, port, and username.

```
[OK] gpu-server  (10.0.0.1:22, user=root)
[OK] staging     (staging.example.com:22, user=deploy)
[--] dev-box     (192.168.1.10:22, user=dev)
```

Status icons: `[OK]` = active, `[--]` = inactive, `[!!]` = error.

______________________________________________________________________

## ssh_upload

Upload a file to a remote node via SFTP.

| Parameter     | Type   | Required | Description             |
| ------------- | ------ | -------- | ----------------------- |
| `node`        | string | yes      | Node name               |
| `local_path`  | string | yes      | Local file path         |
| `remote_path` | string | yes      | Remote destination path |

**Returns:** Confirmation or error message.

```
Uploaded /tmp/model.pt -> gpu-server:/workspace/model.pt
```

______________________________________________________________________

## ssh_download

Download a file from a remote node via SFTP.

| Parameter     | Type   | Required | Description            |
| ------------- | ------ | -------- | ---------------------- |
| `node`        | string | yes      | Node name              |
| `remote_path` | string | yes      | Remote file path       |
| `local_path`  | string | yes      | Local destination path |

**Returns:** Confirmation or error message.

______________________________________________________________________

## ssh_add_node

Add a new SSH node to the Shuttle configuration. The node is registered in the database and connection pool.

| Parameter     | Type         | Required | Default | Description                                  |
| ------------- | ------------ | -------- | ------- | -------------------------------------------- |
| `name`        | string       | yes      | —       | Unique node name                             |
| `host`        | string       | yes      | —       | Hostname or IP                               |
| `port`        | int          | no       | 22      | SSH port                                     |
| `username`    | string       | no       | ""      | SSH username                                 |
| `password`    | string       | no       | —       | Password auth (or use `private_key`)         |
| `private_key` | string       | no       | —       | Private key content                          |
| `jump_host`   | string       | no       | —       | Name of an existing node to use as jump host |
| `tags`        | list[string] | no       | —       | Tags for categorization                      |

Either `password` or `private_key` must be provided. Credentials are encrypted at rest.

**Returns:** Confirmation with node ID.
