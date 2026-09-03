import pandas as pd


def read_seaodf_ini():
    """Parse the shared ``seaodf.ini`` parameter mapping file.

    Reads the CTDDAP ``seaodf.ini`` file from its fixed network path,
    skipping blank lines and lines beginning with ``"REM"``, and
    splits each remaining line into 8 comma-separated fields (padding
    with empty strings if fewer are present).

    Returns:
        A DataFrame with one row per parameter mapping and columns
        ``sbe_code``, ``odf_code``, ``odf_name``, ``data_type``,
        ``format_type``, ``width``, ``precision``, and ``description``.
    """

    rows = []
    filepath = '//ENT.dfo-mpo.ca/DFO-MPO/GROUP/NAT_Shares/DFO/EOS/SSPPI/BioDataSvc/ARC/CTDDAP/CTDSystemSoftware/CTDDAP/bio_exe/seaodf.ini'  # noqa: E501

    with open(filepath, encoding='iso-8859-1', newline='') as f:
        for raw_line in f:
            # Normalize for checks
            stripped = raw_line.strip()
            lstripped_upper = raw_line.lstrip().upper()

            # Skip blank lines or lines that start with 'REM' (case-insensitive, ignoring leading spaces)
            if not stripped or lstripped_upper.startswith('REM'):
                continue

            # Split on the first 7 commas; keep the rest (including commas) in the 8th field
            parts = raw_line.rstrip('\n\r').split(',', 7)

            # Pad with empty strings if fewer than 8 fields
            if len(parts) < 8:
                parts += [''] * (8 - len(parts))

            # Optional: trim whitespace for each field
            parts = [p.strip() for p in parts]

            rows.append(parts)

    # Build DataFrame
    seaodf_df = pd.DataFrame(rows, columns=[
        "sbe_code","odf_code","odf_name","data_type","format_type","width","precision","description"
    ])
    
    return seaodf_df


def main():

    df = read_seaodf_ini()
    print(df)

if __name__ == "__main__":
    main()
