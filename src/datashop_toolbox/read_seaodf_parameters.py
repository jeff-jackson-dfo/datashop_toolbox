import pandas as pd
from pathlib import Path

def read_seaodf_parameters() -> pd.DataFrame:

    seaodf_df = pd.DataFrame()
    
    filepath = Path.cwd() / 'src/datashop_toolbox/lookups' / 'seaodf_parameters.csv'
    print(filepath)
    
    seaodf_df = pd.read_csv(str(filepath), encoding='iso-8859-1')
    
    return seaodf_df


def main():

    df = read_seaodf_parameters()
    print(df)

if __name__ == "__main__":
    main()
