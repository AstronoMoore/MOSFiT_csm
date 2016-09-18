from math import isnan

import numexpr as ne
import numpy as np

from ...constants import C_CGS, DAY_CGS, FOUR_PI, KM_CGS, M_SUN_CGS
from ..module import Module

CLASS_NAME = 'Diffusion'


class Diffusion(Module):
    """Photon diffusion transform.
    """

    N_INT_TIMES = 20
    MIN_EXP_ARG = 20
    DIFF_CONST = 2.0 * M_SUN_CGS / (13.7 * C_CGS * KM_CGS)
    TRAP_CONST = 3.0 * M_SUN_CGS / (FOUR_PI * KM_CGS**2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process(self, **kwargs):
        self._t_explosion = kwargs['texplosion']
        self._kappa = kwargs['kappa']
        self._kappa_gamma = kwargs['kappagamma']
        self._m_ejecta = kwargs['mejecta']
        self._v_ejecta = kwargs['vejecta']
        self._times = kwargs['times']
        if 'densetimes' in kwargs:
            self._dense_times = kwargs['densetimes']
        else:
            self._dense_times = kwargs['times']
        self._luminosities = kwargs['luminosities']
        self._times_since_exp = [(x - self._t_explosion) * DAY_CGS
                                 for x in self._times]
        self._dense_times_since_exp = [(x - self._t_explosion) * DAY_CGS
                                       for x in self._dense_times]
        self._tau_diff = np.sqrt(self.DIFF_CONST * self._kappa *
                                 self._m_ejecta / self._v_ejecta)
        self._trap_coeff = (self.TRAP_CONST * self._kappa_gamma *
                            self._m_ejecta / (self._v_ejecta**2))
        td2, A = self._tau_diff**2, self._trap_coeff

        new_lum = []
        evaled = False
        lum_cache = {}
        min_te = min(self._dense_times_since_exp)
        for te in self._times_since_exp:
            if te <= 0.0:
                new_lum.append(0.0)
                continue
            if te in lum_cache:
                new_lum.append(lum_cache[te])
                continue
            tb = max(np.sqrt(max(te**2 - self.MIN_EXP_ARG * td2, 0.0)), min_te)
            te2 = te**2
            int_times = np.linspace(tb, te, self.N_INT_TIMES)
            dt = int_times[1] - int_times[0]

            int_lums = np.interp(int_times, self._dense_times_since_exp,
                                 self._luminosities)

            if not evaled:
                int_arg = ne.evaluate('2.0 * int_lums * int_times / td2 * '
                                      'exp((int_times**2 - te2) / td2) * '
                                      '(1.0 - exp(-A / te2))')
                evaled = True
            else:
                int_arg = ne.re_evaluate()
            # int_arg = [
            #     2.0 * l * t / td2 *
            #     np.exp((t**2 - te**2) / td2) * (1.0 - np.exp(-A / te**2))
            #     for t, l in zip(int_times, int_lums)
            # ]
            int_arg = [0.0 if isnan(x) else x for x in int_arg]
            lum_val = np.trapz(int_arg, dx=dt)
            lum_cache[te] = lum_val
            new_lum.append(lum_val)
        return {'luminosities': new_lum}
