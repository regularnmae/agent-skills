#!/usr/bin/env bash
# Link the skills into each agent harness already installed here, put agent-mcp
# on PATH, and create the token env file.
#
#   ./install.sh                    # every harness found, plus ~/.local/bin
#   ./install.sh --from-opencode    # also copy tokens out of opencode's config
#   ./install.sh --target DIR       # link into one more skills directory
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
extra=()
from_opencode=0

while [ $# -gt 0 ]; do
  case "$1" in
    --from-opencode) from_opencode=1 ;;
    --target) shift; extra+=("$1") ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown argument $1" >&2; exit 2 ;;
  esac
  shift
done

targets=()
for dir in "$HOME/.config/opencode/skills" "$HOME/.codex/skills" "$HOME/.claude/skills"; do
  [ -d "$(dirname -- "$dir")" ] && targets+=("$dir")
done
targets+=("${extra[@]}")

chmod +x "$root/bin/agent-mcp" "$root/refresh.py"

for target in "${targets[@]}"; do
  mkdir -p "$target"
  for skill in "$root"/skills/*/; do
    name=$(basename -- "$skill")
    mkdir -p "$target/$name"
    # Link the files rather than the directory: a harness that does not follow
    # directory symlinks still finds SKILL.md this way.
    for file in "$skill"*; do
      ln -sfn "$file" "$target/$name/$(basename -- "$file")"
    done
  done
  echo "install.sh: linked $(find "$root/skills" -maxdepth 1 -mindepth 1 -type d | wc -l) skills into $target"
done

mkdir -p "$HOME/.local/bin"
ln -sfn "$root/bin/agent-mcp" "$HOME/.local/bin/agent-mcp"
echo "install.sh: linked agent-mcp into $HOME/.local/bin"

env_file="$HOME/.config/agent-skills/env"
if [ ! -f "$env_file" ]; then
  mkdir -p "$(dirname -- "$env_file")"
  cat > "$env_file" <<'EOF'
# Bearer tokens for the MCP servers, one per line. Fill these in, or re-run
# install.sh --from-opencode to copy them out of opencode's config.
#
# Namespaced on purpose: harnesses export the servers' own *_MCP_TOKEN names
# into the shell, sometimes with tokens that no longer match the live config,
# and those must not shadow what is set here.
AGENT_MCP_BITCOIN_NODE_TOKEN=
AGENT_MCP_MONERO_NODE_TOKEN=
AGENT_MCP_MONERO_WALLET_TOKEN=
AGENT_MCP_LIGHTNING_TOKEN=
AGENT_MCP_SEARXNG_TOKEN=
EOF
  chmod 600 "$env_file"
  echo "install.sh: created $env_file"
fi

if [ "$from_opencode" = 1 ]; then
  python3 - "$root" "$env_file" <<'PY'
import json
import os
import sys

root, env_path = sys.argv[1], sys.argv[2]
registry = json.load(open(os.path.join(root, "servers.json")))
try:
    servers = json.load(open(os.path.expanduser("~/.config/opencode/opencode.json")))["mcp"][
        "servers"
    ]
except (OSError, KeyError) as err:
    raise SystemExit(f"install.sh: cannot read the opencode config: {err}") from None

values = {}
for name, entry in registry.items():
    header = (servers.get(name) or {}).get("headers", {}).get("Authorization", "")
    token = header.split(None, 1)[1] if header.lower().startswith("bearer ") else header
    if token:
        values[entry["token_env"]] = token

lines = open(env_path).read().splitlines()
written, out = set(), []
for line in lines:
    key = line.split("=", 1)[0].strip()
    if key in values:
        out.append(f"{key}={values[key]}")
        written.add(key)
    else:
        out.append(line)
for key, value in values.items():
    if key not in written:
        out.append(f"{key}={value}")

with open(env_path, "w") as handle:
    handle.write("\n".join(out).rstrip("\n") + "\n")
os.chmod(env_path, 0o600)
print(f"install.sh: seeded {len(values)} token(s) into {env_path}")
PY
fi
