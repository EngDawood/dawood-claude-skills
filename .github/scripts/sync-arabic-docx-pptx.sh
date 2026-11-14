#!/usr/bin/env bash
# Copies the skills of the two source repos into plugins/arabic-docx-pptx.
# Source repos are public. Override with SRC_DOCX / SRC_PPTX (a git URL or local path) for testing.
# Bumps the plugin patch version when skill files changed, because plugin updates need a new version.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$ROOT/plugins/arabic-docx-pptx"
SRC_DOCX="${SRC_DOCX:-https://github.com/EngDawood/claude-doc-to-docx-arabic.git}"
SRC_PPTX="${SRC_PPTX:-https://github.com/EngDawood/arabic-pptx-skill.git}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$PLUGIN/skills"
tracked="$(git -C "$ROOT" ls-files -- plugins/arabic-docx-pptx/skills | wc -l)"

sync_skill() { # url skill-name
  local url="$1" skill="$2" dir="$TMP/$2"
  git clone --quiet --depth 1 "$url" "$dir"
  [ -f "$dir/skills/$skill/SKILL.md" ] || { echo "missing skills/$skill/SKILL.md in $url" >&2; exit 1; }
  rm -rf "$PLUGIN/skills/$skill"
  cp -a "$dir/skills/$skill" "$PLUGIN/skills/$skill"
  printf -- '- `%s` from %s at `%s`\n' "$skill" "${url%.git}" "$(git -C "$dir" rev-parse --short HEAD)"
}

{
  echo "# Sources"
  echo
  echo "Do not edit the skills here. They are copied by \`.github/workflows/sync-arabic-docx-pptx.yml\` from:"
  echo
  sync_skill "$SRC_DOCX" doc-to-word-rtl
  sync_skill "$SRC_PPTX" arabic-pptx
} > "$TMP/SOURCES.md"
cp "$TMP/SOURCES.md" "$PLUGIN/SOURCES.md"

if [ -n "$(git -C "$ROOT" status --porcelain -- plugins/arabic-docx-pptx/skills)" ] && [ "$tracked" -gt 0 ]; then
  python3 - "$PLUGIN/.claude-plugin/plugin.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
a, b, c = d["version"].split(".")
d["version"] = f"{a}.{b}.{int(c) + 1}"
open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("version ->", d["version"])
PY
fi
