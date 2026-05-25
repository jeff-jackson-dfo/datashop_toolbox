#!/usr/bin/env python

from .bin_spike import Bin_Spike
from .cars_normbias import CARS_NormBias
from .constant_cluster_size import ConstantClusterSize
from .cum_rate_of_change import CumRateOfChange
from .deepest_pressure import DeepestPressure
from .density_inversion import DensityInversion
from .digit_roll_over import DigitRollOver
from .global_range import GlobalRange
from .gradient import Gradient
from .gradient_depthconditional import GradientDepthConditional
from .location_at_sea import LocationAtSea
from .monotonic_z import MonotonicZ
from .profile_envelop import ProfileEnvelop
from .qctests import *  # noqa: F403
from .rate_of_change import RateOfChange
from .regional_range import RegionalRange
from .spike import Spike
from .spike_depthconditional import SpikeDepthConditional
from .stuck_value import StuckValue
from .tukey53H import Tukey53H
from .valid_geolocation import ValidGeolocation
from .woa_normbias import WOA_NormBias

QCTESTS = {
    "Bin_Spike": Bin_Spike,
    "CARS_NormBias": CARS_NormBias,
    "ConstantClusterSize": ConstantClusterSize,
    "CumRateOfChange": CumRateOfChange,
    "DeepestPressure": DeepestPressure,
    "DensityInversion": DensityInversion,
    "DigitRollOver": DigitRollOver,
    "GlobalRange": GlobalRange,
    "Gradient": Gradient,
    "GradientDepthConditional": GradientDepthConditional,
    "LocationAtSea": LocationAtSea,
    "MonotonicZ": MonotonicZ,
    "ProfileEnvelop": ProfileEnvelop,
    "RateOfChange": RateOfChange,
    "RegionalRange": RegionalRange,
    "Spike": Spike,
    "SpikeDepthConditional": SpikeDepthConditional,
    "StuckValue": StuckValue,
    "Tukey53H": Tukey53H,
    "ValidGeolocation": ValidGeolocation,
    "WOA_NormBias": WOA_NormBias,
}


def catalog(klass):
    return QCTESTS.get(klass, klass)
