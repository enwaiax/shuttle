---
name: shuttle-gpu-diagnostics
description: Diagnose remote GPU nodes safely through Shuttle.
---

# Shuttle GPU diagnostics

Use after loading `shuttle-safe-remote-ops`.

1. Confirm the requested GPU node exactly; never substitute a different SKU or host.
2. Run read-only checks first: `nvidia-smi`, GPU processes, memory/disk, container state, and recent NVIDIA Xid messages.
3. Preserve one Shuttle conversation identity across the diagnostic sequence so working-directory state is isolated from other agents.
4. Summarize evidence before proposing mutation.
5. Any kill, restart, package install, driver action, configuration edit, or reboot must enter Shuttle human approval. Show node, exact command, expected impact, and rollback.
6. After approval, retry only the exact approved command with its `approval_id`.
7. Return observed facts separately from recommendations and cite the Shuttle audit/approval ID.
