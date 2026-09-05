# Reference-doc generation pipeline

Three small scripts that turn the docstrings already in `datashop_toolbox` and
`odf_oracle` into `doc/reference.md`. Nothing here is hand-maintained prose —
if the docstrings change, re-run the pipeline and the doc updates with them.

## Files

| File | Role |
|---|---|
| `extract.py` | Reads one `.py` file with `ast`, prints a JSON summary of its module docstring, classes (bases, docstring, methods with signatures), and top-level functions. |
| `build_doc.py` | Reads the JSON files out of `dt/`, `oracle/`, and `gui/` subfolders of the current directory, groups them into logical sections, and writes `section_datashop_toolbox.md`, `section_odf_oracle.md`, and `section_gui.md`. |
| `preamble.md` | The hand-written Diátaxis framing/intro that goes at the top of the final document. |
| `run_all.sh` | Orchestrates the two scripts end-to-end (macOS/Linux/Git Bash) and produces a single `reference.md`. |
| `run_all.ps1` | Windows PowerShell equivalent of `run_all.sh` — no WSL or Git Bash required. |

## Quick start

**macOS / Linux / Git Bash:**

```bash
chmod +x run_all.sh
./run_all.sh /path/to/datashop_toolbox/src
```

**Windows (PowerShell):**

```powershell
.\run_all.ps1 -SrcPath C:\path\to\datashop_toolbox\src
```

If script execution is blocked by your machine's execution policy, run once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

(This only affects the current PowerShell session — it doesn't change any
system-wide setting.)

Both scripts expect the standard repo layout:

```
<src>/datashop_toolbox/*.py
<src>/datashop_toolbox/gui/*.py
<src>/odf_oracle/*.py
```

It writes `reference.md` in the directory you ran it from. Copy that into
`doc/reference.md` in the repo (or point the script's output redirection
there directly).

`ui_*.py` files (Qt-Designer-generated) are skipped automatically, since
their content — docstrings included — gets overwritten on the next
`pyside6-uic` run.

## A note on the Windows script

`run_all.ps1` mirrors `run_all.sh` line-for-line in behavior, with two
Windows-specific adjustments baked in:

- It writes every intermediate and final file as UTF-8 **without** a byte
  order mark. Windows PowerShell 5.1's `Out-File -Encoding utf8` adds a BOM,
  which breaks `json.load()` on the Python side — so the script captures
  subprocess output directly and writes it with `.NET`'s
  `UTF8Encoding($false)` instead.
- It sets `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` before invoking Python,
  so a non-ASCII character in any docstring can't crash the extraction with
  a console-code-page encoding error.
- It picks up whichever of the `py` launcher or `python` is on `PATH`.

It was reviewed carefully for syntax but not executed against a live
PowerShell install (this environment doesn't have one available) — if
something doesn't run cleanly on your machine, let me know what error you
see and I'll fix it.

## Running the pieces by hand

If you want to inspect or tweak one file at a time instead of running the
whole pipeline:

```bash
# Extract one module to JSON
python3 extract.py ../src/datashop_toolbox/basehdr.py > basehdr.json

# Extract a whole folder into a subfolder named `dt`
mkdir -p dt
for f in ../src/datashop_toolbox/*.py; do
    name=$(basename "$f" .py)
    [[ "$name" == ui_* ]] && continue
    python3 extract.py "$f" > "dt/$name.json"
done
```

`build_doc.py` expects exactly three subfolders in its working directory —
`dt/`, `oracle/`, and `gui/` — each populated the same way, then run:

```bash
python3 build_doc.py
```

## Customizing the grouping

`build_doc.py` hard-codes which module goes under which heading (e.g. "ODF
Header Classes", "MTR / Thermograph Processing") in the `groups`,
`oracle_groups`, and `gui_groups` dictionaries near the top of each section's
build block. Any module present in the extracted JSON but *not* listed in one
of these dictionaries is automatically swept into an "Other" section, so
adding a new file to the package won't cause it to silently disappear from
the reference — it'll just show up under "Other" until you file it properly.

## Requirements

- Python 3.9+ (uses `ast.unparse`)
- No third-party dependencies for either script
