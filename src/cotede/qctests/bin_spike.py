#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""

"""

import numpy as np
from numpy import ma


def bin_spike(x, number_of_points):
    """

        number_of_points is the number of points used for comparison, 
        thus number_of_points=2 means that each point will be compared 
        only against the previous and following measurements.
        
        number_of_points=2 is is probably not a good choice, too small.

        Maybe use pstsd instead?

        Dummy way to avoid warnings when x[ini:fin] are all masked.
        Improve this in the future.
    """
    assert x.ndim == 1, "I'm not ready to deal with multidimensional x"

    assert number_of_points%2 == 0, "number_of_points must be an even integer"

    N = len(x)
    bin = ma.masked_all(N)
    # bin_std = ma.masked_all(N)
    half_window = int(number_of_points/2)
    idx = (i for i in range(half_window, N - half_window) if np.isfinite(x[i]))
    for i in idx:
        ini = max(0, i - half_window)
        fin = min(N, i + half_window)
        # At least 3 valid points
        if ma.compressed(x[ini:fin]).size >= 3:
            bin[i] = x[i] - ma.median(x[ini:fin])
            # bin_std[i] = (np.append(x[ini:i], x[i+1:fin+1])).std()
            bin[i] /= (np.append(x[ini:i], x[i+1:fin+1])).std()

    return bin


class Bin_Spike:
    def __init__(self, data, varname, cfg, autoflag=True):
        self.data = data
        self.varname = varname
        self.cfg = cfg

        self.set_features()
        if autoflag:
            self.test()

    def keys(self):
        return self.features.keys() + \
            [f"flag_{f}" for f in self.flags.keys()]

    def set_features(self):
        self.features = {'bin_spike': bin_spike(self.data[self.varname],
            self.cfg['number_of_points'])}

    def test(self):
        self.flags = {}
        try:
            threshold = self.cfg['threshold']
        except Exception:
            print("Deprecated cfg format. It should contain a threshold item.")
            threshold = self.cfg

        try:
            flag_good = self.cfg['flag_good']
            flag_bad = self.cfg['flag_bad']
        except Exception:
            print("Deprecated cfg format. It should contain flag_good & flag_bad.")
            flag_good = 1
            flag_bad = 3

        assert (np.size(threshold) == 1) and \
                (threshold is not None) and \
                (np.isfinite(threshold))   

        flag = np.zeros(self.data[self.varname].shape, dtype='i1')
        flag[np.nonzero(self.features['bin_spike'] > threshold)] = flag_bad
        flag[np.nonzero(self.features['bin_spike'] <= threshold)] = flag_good
        flag[ma.getmaskarray(self.data[self.varname])] = 9
        self.flags['bin_spike'] = flag
