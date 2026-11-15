#!/usr/bin/env python3
"""ODMR sweep: step the microwaves past 2.87 GHz and log the diamond's glow.

Each point is read with microwaves on and off and reported as contrast
C = (V_on - V_off) / V_off. A resonance is a negative dip. Ctrl-C stops early
and still saves the sweeps that finished.

Examples:
    python3 sweep.py --sim --plot                  # no hardware needed
    python3 sweep.py --sim --sim-field 3 --plot    # simulated magnet, 3 mT
    python3 sweep.py --sweeps 10 --temp 21 --plot
    python3 sweep.py --start 2820 --stop 2920 --step 0.5 --sweeps 20 --plot
"""
import argparse
import sys

from gem import config, odmr, report
from gem.hardware import open_rig


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=float, default=config.SWEEP_START_MHZ, help="MHz")
    p.add_argument("--stop", type=float, default=config.SWEEP_STOP_MHZ, help="MHz")
    p.add_argument("--step", type=float, default=config.SWEEP_STEP_MHZ, help="MHz")
    p.add_argument("--sweeps", type=int, default=5, help="sweeps to average")
    p.add_argument("--avg", type=int, default=8, help="ADC samples per point")
    p.add_argument("--settle-ms", type=float, default=2.0)
    p.add_argument("--power", type=int, default=5, choices=[-4, -1, 2, 5], help="synth dBm")
    p.add_argument("--no-ref", dest="ref", action="store_false",
                   help="skip the microwave-off reading (faster, more drift)")
    p.add_argument("--temp", type=float, default=None, help="room temperature, C (logged)")
    p.add_argument("--note", default="", help="free text logged with the run")
    p.add_argument("--out", default=None, help="CSV path (default: timestamped)")
    p.add_argument("--plot", action="store_true", help="save a PNG next to the CSV")
    p.add_argument("--sim", action="store_true", help="simulate the hardware")
    p.add_argument("--sim-field", type=float, default=0.0, help="simulated field, mT")
    a = p.parse_args(argv)

    freqs = odmr.frange(a.start, a.stop, a.step)
    stamp = odmr.timestamp()
    out = a.out or f"odmr-{stamp}.csv"

    try:
        rig = open_rig(a.sim, a.sim_field, a.power, a.settle_ms)
    except Exception as e:  # noqa: BLE001
        report.say(f"Couldn't open the hardware: {e}", "bold red")
        report.say("Run  python3 setup.py  to see which part is missing.", "yellow")
        return 1

    try:
        rig.set_freq(freqs[0])
        baseline = rig.autorange()
        report.say(f"{rig.describe()}; baseline {baseline:.4f} V; "
                   f"{len(freqs)} points x {a.sweeps} sweeps")
        result = odmr.run_sweep(
            rig, freqs, a.sweeps, a.avg, a.ref,
            progress=lambda d, n, t: report.say(f"sweep {d}/{n} done ({t:.1f} s)", "dim"))
        desc = rig.describe()
    finally:
        rig.close()

    if result.sweeps_done == 0:
        report.say("Stopped before the first sweep finished; nothing saved.", "yellow")
        return 1
    if result.interrupted:
        report.say(f"Stopped early; saving the {result.sweeps_done} finished sweep(s).", "yellow")

    meta = {"time": stamp, "rig": desc, "temp_C": a.temp, "sweeps": result.sweeps_done,
            "avg": a.avg, "power_dBm": a.power, "note": a.note}
    odmr.write_csv(out, result, meta)
    report.say(f"saved {out}", "green")
    if result.unlocked:
        report.say(f"warning: PLL reported unlocked at {result.unlocked} points", "yellow")

    y = result.signal
    dips = odmr.find_dips(freqs, y)
    unit = "%" if a.ref else "V"
    scale = 100 if a.ref else 1
    if dips:
        lines = [f"{f:9.2f} MHz   {v * scale:+.3f} {unit}" for f, v in sorted(dips)]
        b = odmr.field_from_dips(dips)
        if b:
            lines.append(f"B along the most-aligned NV axis ≈ {b:.2f} mT")
        report.panel("Dips found", lines)
    else:
        k = min(range(len(y)), key=lambda i: y[i])
        report.say(f"No clear dip; deepest point {freqs[k]:.2f} MHz ({y[k] * scale:+.4f} {unit})")

    if a.plot:
        png = out.rsplit(".", 1)[0] + ".png"
        odmr.save_plot(png, result, f"ODMR sweep {stamp}" + (" (simulated)" if a.sim else ""), dips)
        report.say(f"saved {png}", "green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
