#!/usr/bin/env bash
# Zip one package for the marketplace: a single top-level folder with SKILL.md
# at its root, no dotfiles, no symlinks, no binaries -- the shape the store's
# security scan expects.
#
#   ./package.sh               # every package in this directory
#   ./package.sh bitcoin-node  # just one
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

package() {
    local name="$1"
    [ -f "$name/SKILL.md" ] || { echo "package.sh: $name has no SKILL.md" >&2; return 1; }

    python3 - "$name" <<'PY'
import sys
import zipfile
from pathlib import Path

name = sys.argv[1]
root = Path(name)
out = Path(f"{name}.zip")
skip = {".DS_Store", "Thumbs.db", "__pycache__"}

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        if any(part in skip or part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise SystemExit(f"package.sh: {path} is a symlink; the scan rejects those")
        if path.is_file():
            archive.write(path, path.as_posix())

print(f"package.sh: wrote {out} ({out.stat().st_size / 1024:.1f} KiB)")
PY
}

if [ $# -gt 0 ]; then
    for name in "$@"; do package "$name"; done
else
    for dir in */; do
        [ -f "${dir}SKILL.md" ] && package "${dir%/}"
    done
fi
