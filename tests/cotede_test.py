import cotede
# from cotede import datasets, qctests
# import numpy as np
# import pandas as pd

# import oceansdb
# import seabird
from seabird.cnv import fCNV
from seabird.qc import fProfileQC

# import gsw

import re

# oceansdb.CARS()['sea_water_temperature']
# oceansdb.WOA()['sea_water_temperature']
# oceansdb.ETOPO()['topography']


## Use CoTeDe test CTD dataset
# data = cotede.datasets.load_ctd()
# print("The variables are: ", ", ".join(sorted(data.keys())))
# print("There is a total of {} observed depths.".format(len(data["TEMP"])))
# pqc = cotede.ProfileQC(data, 'gtspp')
# print(pqc.keys())
# print('Temperature:')
# print(pqc['TEMP'])
# print(pqc.flags['TEMP'])
# print('Salinity:')
# print(pqc['PSAL'])
# print(pqc.flags['PSAL'])
###################################

## Use a real CTD dataset from the seabird package
# profile = fCNV('dPIRX003.cnv')
# print(profile.keys())
# print(profile.attributes)
# print(profile['TEMP'])
# print(profile['PSAL'])
# print(profile['PRES'])

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
    cnv_file = './sampledata/cnv/Dat4805001.CNV'
    profile = fCNV(cnv_file)
    # profile = fProfileQC('dat4805001.cnv', cfg='gtspp')
    # print(profile.keys())
    # print(profile.flags.keys())
    # print(profile.flags['TEMP'])
    # print(profile.flags['PSAL'])
    # print(profile.flags['PRES'])
    # print(profile['DEPTH'])
    profile = fix_sigma_theta(profile)
    # print(profile.keys())
    pqc = cotede.ProfileQC(profile, 'gtspp')
    # print(pqc.attributes)
    # print(pqc.keys())
    # print(pqc['sigma_theta00'])
    # print(profile.__getitem__('timeS'))
    # print(profile.flags['TEMP'].keys())

else:
    ## Use a real BIO CTD dataset
    profile = fCNV('dat4805001.cnv')
    # print(profile.keys())
    # print(profile.attributes)
    # print(profile['TEMP'])
    # print(profile['PSAL'])
    # print(profile['PRES'])
    # print(profile['DEPTH'])
    pqc = cotede.ProfileQC(profile)
    # print(pqc['TEMP'])
    # print(pqc.flags['TEMP'])

# Convert the profile (dict) to a pandas DataFrame
# df = profile.as_DataFrame()
# print(df.head())

# pqc = cotede.ProfileQC(profile, 'gtspp')
# print(pqc.keys())
# print(pqc['sea_water_temperature'])
# pqc.flags['sea_water_salinity']
# pqc.flags['sea_water_salinity']['gradient']
# pqc = cotede.ProfileQC(profile, 'cotede')
# pqc = cotede.ProfileQC(profile, {'sea_water_temperature': {'gradient': {'threshold': 6}}})

