#!/usr/bin/env python3
"""Hardware check: tests every part of the rig and shows what's ready.

    python3 setup.py                     check everything that can be checked
    python3 setup.py --only adf4351      just the synthesizer (repeatable)
    python3 setup.py --interactive       adds a cover-the-photodiode test
    python3 setup.py --have amp,led      parts you've fitted that can't be detected

The synthesizer test never turns the RF output on; the PLL locks with the
output stage off, so it's safe with nothing on the SMA ports.

The RF amp, antenna loop, terminator, LED and diamond have no digital
interface, so nothing can detect them. List the ones you've fitted with
--have; the rest show as NOT FITTED, and the summary says what's still
needed for each bring-up step.

(This is a plain script, not a setuptools file.)
"""
import argparse
import importlib
import importlib.util
import os
import sys
import time

from gem import config
from gem.report import ABSENT, FAIL, MANUAL, READY, SKIP, WARN, Check, panel, say, status_table


# --- the Pi itself ------------------------------------------------------------

def check_pi():
    try:
        model = open("/proc/device-tree/model").read().strip("\x00\n ")
    except OSError:
        model = ""
    out = []
    if "Raspberry Pi" in model:
        out.append(Check("Pi", "Board", READY, model))
    else:
        out.append(Check("Pi", "Board", WARN, model or "not a Raspberry Pi",
                         "Hardware checks will fail here; sweep.py --sim and selftest.py still work"))
    v = sys.version_info
    out.append(Check("Pi", "Python", READY if v >= (3, 9) else FAIL, f"{v.major}.{v.minor}.{v.micro}",
                     "" if v >= (3, 9) else "Needs Python 3.9 or newer"))
    for dev, name, fix in (("/dev/spidev0.0", "SPI0", "sudo raspi-config nonint do_spi 0, then reboot"),
                           ("/dev/i2c-1", "I2C1", "sudo raspi-config nonint do_i2c 0, then reboot")):
        if os.path.exists(dev):
            out.append(Check("Pi", f"{name} ({dev})", READY, "enabled"))
        else:
            out.append(Check("Pi", f"{name} ({dev})", FAIL, "missing", fix))
    return out


PACKAGES = [  # (import name, apt package, what needs it, required?)
    ("spidev", "python3-spidev", "synthesizer SPI", True),
    ("smbus2", "python3-smbus2", "ADC I2C", True),
    ("gpiozero", "python3-gpiozero", "synth CE and LD pins", True),
    ("lgpio", "python3-lgpio", "gpiozero's backend on Bookworm", True),
    ("matplotlib", "python3-matplotlib", "sweep.py --plot", False),
    ("rich", "python3-rich", "colour tables", False),
]


def check_packages():
    out = []
    for mod, apt, why, required in PACKAGES:
        try:
            m = importlib.import_module(mod)
            out.append(Check("Packages", mod, READY, f"{getattr(m, '__version__', '')}  {why}".strip()))
        except ImportError:
            if mod == "smbus2" and importlib.util.find_spec("smbus"):
                out.append(Check("Packages", mod, READY, "using the older smbus module"))
                continue
            out.append(Check("Packages", mod, FAIL if required else WARN,
                             f"missing ({why})", f"sudo apt install -y {apt}"))
    return out


# --- ADS1115 + photodiode -----------------------------------------------------

