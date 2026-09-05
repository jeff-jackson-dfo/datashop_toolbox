#!/usr/bin/env bash
# Regenerate doc/reference.md from the current source tree.
#
# Usage:
#   ./run_all.sh /path/to/datashop_toolbox/src
#
# Expects the repo layout:
#   <src>/datashop_toolbox/*.py
#   <src>/datashop_toolbox/gui/*.py
#   <src>/odf_oracle/*.py
#
# Produces reference.md in the current directory.

set -euo pipefail

SRC="${1:?Usage: $0 /path/to/src}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DT_SRC="$SRC/datashop_toolbox"
GUI_SRC="$SRC/datashop_toolbox/gui"
ORACLE_SRC="$SRC/odf_oracle"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/dt" "$WORK/oracle" "$WORK/gui"

extract_dir() {
    local src_dir="$1" out_dir="$2"
    for f in "$src_dir"/*.py; do
        name="$(basename "$f" .py)"
        # Skip Qt-Designer-generated files; their docstrings are
        # regenerated automatically and aren't hand-maintained.
        case "$name" in
            ui_*) continue ;;
        esac
        python3 "$HERE/extract.py" "$f" > "$out_dir/$name.json"
    done
}

echo "Extracting datashop_toolbox ..."
extract_dir "$DT_SRC" "$WORK/dt"

echo "Extracting odf_oracle ..."
extract_dir "$ORACLE_SRC" "$WORK/oracle"

echo "Extracting datashop_toolbox.gui ..."
extract_dir "$GUI_SRC" "$WORK/gui"

echo "Assembling reference.md ..."
cp "$HERE/preamble.md" "$WORK/preamble.md"
(cd "$WORK" && python3 "$HERE/build_doc.py")

cat "$WORK/preamble.md" \
    "$WORK/section_datashop_toolbox.md" \
    "$WORK/section_odf_oracle.md" \
    "$WORK/section_gui.md" \
    | python3 -c "import re,sys; sys.stdout.write(re.sub(r'\n{3,}', '\n\n', sys.stdin.read()).rstrip() + '\n')" \
    > reference.md

echo "Done: $(pwd)/reference.md"
