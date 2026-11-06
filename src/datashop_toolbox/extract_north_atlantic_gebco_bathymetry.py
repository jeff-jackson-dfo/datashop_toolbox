from pathlib import Path

import xarray as xr

# 1. Open the global GEBCO 2026 sub-ice netCDF file (utilizing lazy-loading)
global_file_path = Path('C:/DFO-MPO/DEV/Bathymetry/GEBCO_2026_sub_ice.nc')
ds = xr.open_dataset(global_file_path)

# 2. Define your target bounding box coordinates
# Longitude uses negative numbers for West (42 W to 100 W becomes -100 to -42)
lat_min, lat_max = 35.0, 80.0
lon_min, lon_max = -100.0, -42.0

# 3. Subset the data using .sel() and slice()
# Note: GEBCO coordinates are typically monotonically increasing ('lat' and 'lon')
subset_ds = ds.sel(
    lat=slice(lat_min, lat_max),
    lon=slice(lon_min, lon_max)
)

# 4. Save your region of interest to a new, much smaller NetCDF file
output_file_path = "GEBCO_2026_subset_35N_80N_100W_42W.nc"
subset_ds.to_netcdf(output_file_path)

print(f"Subset successfully saved to {output_file_path}")
