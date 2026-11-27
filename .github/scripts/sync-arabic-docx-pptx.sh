#!/usr/bin/env bash
# Copies every skill of the single source repo into plugins/arabic-docx-pptx and takes its version.
# Source repo is public. Override with SRC (a git URL or local path) and SRC_REF (branch or tag) for testing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$ROOT/plugins/arabic-docx-pptx"
SRC="${SRC:-https://github.com/EngDawood/arabic-docx-pptx-skills.git}"
SRC_REF="${SRC_REF:-}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --quiet --depth 1 ${SRC_REF:+--branch "$SRC_REF"} "$SRC" "$TMP/src"
[ -d "$TMP/src/skills" ] || { echo "missing skills/ in $SRC" >&2; exit 1; }

mkdir -p "$PLUGIN/.claude-plugin"
rm -rf "$PLUGIN/skills"
cp -a "$TMP/src/skills" "$PLUGIN/skills"

ver="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$TMP/src/.claude-plugin/plugin.json")"

{
  echo "# Sources"
  echo
  echo "Do not edit the skills here. They are copied by \`.github/workflows/sync-arabic-docx-pptx.yml\` from:"
  echo
  printf -- '- `%s` at `%s` (source version: %s)\n' "${SRC%.git}" "$(git -C "$TMP/src" rev-parse --short HEAD)" "$ver"
  for d in "$PLUGIN"/skills/*/; do printf -- '  - skill `%s`\n' "$(basename "$d")"; done
} > "$PLUGIN/SOURCES.md"

# The plugin version follows the source version (plugin updates need a new number).
python3 - "$PLUGIN/.claude-plugin/plugin.json" "$ver" <<'PY'
import json, sys
p, ver = sys.argv[1], sys.argv[2]
d = json.load(open(p, encoding="utf-8"))
old = d.get("version")
if old != ver:
    out = {"name": d["name"], "version": ver}
    out.update({k: v for k, v in d.items() if k not in out})
    open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("version:", old, "->", ver)
PY
