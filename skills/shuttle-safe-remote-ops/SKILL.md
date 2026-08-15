---
name: shuttle-safe-remote-ops
description: Use Shuttle CLI/MCP for policy-controlled remote operations.
---

# Shuttle safe remote operations

Use Shuttle when an agent must operate an existing SSH node and the action must be attributable, policy-checked, human-approved when risky, and auditable.

## Required identity

Every execution must supply stable values for:

- `actor_id`: the human or service requesting the work;
- `client_id`: the agent surface, such as `claude-code`, `codex`, or `hermes`;
- `conversation_id`: the current task/session identifier.

Never reuse another conversation's identity.

## Workflow

1. List/select the exact node. Never silently substitute a similarly named host.
2. Start with read-only diagnosis, especially for production nodes.
3. Call `ssh_run` with the three identity fields.
4. If the result starts with `PENDING_APPROVAL`, stop. Tell the user the exact node and command. Do not attempt to approve it or use the retired `confirm_token` argument.
5. Wait for a human to decide in the Shuttle Web **Approvals** page.
6. Retry the identical command with the returned `approval_id` and identical identity fields.
7. Treat approval as single-use. Any changed node, command, actor, client, or conversation needs a new request.
8. Report the command result and approval ID.

## Safety

- Never bypass `block` decisions.
- Never pass `known_hosts=None`; Shuttle requires trusted SSH host identity.
- Do not put secrets in commands because command text is audited.
- Prefer bounded timeouts and explicit output collection.
- File transfer and node mutation are privileged operations; verify scope before use.
