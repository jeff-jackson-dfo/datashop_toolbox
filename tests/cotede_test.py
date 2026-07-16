# import gsw
import re

import matplotlib.pyplot as plt

import cotede.qc

# from cotede import datasets, qctests
# import numpy as np
# import pandas as pd
# import oceansdb
from seabird import cnv
from seabird.cnv import fCNV
from seabird.qc import fProfileQC

# oceansdb.CARS()['sea_water_temperature']
# oceansdb.WOA()['sea_water_temperature']
# oceansdb.ETOPO()['topography']


## Use CoTeDe test CTD dataset
# data = cotede.datasets.load_ctd()
# print("The variables are: ", ", ".join(sorted(data.keys())))
# print("There is a total of {} observed depths.".format(len(data["TEMP"])))
# pqc = cotede.ProfileQC(data, 'gtspp')
# ic(pqc.keys())
# ic('Temperature:')
# ic(pqc['TEMP'])
# ic(pqc.flags['TEMP'])
# ic('Salinity:')
# ic(pqc['PSAL'])
# ic(pqc.flags['PSAL'])
###################################

## Use a real CTD dataset from the seabird package
# profile = fCNV('dPIRX003.cnv')
# ic(profile.keys())
# ic(profile.attributes)
# ic(profile['TEMP'])
# ic(profile['PSAL'])
# ic(profile['PRES'])

# Set to True to include QC flags for the dataset
use_qc = True

def fix_sigma_theta(profile: fProfileQC) -> fProfileQC:
    """
    Fix the sigma_theta column names in the profile object to remove the strange character causing issues.
    """
    # Get the index position(s) of specified key(s) in the profile object
    keys = profile.keys()
    idx  = [index for (index, item) in enumerate(keys) if re.match('^sigma', item)]

    for i, x in enumerate(idx):

        # Get the data object for the current sigma_theta column
        d = profile.data[x]

        # Update the name of the current sigma_theta data object
        d.attrs["name"] = f'sigma_theta{i}{i}'

        # Assign the reivsed data object back into profile
        profile.data[x] = d

    return profile


if use_qc:
    
    ## Use a real BIO CTD dataset with QC flags
    cnv_file = './sampledata/cnv/D146a001.CNV'

    data = cnv.fCNV(cnv_file)
    print(data.as_DataFrame().head())
    
    ped = cotede.qc.ProfileQCed(data)
    print(f"ped.keys(): {ped.keys()}")

    profile = fProfileQC(cnv_file, cfg='gtspp_bio') 
    print(f"profile.keys(): {profile.keys()}")
    print(f"profile.flags.keys(): {profile.flags.keys()}")

    # ic(profile.flags.keys())
    # ic(profile['TEMP'])
    # ic(profile.flags['TEMP'])
    # ic(profile['PSAL'])
    # ic(profile.flags['PSAL'])
    # ic(profile['PRES'])
    # ic(profile['DEPTH'])
    # ic(profile.__getitem__('timeS'))

    profile = fix_sigma_theta(profile)
    print(f"profile['sigma_theta00']: {profile['sigma_theta00']}")
    print(f"profile.flags['sigma_theta00']: {profile.flags['sigma_theta00']}")
    plt.plot(profile['sigma_theta00'], profile['DEPTH'], '.')
    plt.gca().invert_yaxis()
    plt.show()

else:

    ## Use a real BIO CTD dataset
    profile = fCNV('dat4805001.cnv')
    # ic(profile.keys())
    # ic(profile.attributes)
    # ic(profile['TEMP'])
    # ic(profile['PSAL'])
    # ic(profile['PRES'])
    # ic(profile['DEPTH'])
    pqc = cotede.ProfileQC(profile)
    # ic(pqc['TEMP'])
    # ic(pqc.flags['TEMP'])

# Convert the profile (dict) to a pandas DataFrame
# df = profile.as_DataFrame()
# ic(df.head())

# pqc = cotede.ProfileQC(profile, 'gtspp')
# ic(pqc.keys())
# ic(pqc['sea_water_temperature'])
# pqc.flags['sea_water_salinity']
# pqc.flags['sea_water_salinity']['gradient']
# pqc = cotede.ProfileQC(profile, 'cotede')
# pqc = cotede.ProfileQC(profile, {'sea_water_temperature': {'gradient': {'threshold': 6}}})

