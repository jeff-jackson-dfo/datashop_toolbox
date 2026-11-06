from pathlib import Path

import xarray as xr


def get_bathymetry_for_points(nc_file_path: Path, lats: list[float], lons: list[float]) -> list[float]:
    """
    Retrieves the closest bathymetric values for a list of coordinate pairs
    using fast vectorized lookups.
    
    Parameters:
    nc_file_path (str): Path to the GEBCO NetCDF file.
    lats (list): List of latitudes.
    lons (list): List of longitudes (matching index-for-index with lats).
    
    Returns:
    list: Depth/elevation values in meters.
    """
    # Convert input lists into xarray DataArrays to trigger vectorized lookup
    lat_indices = xr.DataArray(lats, dims="point")
    lon_indices = xr.DataArray(lons, dims="point")
    
    with xr.open_dataset(nc_file_path) as ds:
        # Vectorized lookup using 'nearest' neighbor mapping
        extracted_data = ds['elevation'].sel(
            lat=lat_indices, 
            lon=lon_indices, 
            method="nearest"
        )
        
        # Convert the resulting 1D array back to a standard Python list
        bathymetry_values = extracted_data.values.tolist()
        
    return bathymetry_values


def main():
    # --- Example Usage ---
    gebco_file_path = Path('C:/DFO-MPO/DEV/GitHub/datashop_toolbox/src/datashop_toolbox/lookups/GEBCO_2026_subset_35N_80N_100W_42W.nc')  # noqa: E501
    
    # # Sample lists of matching coordinate pairs
    my_lats = [44.6947, 52.3, 44.7340, 74.5]
    my_lons = [-63.6407 , -55.2, -63.4000, -90.1]
    
    depths = get_bathymetry_for_points(gebco_file_path, my_lats, my_lons)
    
    for lat, lon, depth in zip(my_lats, my_lons, depths, strict=False):
        print(f"Lat: {lat}, Lon: {lon} -> Depth: {depth} m")

if __name__ == "__main__":
    main()