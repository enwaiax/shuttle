# Security Rules

Shuttle evaluates every command against a rule engine before execution. Rules use regex patterns and are organized into four severity levels. This guide covers how rules work, the built-in defaults, per-node overrides, and the confirmation bypass mechanism.

## Security Levels

Every rule has one of four levels. When a command matches a rule, Shuttle takes the corresponding action:

| Level       | Behavior                                                                              | When to use                                                                                |
| ----------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **block**   | Command is rejected immediately. Cannot be bypassed.                                  | Destructive, unrecoverable operations (wipe disk, fork bomb).                              |
| **confirm** | Execution paused. A one-time token is returned that the AI must re-submit to proceed. | Privileged or risky operations that a human should approve (sudo, force delete, shutdown). |
| **warn**    | Command executes, but the event is flagged in the audit log.                          | Operations worth noting but not blocking (package installs, config changes).               |
| **allow**   | Command executes normally.                                                            | The default — any command that does not match a higher-level rule.                         |

Rules are evaluated in **priority order** (lowest number first). The first matching rule determines the outcome. If no rule matches, the command is allowed.

## Regex Pattern Syntax

Rule patterns are Python-compatible regular expressions matched with `re.search()` (not `re.match()`), so they can match anywhere in the command string.

### Examples

| Pattern              | Matches                           | Does not match            |
| -------------------- | --------------------------------- | ------------------------- |
| `^rm -rf /$`         | `rm -rf /` (exact)                | `rm -rf /tmp`             |
| `sudo .*`            | `sudo apt update`, `sudo reboot`  | `visudo`                  |
| `rm -rf `            | `rm -rf /tmp`, `rm -rf ~`         | `rm file.txt`             |
| `mkfs\.`             | `mkfs.ext4 /dev/sda1`             | `mkfsomething`            |
| `curl .* \| bash`    | `curl http://x.com/setup \| bash` | `curl http://x.com/setup` |
| `chmod 777`          | `chmod 777 /var/www`              | `chmod 755 /var/www`      |
| `:\(\)\{.*:\|:&\};:` | Fork bomb pattern                 | Normal commands           |

Patterns are capped at 500 characters to prevent ReDoS attacks. Invalid regex patterns are silently skipped.

## Built-in Default Rules

These rules are seeded into the database on first startup (only if no rules exist yet). They provide a sensible baseline.

### Block (priority 1--4)

| Priority | Pattern              | Description            |
| -------- | -------------------- | ---------------------- |
| 1        | `^rm -rf /$`         | Remove root filesystem |
| 2        | `mkfs\.`             | Format filesystem      |
| 3        | `dd if=.* of=/dev/`  | Raw disk write         |
| 4        | `:\(\)\{.*:\|:&\};:` | Fork bomb              |

### Confirm (priority 10--15)

| Priority | Pattern     | Description                |
| -------- | ----------- | -------------------------- |
| 10       | `sudo .*`   | Sudo commands              |
| 11       | `rm -rf `   | Recursive force delete     |
| 12       | `chmod 777` | World-writable permissions |
| 13       | `shutdown`  | System shutdown            |
| 14       | `reboot`    | System reboot              |
| 15       | `kill -9`   | Force kill process         |

### Warn (priority 20--23)

| Priority | Pattern           | Description         |
| -------- | ----------------- | ------------------- |
| 20       | `apt install`     | APT package install |
| 21       | `pip install`     | Pip package install |
| 22       | `npm install`     | NPM package install |
| 23       | `curl .* \| bash` | Piped remote script |

You can add, edit, disable, or delete these rules through the web panel or directly in the `security_rules` database table.

## Per-Node Rule Overrides

Rules can be **global** (apply to all nodes) or **node-specific** (apply to a single node).

### How Inheritance Works

1. Global rules have `node_id = NULL`. They apply to every node.
1. Node-specific rules have a `node_id` set. They apply only to that node.
1. When a node-specific rule has the **same pattern** as a global rule, the node-specific rule **overrides** the global one for that node.
1. Rules are sorted by priority (lowest first). The first match wins.

### Example Scenario

```
Global rules:
  sudo .*  → confirm  (priority 10)
  rm -rf   → confirm  (priority 11)

GPU Server overrides:
  sudo .*  → allow    (priority 10)   ← overrides global for this node

Prod Server overrides:
  DROP TABLE → block  (priority 5)    ← adds new rule for this node
```

Result:

- **GPU Server**: `sudo apt update` is allowed (node override). `rm -rf /tmp` still requires confirmation (global rule, no override).
- **Prod Server**: `DROP TABLE users` is blocked (node-specific rule). `sudo service restart` requires confirmation (global rule).
- **Other nodes**: Both `sudo` and `rm -rf` require confirmation (global rules only).

### Creating Node Overrides

In the web panel, navigate to **Security Rules**, select a node, and add a rule with the same pattern but a different level. The `source_rule_id` field can optionally reference the global rule being overridden for traceability.

## Confirm Token Mechanism

When a command matches a **confirm**-level rule, Shuttle does not execute it. Instead, it returns a response containing:

- The matched rule description
- A one-time **confirm token**

### How Bypass Works

1. The AI assistant receives the confirm response and presents it to the user.
1. The user approves the command.
1. The AI re-submits the same `ssh_run` call with the `confirm_token` parameter.
1. Shuttle validates the token:
   - Token must exist in the in-memory store
   - Token must match the exact same command and node
   - Token must not be expired (default TTL: 300 seconds / 5 minutes)
1. If valid, the token is consumed (one-time use) and the command executes.
1. Block-level rules **cannot** be bypassed, even with a valid token.

### Token Properties

- Generated using `secrets.token_urlsafe(32)` (cryptographically random)
- Stored in-memory only (not persisted to database)
- Single-use: consumed on validation regardless of outcome
- TTL: 300 seconds by default
- Lazy cleanup: expired tokens are pruned when the store exceeds 100 entries

## Best Practices

1. **Start with the defaults.** The built-in rules cover the most common dangerous operations. Add rules as you discover patterns specific to your environment.

1. **Use block sparingly.** Block rules cannot be bypassed. Reserve them for truly catastrophic commands (disk wipe, fork bomb). For most risky commands, confirm is a better choice.

1. **Tighten prod, loosen dev.** Use per-node overrides to allow `sudo` on development servers while keeping it at confirm on production.

1. **Be specific with patterns.** `rm -rf /` (with anchor) is better than `rm` (too broad). Test your regex against expected commands before deploying.

1. **Use priority to control ordering.** Lower numbers are evaluated first. Place block rules at low priorities (1--9), confirm rules in the middle (10--19), and warn rules higher (20+).

1. **Review the Activity log.** The web panel shows which rules were triggered and whether commands were bypassed. Use this data to tune your rules over time.

1. **Disable rather than delete.** Each rule has an `enabled` flag. Disable a rule to stop it from matching without losing the configuration.
