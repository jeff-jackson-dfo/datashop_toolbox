"""
datashop_toolbox package initialization.

IMPORTANT DESIGN RULE:
- __init__.py must NEVER import modules that import this package again
- GUI and workflow modules are intentionally NOT imported here
- This prevents circular imports and third-party side-effects
"""

# ---- Core data structures (safe, no GUI, no workflows) ----

from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.compasshdr import CompassCalHeader
from datashop_toolbox.cruisehdr import CruiseHeader
from datashop_toolbox.eventhdr import EventHeader
from datashop_toolbox.generalhdr import GeneralCalHeader
from datashop_toolbox.historyhdr import HistoryHeader
from datashop_toolbox.instrumenthdr import InstrumentHeader
from datashop_toolbox.metadata_report import generate_report
from datashop_toolbox.meteohdr import MeteoHeader
from datashop_toolbox.odfhdr import OdfHeader
from datashop_toolbox.parameterhdr import ParameterHeader
from datashop_toolbox.polynomialhdr import PolynomialCalHeader
from datashop_toolbox.qualityhdr import QualityHeader
from datashop_toolbox.recordhdr import RecordHeader
from datashop_toolbox.records import DataRecords
from datashop_toolbox.select_metadata_file_and_data_folder import MainWindow, SubWindowOne
from datashop_toolbox.thermograph import ThermographHeader
from datashop_toolbox.validated_base import ValidatedBase

# ---- Public API ----

__all__ = [
    "BaseHeader",
    "CompassCalHeader",
    "CruiseHeader",
    "EventHeader",
    "GeneralCalHeader",
    "HistoryHeader",
    "InstrumentHeader",
    "MeteoHeader",
    "OdfHeader",
    "ParameterHeader",
    "PolynomialCalHeader",
    "QualityHeader",
    "RecordHeader",
    "DataRecords",
    "ValidatedBase",
    "ThermographHeader",
    "generate_report",
    "MainWindow",
    "SubWindowOne",
]

# ---- Optional runtime feedback ----
print("✅ datashop_toolbox core API loaded (GUI and workflows are lazy-loaded)")