def check_adc(interactive=False):
    g = "Readout"
    try:
        from gem import ads1115
        found = ads1115.probe()
    except Exception as e:  # noqa: BLE001
        return [Check(g, "ADS1115 ADC", FAIL, f"can't use I2C bus {config.I2C_BUS}: {e}",
                      "Enable I2C and install python3-smbus2"),
                Check(g, "Photodiode amp (A0)", SKIP, "needs the ADC")]

    if config.ADC_ADDR not in found:
        if found:
            c = Check(g, "ADS1115 ADC", FAIL, f"answering at {', '.join(hex(a) for a in found)}, "
                      f"expected {hex(config.ADC_ADDR)}", "Tie the module's ADDR pin to GND")
        else:
            c = Check(g, "ADS1115 ADC", FAIL, "no answer at 0x48 to 0x4B",
                      "Check VDD to pin 1 (3.3 V), GND, SDA to pin 3, SCL to pin 5")
        return [c, Check(g, "Photodiode amp (A0)", SKIP, "needs the ADC")]

    out = [Check(g, "ADS1115 ADC", READY, f"answering at {hex(config.ADC_ADDR)}")]
    adc = ads1115.ADS1115(pga=1)                      # ±4.096 V: safe for 0 to 3.3 V
    try:
        v = adc.average(16)
        if v < 0.005:
            out.append(Check(g, "Photodiode amp (A0)", WARN, f"{v:.4f} V: dark or not connected",
                             "Fine if the photodiode is covered or the amp isn't built yet"))
        elif v > 3.2:
            out.append(Check(g, "Photodiode amp (A0)", WARN, f"{v:.3f} V: saturated",
                             "Too much light for 10 MΩ: shade stray light or use 1 MΩ"))
        else:
            out.append(Check(g, "Photodiode amp (A0)", READY, f"{v:.4f} V"))

        if interactive and 0.005 <= v <= 3.2:
            input("  Cover the photodiode completely, then press Enter... ")
            dark = adc.average(16)
            ok = dark < v * 0.5
            out.append(Check(g, "Photodiode responds to light", READY if ok else FAIL,
                             f"{v:.4f} V lit → {dark:.4f} V covered",
                             "" if ok else "Check BPW34 orientation: cathode to op-amp pin 2"))
    finally:
        adc.close()
    return out


# --- ADF4351 ------------------------------------------------------------------

LOCK_TEST_MHZ = (2614.0, 2870.0, 3126.0)
SYNTH_WIRING_FIX = ("Check in order: barrel power plugged in; P3 jumpers removed; "
                    "DAT→pin 19, CLK→pin 23, LE→pin 24 with 10 kΩ to GND; "
                    "CE→pin 22, LD→pin 18; common GND")


def check_synth():
    """Prove the synth is alive using its lock-detect pin, RF output kept off.

    SPI is write-only on this chip, so LD is the only evidence. It must go
    high after programming each test frequency, and drop when CE powers the
    chip down; the second part proves LD is really wired to the chip and not
    floating high or tied to 3.3 V.
    """
    g = "Synthesizer"
    try:
        from gem.adf4351 import ADF4351, actual_freq
        synth = ADF4351(power_dbm=-4)
    except Exception as e:  # noqa: BLE001
        msg = str(e) or type(e).__name__
        fix = "Enable SPI; install python3-spidev, python3-gpiozero and python3-lgpio"
        if "in use" in msg.lower() or "busy" in msg.lower():
            fix = "Another program (sweep.py?) is holding the pins; stop it and rerun"
        return [Check(g, "ADF4351", FAIL, msg, fix)]

    try:
        synth.chip_enable(True)
        time.sleep(0.01)
        locks = []
        for f in LOCK_TEST_MHZ:
            synth.set_freq(f, rf_on=False, full=True)
            locks.append((f, synth.wait_lock(0.05)))

        synth.chip_enable(False)                 # LD must drop with the chip off
        time.sleep(0.02)
        drops = not synth.locked()
        synth.chip_enable(True)
        time.sleep(0.01)
        synth.set_freq(config.D_MHZ, rf_on=False, full=True)
        relock = synth.wait_lock(0.05)
    finally:
        synth.close()

    detail = ", ".join(f"{f:.0f} {'✔' if ok else '✘'}" for f, ok in locks)
    all_ok = all(ok for _, ok in locks) and relock
    any_ok = any(ok for _, ok in locks)
    out = []
    if all_ok and drops:
        out.append(Check(g, "ADF4351 lock", READY, f"locks at {detail} MHz"))
        out.append(Check(g, "Lock-detect wire", READY, "LD drops when CE powers the chip down"))
    elif any_ok and not drops:
        out.append(Check(g, "ADF4351 lock", WARN, f"LD reads high at {detail} MHz, but also with the chip off"))
        out.append(Check(g, "Lock-detect wire", FAIL, "LD is stuck high",
                         "The LD wire should go to P2 'LD', not 3V3 or MUX"))
    elif any_ok:
        out.append(Check(g, "ADF4351 lock", WARN, f"partial lock: {detail} MHz",
                         "Intermittent: check the 10 kΩ LE pull-down, short jumper wires and barrel power"))
        out.append(Check(g, "Lock-detect wire", READY if drops else WARN,
                         "LD drops with the chip off" if drops else "LD stays high with the chip off"))
    else:
        out.append(Check(g, "ADF4351 lock", FAIL, f"no lock at {detail} MHz", SYNTH_WIRING_FIX))
        out.append(Check(g, "Lock-detect wire", SKIP, "can't verify without a lock"))
    out.append(Check(g, "Frequency plan", READY,
                     f"{config.D_MHZ:.0f} MHz → {actual_freq(config.D_MHZ):.4f} MHz "
                     f"({config.CHANNEL_KHZ:g} kHz grid, {config.REF_MHZ:g} MHz ref)"))
    return out


