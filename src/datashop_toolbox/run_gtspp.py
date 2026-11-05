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
    # QF,
    # Bathymetry,
    # NetCDFBathymetry,
    # Stage1Config,
    # Station,
    Stage1Config,
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

odf_folder = Path('C:/DFO-MPO/DEV/Testing/data/HUD2008004/')
stations = load_stations(odf_folder)
run_stage1(stations, Stage1Config())
profiles = load_profiles(stations)
run_stage2(profiles, Stage2Config())
save_stage2_to_odf(profiles, "qc_odf")
