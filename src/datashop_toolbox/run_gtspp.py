from pathlib import Path

from datashop_toolbox.gtspp_odf_output import (
    # apply_profile_to_odf,
    # build_quality_header,
    # ensure_flag_columns,
    save_stage2_to_odf,
    # verify_written,
    # write_profile_odf,
)
from datashop_toolbox.gtspp_stage1 import (
    QF,
    NetCDFBathymetry,
    # Stage1Config,
    # Station,
    Stage1Config,
    # Bathymetry,
    get_platform_speeds,
    load_stations,
    run_stage1,
)
from datashop_toolbox.gtspp_stage2 import (
    # Profile,
    Stage2Config,
    # Test2,
    # kind_of,
    load_profiles,
    run_stage2,
)

bathy = NetCDFBathymetry(Path('C:/DFO-MPO/DEV/Bathymetry/GEBCO_2026_subset_35N_80N_100W_42W.nc'))

stage1_cfg = Stage1Config(
    max_speed_knots={**get_platform_speeds(), "HUDSON": 14.0},
    bathymetry=bathy,
    land_flag=QF.ERRONEOUS,          # flag a position on land 4 instead of 3
)
stage2_cfg = Stage2Config(
    bathymetry=bathy,
    # spike_thresholds={"temperature": 1.0, "salinity": 0.2},
)

odf_folder = Path('C:/DFO-MPO/DEV/Testing/data/HUD2008004/')
stations = load_stations(odf_folder)
run_stage1(stations, stage1_cfg)
profiles = load_profiles(stations)
run_stage2(profiles, stage2_cfg)
save_stage2_to_odf(profiles, "qc_odf")
