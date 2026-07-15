
"""
fix_btl_header.py

Replaces column names that are too long with shorter versions.

Author: Jeff Jackson
Date: 22-June-2026
"""

import os
import re
from pathlib import Path
import shutil


def fix_header(header: str) -> str:
    """Return the header with the proper spacing between column names."""

    new_header = re.sub('Par/sat/log', '  ParSatLog', header)

    return new_header


def main():

    test = False

    if test:

        head = "    Bottle     Bottle        Date Sbeox0ML/L Sbeox1ML/L      Sal00      Sal11 Potemp090C Potemp190C  Sigma-é00  Sigma-é11       Scan      TimeS       PrDM      T090C      C0S/m      T190C      C1S/m    Sbeox0V    Sbeox1V       AltMPar/sat/log    FlSPuv0       FlSP         Ph   CStarAt0   CStarTr0   Latitude  Longitude     Dz/dtM      DepSM" 
        data = "      1        524168 May 24 2026     6.9422     6.9252    34.0082    34.0121     1.6297     1.5727    27.2048    27.2121      24717   1029.833    160.332     1.6376   2.974963     1.5805   2.970396     2.2282     2.2785       5.67 8.8846e-02     2.0737 1.2584e-01      8.112     0.1406    96.5472   54.21994  -55.02340     -0.005    158.836 (avg)"
        
        new_head = fix_header(head, data)

        print(new_head)
    
    else:

        orig_path = Path.cwd()
        btl_path = Path('C:/DFO-MPO/DEV/AtSea/JC291/CTD/DATASHOP_PROCESSING/Step_2_Apply_Calibrations/BTL/')

        os.chdir(btl_path)

        if not Path('orig').exists():
            os.mkdir('orig')

        btl_files = btl_path.glob('291a*.btl')

        for btl_file in btl_files:

            print(f"Updating BTL file: {btl_file}")
            print(f"Backing up original BTL file: {btl_file, Path(btl_path / 'orig' / (btl_file.stem + '_org.btl'))}")
            shutil.copy(btl_file, Path(btl_path / 'orig' / (btl_file.stem + '_org.btl')))

            # Read the current BTL file and update its column name line
            header_line = 0
            btl_lines = list()
            with open(btl_path / btl_file, 'r', encoding='latin-1') as file:
                for line in file:
                    btl_lines.append(line)
                    if line.startswith('#') or line.startswith('*'):
                        header_line += 1
            new_header = fix_header(btl_lines[header_line])
            btl_lines[header_line] = new_header

            # Write out the modified BTL file
            with open(btl_path / btl_file, "w", encoding="latin-1", newline="") as f:
                f.writelines(btl_lines)

            print(f"Fixed header written to: {btl_path / btl_file}")

        os.chdir(orig_path)


if __name__ == "__main__":
    main()
