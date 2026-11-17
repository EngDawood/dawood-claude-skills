#!/usr/bin/env bash
# Copies the find-oss-alternative skill (repo root is the skill) into plugins/find-oss-alternative.
# Source repo is public. Override with SRC (a git URL or local path) for testing.
# Skips assets/ and docs/ (demo video and report page), which the skill does not need.
# Bumps the plugin patch version when skill files changed, because plugin updates need a new version.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$ROOT/plugins/find-oss-alternative"
SKILL="$PLUGIN/skills/find-oss-alternative"
SRC="${SRC:-https://github.com/lumpinif/find-oss-alternative.git}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

tracked="$(git -C "$ROOT" ls-files -- plugins/find-oss-alternative/skills | wc -l)"

git clone --quiet --depth 1 "$SRC" "$TMP/src"
[ -f "$TMP/src/SKILL.md" ] || { echo "missing SKILL.md in $SRC" >&2; exit 1; }

rm -rf "$SKILL"
mkdir -p "$SKILL"
for item in SKILL.md LICENSE package.json references scripts templates examples; do
  [ -e "$TMP/src/$item" ] && cp -a "$TMP/src/$item" "$SKILL/$item"
done

ver="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("version") or "none")' "$TMP/src/package.json" 2>/dev/null || echo none)"
{
  echo "# Sources"
  echo
  echo "Do not edit the skill here. It is copied by \`.github/workflows/sync-find-oss-alternative.yml\` from:"
  echo
  printf -- '- `find-oss-alternative` from %s at `%s` (source version: %s)\n' "${SRC%.git}" "$(git -C "$TMP/src" rev-parse --short HEAD)" "$ver"
} > "$PLUGIN/SOURCES.md"

changed=0
if [ -n "$(git -C "$ROOT" status --porcelain -- plugins/find-oss-alternative/skills)" ] && [ "$tracked" -gt 0 ]; then changed=1; fi

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
    out = {"name": d["name"], "version": d["version"]}
    out.update({k: v for k, v in d.items() if k not in out})
    open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("version:", old, "->", d["version"])
PY
