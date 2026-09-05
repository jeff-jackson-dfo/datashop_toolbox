# `datashop_toolbox` / `odf_oracle` — Reference

> **Status:** Draft, generated from the in-code docstrings.
> **Diátaxis quadrant:** [Reference](https://diataxis.fr/reference/) — this document is
> information-oriented and describes the toolbox's public interface as it exists in code.
> It is not a tutorial (see a future `doc/tutorials.md`) and not a how-to guide (see a
> future `doc/how-to.md`); it does not explain *why* the toolbox is built this way (see a
> future `doc/explanation.md`). Its only job is to be an accurate, complete, and
> consistently structured description of the API.

## About this document

This reference is organized around the codebase's own structure — one subsection per
Python module, in the order a reader would encounter them when browsing `src/`. Each
module entry lists:

- a one-line summary (from the module's own docstring, where one exists),
- its public classes, with their constructor and methods, and
- its public module-level functions.

Signatures and descriptions are pulled directly from the current source and docstrings,
so this document should be regenerated whenever the underlying code changes materially —
it is not meant to be hand-maintained prose. Private/internal helpers (names beginning
with a single underscore) are still listed where they materially affect how a class
behaves, since maintainers are a primary audience for this reference; genuinely
implementation-only helpers are omitted only where doing so doesn't lose information a
caller would need. Qt-Designer–generated `ui_*.py` files are excluded, since their
docstrings are regenerated automatically and are not hand-maintained.

## Packages covered

| Package | Location | Purpose |
|---|---|---|
| [`datashop_toolbox`](#datashop_toolbox) | `src/datashop_toolbox/` | ODF header data model, CTD/thermograph processing pipelines, interactive QC tooling, and supporting file-format utilities. |
| [`datashop_toolbox.gui`](#datashop_toolboxgui) | `src/datashop_toolbox/gui/` | PySide6 widgets and dialogs used by the toolbox's interactive tools (ODF metadata entry, RBR→ODF conversion). |
| [`odf_oracle`](#odf_oracle) | `src/odf_oracle/` | Loaders that write a populated `OdfHeader` object into the ODF_ARCHIVE Oracle database, plus the connection-pool and value-conversion helpers they depend on. |

---

