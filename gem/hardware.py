"""The rig behind one interface: the real Pi hardware, or a simulation.

Both have the same methods, so the sweep code never knows which it has:

    set_freq(mhz, rf_on)   program the synth (waits for lock on real hardware)
    rf(on)                 microwaves on/off without retuning
    locked()               PLL lock state
    read(n)                average n photodiode readings, volts
    autorange()            pick the ADC range for the current light level
    describe()             one line for the CSV header
    close()                RF off, release everything
"""
import math
import random
import time

from . import config


class SimRig:
    """A single NV crystal, simulated.

    The field points along one NV axis (the "hexagonal face down" case), so
    one axis sees B and the other three see B/3 (cos 109.5 deg = -1/3).
    Dips appear at D +/- gamma*B and, three times deeper, at D +/- gamma*B/3.
    """

    def __init__(self, field_mt=0.0, contrast=0.01, fwhm_mhz=8.0, noise_v=0.001, seed=None):
        self.f = config.D_MHZ
        self.rf_on = True
        self.t0 = time.monotonic()
        self.contrast = contrast
        self.hwhm = fwhm_mhz / 2
        self.noise = noise_v
        self.rng = random.Random(seed)
        g, b = config.GAMMA_MHZ_PER_MT, field_mt
        # (centre, weight): one axis along B, three at 1/3 of it
        self.lines = [(config.D_MHZ - g * b, 0.25), (config.D_MHZ + g * b, 0.25),
                      (config.D_MHZ - g * b / 3, 0.75), (config.D_MHZ + g * b / 3, 0.75)]
        self.field_mt = field_mt

    def set_freq(self, f, rf_on=True):
        self.f, self.rf_on = f, rf_on

    def rf(self, on):
        self.rf_on = on

    def locked(self):
        return True

    def read(self, n):
        base = 1.0 + 0.02 * math.sin((time.monotonic() - self.t0) / 5.0)   # slow drift
        dip = 0.0
        if self.rf_on:
            for c, w in self.lines:
                dip += w * self.contrast / (1.0 + ((self.f - c) / self.hwhm) ** 2)
        return base * (1.0 - dip) + self.rng.gauss(0, self.noise / math.sqrt(n))

    def autorange(self):
        return self.read(8)

    def describe(self):
        return f"simulated, B = {self.field_mt} mT along one NV axis"

    def close(self):
        pass


class PiRig:
    def __init__(self, power_dbm=5, settle_ms=2.0):
        from .adf4351 import ADF4351
        from .ads1115 import ADS1115
        self.synth = ADF4351(power_dbm=power_dbm)
        try:
            self.adc = ADS1115(pga=1)
        except Exception:
            self.synth.close()
            raise
        self.settle = settle_ms / 1000.0
        self.power_dbm = power_dbm

    def set_freq(self, f, rf_on=True):
        self.synth.set_freq(f, rf_on)
        self.synth.wait_lock()
        time.sleep(self.settle)

    def rf(self, on):
        self.synth.rf_enable(on)
        time.sleep(self.settle)

    def locked(self):
        return self.synth.locked()

    def read(self, n):
        return self.adc.average(n)

    def autorange(self):
        return self.adc.autorange()

    def describe(self):
        return f"pi, synth {self.power_dbm} dBm, ADC +/-{self.adc.full_scale} V"

    def close(self):
        try:
            self.synth.close()
        finally:
            self.adc.close()


def open_rig(sim=False, sim_field=0.0, power_dbm=5, settle_ms=2.0):
    if sim:
        return SimRig(field_mt=sim_field)
    return PiRig(power_dbm=power_dbm, settle_ms=settle_ms)
