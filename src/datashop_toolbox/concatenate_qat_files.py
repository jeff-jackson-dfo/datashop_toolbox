# Author: Jeff Jackson
# Last Updated: 11-FEB-2026

import os
from pathlib import Path


def concatenate_qat_files(mission_number: str, qat_folder_path: str):
    """Concatenate all .qat files in a folder into one CSV file.

    Reads every ``*.qat`` file in ``qat_folder_path``, extracts the
    event number from each filename, and writes a single combined
    ``"<mission_number>_QAT.csv"`` file (in the same folder) with the
    source filename prepended to every data row and the cruise-name
    column removed.

    Args:
        mission_number: Mission number used to name the output file,
            e.g. ``"BCD2025669"``.
        qat_folder_path: Path to the folder containing the ``.qat``
            files to concatenate. This also becomes the current
            working directory and the location of the output file.
    """

    os.chdir(qat_folder_path)

    header_line = ""

    # Get the list of files to concatenate.
    filelist = Path.glob("*.qat")
    print(filelist)

    # Open the output file.
    fout = Path.open(f"{mission_number}_QAT.csv", "w+")

    # Iterate through the list of input files.
    for i, filename in enumerate(filelist):
        # Get the event number from the filename.
        event = filename[5:8]

        print("Processing event: ", event)

        # Open the current input file.
        fin = Path.open(filename)

        # Save the header line from the first file opened, edit it and output to the concatenated file.
        if i == 0:
            with Path.open(filename) as f:
                header_line = f.readline()
            header_line = f"filename,{header_line}"
            fout.write(header_line)

        # Keep track of the number of lines in each QAT file.
        linecount = 0

        # Read in each line of the file and process it.
        for line in fin:
            linecount = linecount + 1

            if linecount != 1:
                # Parse the current line using the comma as the token.
                params = line.split(",")

                # Change the second list parameter to the event number because some files are missing this value.
                params[1] = str(int(event))

                # Delete the cruise name from the list.
                params[0:0] = []

                # Insert the filename in as the first parameter in the list.
                file_minus_ext = filename[0:8]
                params[:0] = [file_minus_ext]

                # Iterate through the list and remove all leading and trailing spaces.
                for j, v in enumerate(params):
                    params[j] = v.strip(" ")

                #  Rejoin the comma parameters separating the value with commas.
                newline = ", ".join(params)
                fout.write(newline)

        fin.close()

        linecount = 0

    fout.close()


def main():
    from pathlib import Path

    qat_path = Path(
        "C:/DFO-MPO/DEV/Data/2025/BCD2025669/DATASHOP_PROCESSING/Step_2_Apply_Calibrations/QAT/"
    )
    concatenate_qat_files("BCD2025669", qat_path)


if __name__ == "__main__":
    main()
