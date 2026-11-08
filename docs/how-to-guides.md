# How-To Guides

> **Diátaxis quadrant:** [How-to guides](https://diataxis.fr/how-to-guides/) are
> goal-oriented. Each one gives you the steps to reach a specific result and assumes
> you already know the basics. If you are new to the toolbox, start with the
> [tutorials](tutorials.md) instead.

Pick the task you want to accomplish.

## Create and edit ODF files

<div class="grid cards" markdown>

-   :material-file-plus-outline:{ .lg .middle } __Create a new ODF file from scratch__

    ---

    Build an ODF file in Python with `OdfHeader`: fill in the cruise, event and
    instrument headers, define parameters, attach a data frame, and write the file
    to disk.

    [:octicons-arrow-right-24: Create an ODF file](how-to-create-an-odf-file.md)

-   :material-file-edit-outline:{ .lg .middle } __Edit a set of ODF files__

    ---

    Apply the same metadata corrections to every ODF file in a folder, record each
    change in a new History header, and write the revised files to a new folder.

    [:octicons-arrow-right-24: Edit a set of ODF files](how-to-edit-a-set-of-odf-files.md)

</div>

## Quality control

<div class="grid cards" markdown>

-   :material-check-circle-outline:{ .lg .middle } __Run the GTSPP quality control__

    ---

    Apply the GTSPP Stage 1 and Stage 2 tests to a folder of ODF files. You get
    quality-controlled copies with flags, a `QCFF_01` column, and an updated Quality
    header. Your originals are not touched.

    [:octicons-arrow-right-24: Run the GTSPP QC](how-to-run-gtspp-qc.md)

</div>

## Maintain the project

<div class="grid cards" markdown>

-   :material-text-box-outline:{ .lg .middle } __Generate the package documentation__

    ---

    Install the MkDocs packages, create the docstrings, and build this
    documentation site.

    [:octicons-arrow-right-24: Generate the documentation](generating_documentation.md)

</div>

## Looking for something else?

<div class="grid cards" markdown>

-   :material-lightbulb-outline:{ .lg .middle } __Background__

    ---

    Why the ODF format and the processing pipeline work the way they do.

    [:octicons-arrow-right-24: Background](background.md)

-   :material-school:{ .lg .middle } __Tutorials__

    ---

    Installing or trying the toolbox for the first time.

    [:octicons-arrow-right-24: Tutorials](tutorials.md)

-   :material-api:{ .lg .middle } __Reference__

    ---

    Find the class or function you need. The GTSPP modules have their own
    reference.

    [:octicons-arrow-right-24: Reference](reference.md) ·
    [:octicons-arrow-right-24: GTSPP reference](gtspp_reference.md)

</div>

<< [Welcome](index.md) | [Tutorials](tutorials.md) >>
