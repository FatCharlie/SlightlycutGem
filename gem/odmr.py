"""The ODMR sweep: step the microwaves, read the glow, report contrast.

For each frequency f the photodiode is read with the microwaves on, then off:

    C(f) = (V_on(f) - V_off(f)) / V_off(f)

    V_on   photodiode voltage with microwaves on at f
    V_off  the same moments later with microwaves off
    C      fractional change; a resonance is a negative dip

Dividing by V_off cancels slow LED and temperature drift: a poor man's lock-in.
"""
import csv
import datetime as dt
import statistics
import time
from dataclasses import dataclass, field

from . import config


def frange(start, stop, step):
    if step <= 0 or stop < start:
        raise ValueError("need step > 0 and stop >= start")
    n = int(round((stop - start) / step))
    return [round(start + i * step, 6) for i in range(n + 1)]


@dataclass
class SweepResult:
    freqs: list
    on: list
    off: list                 # None entries when the reference is skipped
    sweeps_done: int
    unlocked: int = 0
    interrupted: bool = False
    seconds: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def contrast(self):
        return [(v - r) / r if r else None for v, r in zip(self.on, self.off)]

    @property
    def signal(self):
        """Contrast if there's a reference, raw volts if not."""
        return self.contrast if self.off[0] is not None else self.on


def run_sweep(rig, freqs, sweeps=5, avg=8, ref=True, progress=None):
    """Average `sweeps` passes over `freqs`. Ctrl-C keeps the finished passes."""
    on_sum = [0.0] * len(freqs)
    off_sum = [0.0] * len(freqs)
    done, unlocked, interrupted = 0, 0, False
    t0 = time.monotonic()
    try:
        for s in range(sweeps):
            on_pass = [0.0] * len(freqs)
            off_pass = [0.0] * len(freqs)
            for i, f in enumerate(freqs):
                rig.set_freq(f, rf_on=True)
                if not rig.locked():
                    unlocked += 1
                on_pass[i] = rig.read(avg)
                if ref:
                    rig.rf(False)
                    off_pass[i] = rig.read(avg)
                    rig.rf(True)
            on_sum = [a + b for a, b in zip(on_sum, on_pass)]
            off_sum = [a + b for a, b in zip(off_sum, off_pass)]
            done += 1
            if progress:
                progress(done, sweeps, time.monotonic() - t0)
    except KeyboardInterrupt:
        interrupted = True
    n = max(done, 1)
    return SweepResult(
        freqs=freqs,
        on=[x / n for x in on_sum],
        off=[x / n for x in off_sum] if ref else [None] * len(freqs),
        sweeps_done=done, unlocked=unlocked, interrupted=interrupted,
        seconds=time.monotonic() - t0)


def find_dips(freqs, y, min_sigma=5.0, min_separation_mhz=10.0):
    """Dips: points that are the lowest within +/- min_separation_mhz and stand
    at least min_sigma noise-widths below the baseline. Deepest first.

    Noise comes from point-to-point differences (MAD of y[i+1] - y[i], / sqrt 2),
    which a smooth dip barely affects; the baseline is the median of y.
    Returns [(freq_MHz, value), ...].
    """
    vals = [v for v in y if v is not None]
    if len(vals) < 5:
        return []
    med = statistics.median(vals)
    diffs = [b - a for a, b in zip(vals, vals[1:])]
    dmed = statistics.median(diffs)
    sigma = 1.4826 * statistics.median(abs(d - dmed) for d in diffs) / 2 ** 0.5 or 1e-12
    cands = []
    for i, (f, v) in enumerate(zip(freqs, y)):
        if v is None or med - v <= min_sigma * sigma:
            continue
        window = [y[j] for j in range(len(y))
                  if y[j] is not None and abs(freqs[j] - f) <= min_separation_mhz]
        if v <= min(window):             # lowest point within +/- min_separation_mhz
            cands.append((f, v))
    cands.sort(key=lambda c: c[1])
    picked = []
    for f, v in cands:
        if all(abs(f - p) >= min_separation_mhz for p, _ in picked):
            picked.append((f, v))
    return picked


def field_from_dips(dips):
    """B along the most-aligned NV axis from the outermost dip pair, in mT.

    B = (f_high - f_low) / (2 * gamma)
    """
    if len(dips) < 2:
        return None
    fs = sorted(f for f, _ in dips)
    return (fs[-1] - fs[0]) / (2 * config.GAMMA_MHZ_PER_MT)


def write_csv(path, result, meta):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["#"] + [x for kv in meta.items() for x in kv])
        w.writerow(["freq_MHz", "V_on", "V_off", "contrast"])
        for row in zip(result.freqs, result.on, result.off, result.contrast):
            w.writerow(row)


def save_plot(path, result, title, dips=()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ref = result.off[0] is not None
    y = [v * 100 for v in result.contrast] if ref else result.on
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(result.freqs, y, lw=1.2)
    ax.axvline(config.D_MHZ, color="0.7", lw=0.8, ls="--")
    for f, _ in dips:
        ax.axvline(f, color="tab:red", lw=0.6, alpha=0.5)
    ax.set_xlabel("Microwave frequency (MHz)")
    ax.set_ylabel("Contrast (%)" if ref else "Photodiode (V)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def timestamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")
