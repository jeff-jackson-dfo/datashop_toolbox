__author__ = "Guilherme Castelao"
__email__ = "guilherme@castelao.net"

# --- core imports ---
from .cnv import CNV, fCNV
from .qc import fProfileQC
from .exceptions import CNVError

__all__ = [
    "CNV",
    "fCNV",
    "fProfileQC",
    "CNVError",
]

# --- version handling ---
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:  # Python < 3.8
    from importlib_metadata import version, PackageNotFoundError  # type: ignore

try:
    __version__ = version("seabird")
except PackageNotFoundError:
    try:
        from .version import __version__
    except ImportError:
        __version__ = "0.0.0-dev"

# --- dependency check (optional but useful) ---
def _check_dependencies():
    missing = []

    try:
        import numpy  # noqa
    except ImportError:
        missing.append("numpy")

    try:
        import pandas  # noqa
    except ImportError:
        missing.append("pandas")

    try:
        import gsw  # noqa
    except ImportError:
        missing.append("gsw")

    if missing:
        raise ImportError(
            f"Missing required seabird dependencies: {', '.join(missing)}"
        )

# Run dependency check on import (optional)
try:
    _check_dependencies()
    print(f"✅ Seabird version {__version__} successfully loaded")
    

except ImportError as e:
    print(f"⚠️ seabird dependency warning: {e}")