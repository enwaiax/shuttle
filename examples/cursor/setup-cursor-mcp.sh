#!/usr/bin/env bash
# Write Shuttle stdio MCP config for Cursor (project-local .cursor/mcp.json).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CURSOR_DIR="$ROOT/.cursor"
OUT="$CURSOR_DIR/mcp.json"

echo "Shuttle → Cursor MCP (stdio)"
echo "Project root: $ROOT"
mkdir -p "$CURSOR_DIR"

if [[ -f "$OUT" ]]; then
  echo "⚠️  $OUT already exists — backing up"
  cp "$OUT" "$OUT.backup.$(date +%Y%m%d%H%M%S)"
fi

cat >"$OUT" <<'EOF'
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"]
    }
  }
}
EOF

echo "✅ Wrote $OUT"
echo ""
echo "Next:"
echo "  1. shuttle node add   # configure SSH nodes"
echo "  2. Restart Cursor"
echo "  3. For HTTP mode instead, see examples/cursor/serve-config.json and docs/mcp-setup.md"
