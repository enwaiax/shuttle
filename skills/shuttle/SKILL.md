---
name: shuttle
description: Use Shuttle for authenticated, policy-controlled remote operations.
---

# Using Shuttle

Use Shuttle when an AI agent needs to operate existing SSH nodes through a central policy, approval, and audit gateway.

## Core workflow

1. Inspect available nodes with `ssh_list_nodes` and select the exact requested node. Never substitute another host silently.
2. Begin with read-only inspection whenever possible.
3. Run commands with `ssh_run`. Shuttle derives actor, client, and conversation identity from the authenticated MCP request context.
4. Handle the result according to its policy decision:
   - `ALLOW` / `WARN`: inspect and report the result.
   - `BLOCK`: stop; do not bypass it.
   - `PENDING_APPROVAL`: report the exact node and command, then wait for a human decision in the Shuttle Web Approvals page.
5. After approval, retry the identical command with its `approval_id`. An approval is bound to the authenticated requester, MCP session, node, and exact command; it is single-use and expires.
6. Report the command result together with its approval or audit ID when present.

## Sessions

- Shuttle automatically preserves remote working-directory state within the authenticated MCP session.
- Do not try to provide or override actor, client, or conversation identifiers.
- A reconnect may create a new conversation boundary; do not assume prior approvals or session state carry over.

## File operations

- Use `ssh_upload` and `ssh_download` only after verifying the local path, remote path, node, and overwrite impact.
- Do not place secrets in command text or ordinary files when a credential mechanism is available.
- Treat node creation and file transfer as privileged operations even when no shell command is involved.

## Authentication and host trust

- HTTP MCP uses an Agent token distinct from the Web/operator token.
- Never expose the Web/operator token to an agent.
- Shuttle requires SSH host-key verification. Register the host key in the trusted `known_hosts` file before connecting; never disable checking with `known_hosts=None`.

## Failure handling

- Use bounded timeouts for commands that may hang.
- On connection or host-key errors, stop and report the exact failure instead of weakening verification.
- If an approval is denied, expired, consumed, or mismatched, request a new approval rather than altering identifiers or replaying it.
