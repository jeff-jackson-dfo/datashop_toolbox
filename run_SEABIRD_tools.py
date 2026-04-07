# import seabird
from seabird.cnv import fCNV
# from seabird.qc import fProfileQC
# from gsw import z_from_p
import gsw

print(gsw.__version__)
cnv_file_location = "./sampledata/cnv/D900a108.cnv"
profile = fCNV(cnv_file_location)

print("Header: %s" % profile.attributes.keys())
print("Data: %s" % profile.keys())

# df = profile.as_DataFrame()
# print(df.head())