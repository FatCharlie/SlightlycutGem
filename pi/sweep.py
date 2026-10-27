#!/usr/bin/env python3
"""ODMR sweep for the Raspberry Pi version of the Uncut Gem.

For each frequency: set the ADF4351, wait for lock, average the photodiode
voltage from the ADS1115. With --ref (on by default) each point is also read
with the microwaves off, and the script reports contrast:

    C(f) = (V_on(f) - V_off(f)) / V_off(f)

A dip shows as negative C near 2.87 GHz. Dividing by V_off cancels slow
LED and temperature drift, which is the poor man's version of a lock-in.

Examples:
    python3 sweep.py --sim                         # no hardware needed
    python3 sweep.py --start 2614 --stop 3126 --step 4 --sweeps 10
    python3 sweep.py --start 2820 --stop 2920 --step 0.5 --no-ref
"""
import argparse
import csv
import datetime as dt
import math
import random
import time


class SimHardware:
    """Fake synth + ADC: a 1 V baseline with a 1% dip at 2870 MHz, noise and drift."""

    def __init__(self, field_mt=0.0):
        self.f = 2870.0
        self.rf = True
        self.t0 = time.time()
        self.split = 28.0 * field_mt  # MHz, from f = D +/- gamma*B with gamma = 28 MHz/mT

    def set_freq(self, f, rf_on=True):
        self.f, self.rf = f, rf_on

    def rf_enable(self, on):
        self.rf = on

    def locked(self):
        return True

    def average(self, n):
        base = 1.0 + 0.02 * math.sin((time.time() - self.t0) / 5.0)  # drift
        dip = 0.0
        if self.rf:
            for c in (2870.0 - self.split, 2870.0 + self.split):
                dip += 0.01 / (1.0 + ((self.f - c) / 8.0) ** 2)  # 16 MHz FWHM Lorentzian
        return base * (1.0 - dip) + random.gauss(0, 0.002 / math.sqrt(n))

    def close(self):
        pass


class PiHardware:
    def __init__(self, power_dbm, channel, settle_ms):
        from adf4351 import ADF4351
        from ads1115 import ADS1115
        self.synth = ADF4351(power_dbm=power_dbm)
        self.adc = ADS1115(channel=channel, pga=1)
        self.settle = settle_ms / 1000.0

    def set_freq(self, f, rf_on=True):
        self.synth.set_freq(f, rf_on)
        t_end = time.time() + 0.01
        while not self.synth.locked() and time.time() < t_end:
            time.sleep(0.0002)
        time.sleep(self.settle)

    def rf_enable(self, on):
        self.synth.rf_enable(on)
        time.sleep(self.settle)

    def locked(self):
        return self.synth.locked()

    def average(self, n):
        return self.adc.average(n)

    def autorange(self):
        v = self.adc.average(8)
        self.adc.set_pga(self.adc.autorange(v))
        return v

    def close(self):
        self.synth.close()


def frange(start, stop, step):
    n = int(round((stop - start) / step))
    return [round(start + i * step, 6) for i in range(n + 1)]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=float, default=2614.0, help="MHz")
    p.add_argument("--stop", type=float, default=3126.0, help="MHz")
    p.add_argument("--step", type=float, default=4.0, help="MHz")
    p.add_argument("--sweeps", type=int, default=5, help="sweeps to average")
    p.add_argument("--avg", type=int, default=8, help="ADC samples per point")
    p.add_argument("--settle-ms", type=float, default=2.0)
    p.add_argument("--power", type=int, default=5, choices=[-4, -1, 2, 5], help="dBm")
    p.add_argument("--channel", type=int, default=0, help="ADS1115 input AINx")
    p.add_argument("--no-ref", dest="ref", action="store_false",
                   help="skip the microwave-off reference reading")
    p.add_argument("--temp", type=float, default=None, help="room temperature, C (logged)")
    p.add_argument("--note", default="", help="free text logged with the run")
    p.add_argument("--out", default=None, help="CSV path (default: timestamped)")
    p.add_argument("--plot", action="store_true", help="save a PNG next to the CSV")
    p.add_argument("--sim", action="store_true", help="simulate hardware")
    p.add_argument("--sim-field", type=float, default=0.0, help="simulated field, mT")
    a = p.parse_args()

    hw = SimHardware(a.sim_field) if a.sim else PiHardware(a.power, a.channel, a.settle_ms)
    freqs = frange(a.start, a.stop, a.step)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = a.out or f"odmr-{stamp}.csv"

    try:
        hw.set_freq(freqs[0])
        if not a.sim:
            v0 = hw.autorange()
            print(f"baseline {v0:.4f} V; ADC range +/-{__import__('ads1115').FSR[hw.adc.pga]} V")
        on_sum = [0.0] * len(freqs)
        off_sum = [0.0] * len(freqs)
        unlocked = 0
        t_start = time.time()
        for s in range(a.sweeps):
            for i, f in enumerate(freqs):
                hw.set_freq(f, rf_on=True)
                if not hw.locked():
                    unlocked += 1
                on_sum[i] += hw.average(a.avg)
                if a.ref:
                    hw.rf_enable(False)
                    off_sum[i] += hw.average(a.avg)
                    hw.rf_enable(True)
            print(f"sweep {s + 1}/{a.sweeps} done ({time.time() - t_start:.1f} s)")
    finally:
        hw.close()

    on = [x / a.sweeps for x in on_sum]
    off = [x / a.sweeps for x in off_sum] if a.ref else [None] * len(freqs)
    contrast = [(v - r) / r if r else None for v, r in zip(on, off)]

    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# time", stamp, "temp_C", a.temp, "sweeps", a.sweeps,
                    "avg", a.avg, "power_dBm", a.power, "sim", a.sim, "note", a.note])
        w.writerow(["freq_MHz", "V_on", "V_off", "contrast"])
        for row in zip(freqs, on, off, contrast):
            w.writerow(row)
    print(f"saved {out}")
    if unlocked:
        print(f"warning: PLL reported unlocked at {unlocked} points")

    y = contrast if a.ref else on
    k = min(range(len(y)), key=lambda i: y[i])
    label = "contrast" if a.ref else "V"
    print(f"deepest point: {freqs[k]:.3f} MHz, {label} = {y[k]:.5f}")

    if a.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(freqs, [v * 100 for v in y] if a.ref else y, lw=1.2)
        ax.axvline(2870, color="0.7", lw=0.8, ls="--")
        ax.set_xlabel("Microwave frequency (MHz)")
        ax.set_ylabel("Contrast (%)" if a.ref else "Photodiode (V)")
        ax.set_title(f"ODMR sweep {stamp}" + (" (simulated)" if a.sim else ""))
        fig.tight_layout()
        png = out.rsplit(".", 1)[0] + ".png"
        fig.savefig(png, dpi=120)
        print(f"saved {png}")


if __name__ == "__main__":
    main()
