> Note: development was performed in the project's
> root folder using a virtual environment created 
> by uv.

# Below are the Steps used to Generate the Package's Documentation

## Installed Required `mkdocs` Packages
```powershell
(venv) PS C:\Dev\GitHub\datashop_toolbox> uv pip install mkdocs
(venv) PS C:\Dev\GitHub\datashop_toolbox> uv pip install "mkdocstrings[python]"
(venv) PS C:\Dev\GitHub\datashop_toolbox> uv pip install mkdocs-material
```

## Created the Docstrings
The docstrings were created using the Google-style 
because it involves less text (cleaner) and it
is the preferred style for Mkdocs.

Once docstrings are created for say a module
called `tabulate`, one can access the info
using the help command:
```python
>>> help(tabulate)
```

## Create the Mkdocs Structure for Your Project
```powershell
(venv) PS C:\Dev\GitHub\datashop_toolbox> mkdocs new .
```

## Updated the `mkdocs.yml` File

### 1. Changed the site_name

```yaml
site_name: My Docs
```

to

```yaml
site_name: Datashop Toolbox Docs
```

### 2. Added required functionality

```yaml
site_name: Datashop Toolbox Docs

theme:
  name: "material"
  features:
    - content.code.copy  # This enables the copy button globally

plugins:
  - mkdocstrings

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.mark
  
```

## Created New Markdown Files

The only Markdown file that exists when you run
mkdocs the first time is index.md; which needs
to be modified as it is the home page for the
documentation.

It is highly recommended that documentation follow 
the best practice for project documentation as 
described by Daniele Procida in the 
[Diátaxis documentation framework](https://diataxis.fr/)
and consists of four separate parts:

1. [Tutorials](tutorials.md)
2. [How-To Guides](how-to-guides.md)
3. [Reference](reference.md)
4. [Explanation](explanation.md)

Once these four documents have been created,
navigation to them should be added in the
mkdocs.yml file, like so:

```yaml
site_name: Datashop Toolbox Docs

theme:
  name: "material"
  features:
    - content.code.copy  # This enables the copy button globally

plugins:
  - mkdocstrings

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.mark

nav:
  - Datashop Toolbox Docs: index.md
  - tutorials.md
  - How-To Guides: how-to-guides.md
  - reference.md
  - explanation.md
```

## Check Documentation 

```powershell
(venv) PS C:\DEV\GitHub\datashop_toolbox> mkdocs serve

 │  ⚠  Warning from the Material for MkDocs team
 │
 │  MkDocs 2.0, the underlying framework of Material for MkDocs,
 │  will introduce backward-incompatible changes, including:
 │
 │  × All plugins will stop working – the plugin system has been removed
 │  × All theme overrides will break – the theming system has been rewritten
 │  × No migration path exists – existing projects cannot be upgraded
 │  × Closed contribution model – community members can't report bugs
 │  × Currently unlicensed – unsuitable for production use
 │
 │  Our full analysis:
 │
 │  https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/

INFO    -  Building documentation...
INFO    -  Cleaning site directory
INFO    -  The following pages exist in the docs directory, but are not included in the "nav" configuration:
             - generating_documentation.md
INFO    -  Documentation built in 0.68 seconds
INFO    -  [15:05:39] Watching paths for changes: 'docs', 'mkdocs.yml'
INFO    -  [15:05:39] Serving on http://127.0.0.1:8000/
```

One of the more useful features of Mkdocs is that 
during 