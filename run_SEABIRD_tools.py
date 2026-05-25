# import seabird
# from seabird.qc import fProfileQC
# from gsw import z_from_p
import gsw

from seabird.cnv import fCNV

print(gsw.__version__)
cnv_file_location = "./sampledata/cnv/D900a108.cnv"
profile = fCNV(cnv_file_location)

print(f"Header: {profile.attributes.keys()}")
print(f"Data: {profile.keys()}")

# df = profile.as_DataFrame()
# print(df.head())