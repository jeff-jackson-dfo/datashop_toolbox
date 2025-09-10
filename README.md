The ocean data group at the Bedford Institute of Oceanography is responsible for archiving oceanographic data and assisting with its data management and processing.

For a few decades now it has been using an in-house data file format specification called ODF (Ocean Data Format). 
This specification needed to be revised. 

You can find the most recent version of this specification here: [ODF Specification Verion 3.0](./ODF_File_Specification.md)

The goal of this project is to replace structured code that was written in a proprietary language for handling ODF files with opensource object-oriented code written in Python.

### INSTALLATION

Installing on Windows using pip:

    C:\> pip install datashop_toolbox-<insert version e.g. 0.9.2>-py3-none-any.whl

Importing and using the package within a terminal window:

    from odf_toolbox.odfhdr import OdfHeader
    from odf_toolbox.metadata_report import generate_report