# --- parts nothing can detect -------------------------------------------------

MANUAL_PARTS = [  # (--have key, group, name, what to check by eye)
    ("amp", "RF", "RF amplifier (40 dB)", "5 V from Pi pin 2, GND; SMA in from synth OUT+"),
    ("loop", "RF", "Antenna loop (RG316 pigtail)", "Leads cut off; 2 to 3 mm loop flat on the block"),
    ("terminator", "RF", "50 Ω terminator on OUT−", "Synth OUT− only, never the amp output"),
    ("led", "Optics", "Green LED + 100 Ω", "Lit at power-up from Pi pin 4"),
    ("diamond", "Optics", "NV diamond", "Glows red under the LED; look through red gel"),
]


def check_manual(have):
    out = []
    for key, group, name, hint in MANUAL_PARTS:
        if key in have:
            out.append(Check(group, name, MANUAL, "fitted", hint))
        else:
            out.append(Check(group, name, ABSENT, f"add --have {key} once fitted"))
    return out


# --- what can be run next -----------------------------------------------------

def readiness(checks, have):
    st = {c.name: c.status for c in checks}
    adc = st.get("ADS1115 ADC") == READY
    synth = st.get("ADF4351 lock") == READY
    steps = [("Simulation: sweep.py --sim", True, ""),
             ("ADC and photodiode amp", adc, "" if adc else "ADS1115 not answering")]
    steps.append(("Synthesizer locks", synth, "" if synth else "ADF4351 not locking"))
    rf_missing = [k for k in ("amp", "loop") if k not in have]
    rf = synth and not rf_missing
    steps.append(("RF chain to the diamond", rf,
                  "" if rf else (f"waiting on: {', '.join(rf_missing)}" if rf_missing else "synth first")))
    opt_missing = [k for k in ("led", "diamond") if k not in have]
    full = rf and adc and not opt_missing
    why = "" if full else ("waiting on: " + ", ".join(rf_missing + opt_missing) if rf_missing + opt_missing
                           else "fix the failures above")
    steps.append(("First real sweep: sweep.py --plot", full, why))
    return steps


CHECKS = {"pi": check_pi, "packages": check_packages, "adc": check_adc,
          "adf4351": check_synth, "manual": None}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", choices=list(CHECKS), action="append", help="run only these checks")
    p.add_argument("--have", default="",
                   help="fitted parts nothing can detect: " + ",".join(k for k, *_ in MANUAL_PARTS))
    p.add_argument("--interactive", action="store_true", help="also ask you to cover the photodiode")
    a = p.parse_args(argv)
    have = {h.strip().lower() for h in a.have.split(",") if h.strip()}
    unknown = have - {k for k, *_ in MANUAL_PARTS}
    if unknown:
        p.error(f"unknown --have part(s): {', '.join(sorted(unknown))}")
    run = a.only or list(CHECKS)

    checks = []
    for name in run:
        if name == "manual":
            checks += check_manual(have)
        elif name == "adc":
            checks += check_adc(a.interactive)
        else:
            checks += CHECKS[name]()

    status_table("SlightlyCutGem hardware check", checks)
    if not a.only:
        panel("What you can do now",
              [("[bold green]✔[/] " if ok else "[dim]✘[/] ") + name + (f"  [dim]({why})[/]" if why else "")
               for name, ok, why in readiness(checks, have)])
    missing = [apt for mod, apt, _, _ in PACKAGES
               if any(c.group == "Packages" and c.name == mod and c.status in (FAIL, WARN) for c in checks)]
    if missing:
        say("Install everything missing in one go:", "yellow")
        say(f"  sudo apt install -y {' '.join(missing)}")
    fails = sum(c.status == FAIL for c in checks)
    warns = sum(c.status == WARN for c in checks)
    if fails:
        say(f"{fails} failed, {warns} warning(s)", "bold red")
    elif warns:
        say(f"No failures, {warns} warning(s)", "bold yellow")
    else:
        say("Everything checked is ready.", "bold green")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
