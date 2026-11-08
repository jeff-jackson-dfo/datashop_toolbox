# Steps to Generate Package Documentation

> Note: development was performed in the project's
> root folder using a virtual environment created
> by uv. The documentation is built with
> [Zensical](https://zensical.org/), the successor to
> Material for MkDocs.

## Install the Required Packages

```powershell
(venv) PS C:\Dev\GitHub\datashop_toolbox> uv pip install zensical
(venv) PS C:\Dev\GitHub\datashop_toolbox> uv pip install mkdocstrings-python
```

`zensical` builds and serves the site and includes the theme.
`mkdocstrings-python` generates the API reference from the
docstrings. No separate `mkdocs` or `mkdocs-material` install
is needed.

## Create the Docstrings

The docstrings are created using the Google-style
because it involves less text (cleaner) and it
is the preferred style for `mkdocstrings`.

Once docstrings are created for say a module
called `tabulate`, one can access the info
using the help command:

```python
>>> help(tabulate)
```

## Create the Zensical Structure for Your Project

For a new project, run the following in the project's root folder:

```powershell
(venv) PS C:\Dev\GitHub\datashop_toolbox> zensical new .
```

This creates a `zensical.toml` configuration file, a `docs` folder
with starter pages, and a GitHub Actions workflow in
`.github/workflows/docs.yml`.

This project already has a `docs` folder and keeps its
configuration in `mkdocs.yml`. Zensical reads that file directly
when there is no `zensical.toml`, so there is no need to convert it.

## Update the `mkdocs.yml` File

### 1. Change the `site_name`

```yaml
site_name: My Docs
```

to

```yaml
site_name: Datashop Toolbox Docs
```

### 2. Set the `site_url`

Add the address where the site will be published. For GitHub
Pages this is `https://<username>.github.io/<repository>/`, and the
trailing slash is required:

```yaml
site_url: https://jeff-jackson-dfo.github.io/datashop_toolbox/
```

### 3. Add Required Functionality

```yaml
site_name: Datashop Toolbox Docs
site_url: https://jeff-jackson-dfo.github.io/datashop_toolbox/

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
  - attr_list
  - md_in_html
  - pymdownx.emoji:
      emoji_index: !!python/name:zensical.extensions.emoji.twemoji
      emoji_generator: !!python/name:zensical.extensions.emoji.to_svg
```

`attr_list`, `md_in_html` and `pymdownx.emoji` enable the
grid cards and icons used on the home and how-to pages.

### 4. Create New Markdown Files

The only Markdown file that exists when you run
`zensical new` the first time is `index.md` (plus a
`markdown.md` example page); `index.md` needs
to be modified as it is the home page for the
documentation.

It is highly recommended that documentation follow
the best practice for project documentation as
described by Daniele Procida in the
[Diátaxis documentation framework](https://diataxis.fr/)
and consists of four separate parts:

1. [Background](background.md)
2. [Tutorials](tutorials.md)
3. [How-To Guides](how-to-guides.md)
4. [Reference](reference.md)

Once these four documents have been created,
navigation to them should be added in the
`mkdocs.yml` file, like so:

```yaml
nav:
  - Datashop Toolbox Docs: index.md
  - background.md
  - tutorials.md
  - How-To Guides: how-to-guides.md
  - Reference: reference.md
  - GTSPP Reference: gtspp_reference.md
```

## View While Editing the Documentation

```powershell
(venv) PS C:\DEV\GitHub\datashop_toolbox> zensical serve
```

Zensical builds the site and serves it on
`http://localhost:8000`.

One of the more useful features of Zensical is that
when working on the documentation locally, any
changes made are automatically rebuilt and shown on the
webpage running on the local webserver.

## Publish the Documentation to GitHub

The documentation is published to GitHub Pages by a GitHub Actions
workflow. Every push to the `master` (or `main`) branch rebuilds the
site with Zensical and deploys it. This replaces the `mkdocs gh-deploy`
command used with MkDocs.

### One-Time Setup

1. Copy the workflow file `docs.yml` into the repository as
   `.github/workflows/docs.yml`.

2. In the repository on GitHub, go to **Settings** > **Pages** and,
   under **Build and deployment**, set **Source** to **GitHub Actions**.

3. Commit and push the workflow file:

```powershell
(venv) PS C:\DEV\GitHub\datashop_toolbox> git add .github/workflows/docs.yml
(venv) PS C:\DEV\GitHub\datashop_toolbox> git commit -m "Add documentation workflow"
(venv) PS C:\DEV\GitHub\datashop_toolbox> git push
```

### Publish Changes

Once the one-time setup is done, publishing is just a push:

```powershell
(venv) PS C:\DEV\GitHub\datashop_toolbox> git add .
(venv) PS C:\DEV\GitHub\datashop_toolbox> git commit -m "Update documentation"
(venv) PS C:\DEV\GitHub\datashop_toolbox> git push
```

Follow the progress on the **Actions** tab of the repository. When the
workflow finishes, the site is available at
`https://<username>.github.io/<repository>/`. The workflow can also be
started by hand from the **Actions** tab (**Documentation** >
**Run workflow**).

### Check the Build Locally

To check that the site builds without errors before pushing:

```powershell
(venv) PS C:\DEV\GitHub\datashop_toolbox> zensical build --clean
```

The generated site is written to the `site` folder.
