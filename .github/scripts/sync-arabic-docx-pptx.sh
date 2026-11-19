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
  local ver
  ver="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("version") or "none")' "$dir/.claude-plugin/plugin.json" 2>/dev/null || echo none)"
  printf -- '- `%s` from %s at `%s` (source version: %s)\n' "$skill" "${url%.git}" "$(git -C "$dir" rev-parse --short HEAD)" "$ver"
}

{
  echo "# Sources"
  echo
  echo "Do not edit the skills here. They are copied by \`.github/workflows/sync-arabic-docx-pptx.yml\` from:"
  echo
  sync_skill "$SRC_DOCX" arabic-docx
  sync_skill "$SRC_PPTX" arabic-pptx
} > "$TMP/SOURCES.md"
cp "$TMP/SOURCES.md" "$PLUGIN/SOURCES.md"

changed=0
if [ -n "$(git -C "$ROOT" status --porcelain -- plugins/arabic-docx-pptx/skills)" ] && [ "$tracked" -gt 0 ]; then changed=1; fi

# Version: add 0.1.0 when plugin.json has none; otherwise bump the patch number when skills changed.
python3 - "$PLUGIN/.claude-plugin/plugin.json" "$changed" <<'PY'
import json, sys
p, changed = sys.argv[1], sys.argv[2] == "1"
d = json.load(open(p, encoding="utf-8"))
old = d.get("version")
if not old:
    d["version"] = "0.1.0"
elif changed:
    a, b, c = old.split(".")
    d["version"] = f"{a}.{b}.{int(c) + 1}"
if d.get("version") != old:
    # keep "version" right after "name"
    out = {"name": d["name"], "version": d["version"]}
    out.update({k: v for k, v in d.items() if k not in out})
    open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("version:", old, "->", d["version"])
PY
