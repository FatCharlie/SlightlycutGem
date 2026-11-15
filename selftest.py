#!/usr/bin/env python3
"""Self-test: checks the software with no hardware attached.

    python3 selftest.py          run everything
    python3 selftest.py synth    run only tests whose name contains "synth"

Runs anywhere (the Pi, a laptop). Fake SPI, GPIO and I2C stand in for the
real parts, and act out wiring faults so we can check that check_hw.py's
diagnosis is right. Plain Python: each test is a function that raises
AssertionError on failure. Add one by writing a function and listing it in
TESTS at the bottom.
"""
import contextlib
import os
import sys
import tempfile
import time
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gem import ads1115, config, odmr  # noqa: E402
from gem.adf4351 import ADF4351, actual_freq, calc, registers  # noqa: E402
from gem.hardware import SimRig  # noqa: E402


def near(a, b, tol):
    assert abs(a - b) <= tol, f"{a} is not within {tol} of {b}"


# =============================================================================
# Fakes for the Pi's hardware libraries
# =============================================================================

class FakeSynthBoard:
    """Pretends to be the ADF4351 EVAL board on the end of the wires.

    mode: good | unpowered | ld_stuck_high | flaky
    """

    def __init__(self, mode="good"):
        self.mode = mode
        self.ce = False
        self.programmed = False
        self.words = []
        self.writes = 0

    def spi_write(self, word):
        self.words.append(word)
        self.writes += 1
        if word & 0x7 == 0:            # R0 is written last and starts the lock
            self.programmed = True

    def ld(self):
        if self.mode == "ld_stuck_high":
            return True
        if self.mode == "unpowered":
            return False
        locked = self.ce and self.programmed
        if self.mode == "flaky":       # locks on every other programming
            return locked and (self.writes // 6) % 2 == 1
        return locked


class FakeI2CBus:
    """An ADS1115 at `addr` whose A0 reads `volts`."""

    def __init__(self, addr=0x48, volts=1.0):
        self.addr, self.volts, self.pga = addr, volts, 1
        self.config_writes = []

    def _check(self, addr):
        if addr != self.addr:
            raise OSError(121, "Remote I/O error")

    def read_i2c_block_data(self, addr, reg, n):
        self._check(addr)
        if reg == ads1115.REG_CONFIG:
            return [0x85, 0x83]
        raw = int(round(self.volts / ads1115.FSR[self.pga] * 32768))
        raw = max(-32768, min(32767, raw)) & 0xFFFF
        return [raw >> 8, raw & 0xFF]

    def write_i2c_block_data(self, addr, reg, data):
        self._check(addr)
        word = (data[0] << 8) | data[1]
        self.config_writes.append(word)
        self.pga = (word >> 9) & 0b111

    def close(self):
        pass


@contextlib.contextmanager
def fake_pi(board=None, bus=None):
    """Swap in fake spidev, gpiozero and smbus2 modules for the duration."""
    board = board or FakeSynthBoard()
    bus = bus or FakeI2CBus()

    spidev = types.ModuleType("spidev")

    class SpiDev:
        mode = 0
        max_speed_hz = 0
        def open(self, b, d): pass
        def xfer2(self, data): board.spi_write(int.from_bytes(bytes(data), "big"))
        def close(self): pass
    spidev.SpiDev = SpiDev

    gpiozero = types.ModuleType("gpiozero")

    class DigitalOutputDevice:
        def __init__(self, pin, initial_value=False):
            board.ce = bool(initial_value)
        @property
        def value(self): return int(board.ce)
        @value.setter
        def value(self, v):
            board.ce = bool(v)
            if not v:
                board.programmed = False    # powered down: lock is lost
        def close(self): pass

    class DigitalInputDevice:
        def __init__(self, pin): pass
        @property
        def value(self): return int(board.ld())
        def close(self): pass

    gpiozero.DigitalOutputDevice = DigitalOutputDevice
    gpiozero.DigitalInputDevice = DigitalInputDevice

    smbus2 = types.ModuleType("smbus2")
    smbus2.SMBus = lambda n: bus

    saved = {k: sys.modules.get(k) for k in ("spidev", "gpiozero", "smbus2")}
    sys.modules.update(spidev=spidev, gpiozero=gpiozero, smbus2=smbus2)
    try:
        yield board, bus
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# =============================================================================
# Synthesizer register math
# =============================================================================

def test_synth_2870_frequency_plan():
    # 2870 / 25 = 114.8 -> INT 114, FRAC/MOD = 0.8 = 4/5 after reduction
    assert calc(2870.0) == (114, 4, 5, 1, 25.0)
    near(actual_freq(2870.0), 2870.0, 1e-9)


def test_synth_sweep_range_lands_on_10khz_grid():
    for f in (2614.0, 2870.0, 3126.0, 2870.01, 2700.37, 2999.99):
        near(actual_freq(f), round(f * 100) / 100, 5e-6)


def test_synth_every_register_carries_its_address():
    regs = registers(2870.0)
    assert [r & 0x7 for r in regs] == [0, 1, 2, 3, 4, 5]
    assert all(0 <= r < 2 ** 32 for r in regs)


def test_synth_rf_bit_and_power_code():
    on = registers(2870.0, power_dbm=5, rf_on=True)[4]
    off = registers(2870.0, power_dbm=-4, rf_on=False)[4]
    assert (on >> 5) & 1 == 1 and (off >> 5) & 1 == 0
    assert (on >> 3) & 0b11 == 3 and (off >> 3) & 0b11 == 0


def test_synth_rejects_bad_input():
    for bad in (lambda: calc(5000.0), lambda: calc(10.0), lambda: registers(2870.0, power_dbm=3)):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


# =============================================================================
# Synthesizer driver, on a fake board
# =============================================================================

def test_synth_driver_full_write_is_r5_first_r0_last():
    with fake_pi() as (board, _):
        s = ADF4351()
        s.set_freq(2870.0)
        assert [w & 0x7 for w in board.words] == [5, 4, 3, 2, 1, 0]
        assert s.wait_lock()
        s.close()


def test_synth_driver_retune_sends_only_changes_then_r0():
    with fake_pi() as (board, _):
        s = ADF4351()
        s.set_freq(2870.0)
        board.words.clear()
        s.set_freq(2874.0)
        assert board.words[-1] & 0x7 == 0, "R0 must be last"
        assert 5 not in [w & 0x7 for w in board.words]
        s.close()


def test_synth_driver_rf_toggle_touches_only_r4_bit5():
    with fake_pi() as (board, _):
        s = ADF4351()
        s.set_freq(2870.0, rf_on=True)
        before = s._regs[4]
        board.words.clear()
        s.rf_enable(False)
        assert board.words == [before & ~(1 << 5)]
        s.close()
        assert (board.words[-1] >> 5) & 1 == 0, "close() must leave RF off"


# =============================================================================
# check_hw.py's synthesizer diagnosis
# =============================================================================

def _synth_check(mode):
    import check_hw
    with fake_pi(FakeSynthBoard(mode)) as (board, _):
        checks = {c.name: c for c in check_hw.check_synth()}
    return checks, board


def test_check_synth_good_board_is_ready():
    from gem.report import READY
    c, _ = _synth_check("good")
    assert c["ADF4351 lock"].status == READY
    assert c["Lock-detect wire"].status == READY


def test_check_synth_never_enables_rf():
    _, board = _synth_check("good")
    r4 = [w for w in board.words if w & 0x7 == 4]
    assert r4 and all((w >> 5) & 1 == 0 for w in r4)


def test_check_synth_unpowered_points_at_wiring():
    from gem.report import FAIL
    c, _ = _synth_check("unpowered")
    assert c["ADF4351 lock"].status == FAIL
    assert "P3 jumpers" in c["ADF4351 lock"].fix


def test_check_synth_catches_ld_stuck_high():
    from gem.report import FAIL
    c, _ = _synth_check("ld_stuck_high")
    assert c["Lock-detect wire"].status == FAIL


def test_check_synth_flaky_lock_is_a_warning():
    from gem.report import WARN
    c, _ = _synth_check("flaky")
    assert c["ADF4351 lock"].status == WARN, c["ADF4351 lock"].detail


# =============================================================================
# ADC
# =============================================================================

def test_adc_config_word():
    # A0 vs GND, ±4.096 V, 860 SPS, continuous, comparator off
    assert ads1115.config_word(0, 1, 860) == 0b0100_0010_1110_0011


def test_adc_counts_to_volts_sign():
    near(ads1115.counts_to_volts(0x7F, 0xFF, 1), 4.096, 1e-3)
    near(ads1115.counts_to_volts(0x80, 0x00, 1), -4.096, 1e-9)
    assert ads1115.counts_to_volts(0, 0, 1) == 0.0


def test_adc_reads_and_autoranges():
    with fake_pi(bus=FakeI2CBus(volts=0.3)):
        adc = ads1115.ADS1115(rate=860)
        near(adc.average(4), 0.3, 2e-4)
        adc.autorange()
        assert adc.pga == 4, f"0.3 V should pick ±0.512 V, got pga {adc.pga}"
        near(adc.average(4), 0.3, 5e-5)


def test_check_adc_wrong_address_is_explained():
    import check_hw
    from gem.report import FAIL
    with fake_pi(bus=FakeI2CBus(addr=0x49)):
        c = {x.name: x for x in check_hw.check_adc()}
    assert c["ADS1115 ADC"].status == FAIL and "ADDR" in c["ADS1115 ADC"].fix


def test_check_adc_flags_saturation():
    import check_hw
    from gem.report import WARN
    with fake_pi(bus=FakeI2CBus(volts=3.29)):
        c = {x.name: x for x in check_hw.check_adc()}
    assert c["Photodiode amp (A0)"].status == WARN and "saturated" in c["Photodiode amp (A0)"].detail


# =============================================================================
# Sweep, on the simulated rig
# =============================================================================

def test_sweep_frange():
    f = odmr.frange(2614, 3126, 4)
    assert len(f) == 129 and f[0] == 2614 and f[-1] == 3126 and f[64] == 2870


def test_sweep_zero_field_finds_one_dip_at_d():
    rig = SimRig(field_mt=0, seed=1)
    freqs = odmr.frange(2800, 2940, 1)
    r = odmr.run_sweep(rig, freqs, sweeps=3, avg=8)
    dips = odmr.find_dips(freqs, r.contrast)
    assert len(dips) == 1, dips
    near(dips[0][0], config.D_MHZ, 2)


def test_sweep_3mt_finds_four_dips_and_the_field():
    rig = SimRig(field_mt=3.0, seed=2)
    freqs = odmr.frange(2760, 2980, 1)
    r = odmr.run_sweep(rig, freqs, sweeps=3, avg=8)
    dips = sorted(f for f, _ in odmr.find_dips(freqs, r.contrast))
    expect = [2870 - 84, 2870 - 28, 2870 + 28, 2870 + 84]
    assert len(dips) == 4, dips
    for got, want in zip(dips, expect):
        near(got, want, 2)
    near(odmr.field_from_dips([(f, 0) for f in dips]), 3.0, 0.1)


def test_sweep_ctrl_c_keeps_finished_passes():
    class StopsMidway(SimRig):
        calls = 0
        def read(self, n):
            self.calls += 1
            if self.calls > 50:        # the 2-point sweep needs 4 reads per pass
                raise KeyboardInterrupt
            return super().read(n)
    r = odmr.run_sweep(StopsMidway(seed=3), [2860.0, 2870.0], sweeps=100, avg=1)
    assert r.interrupted and r.sweeps_done == 12


def test_sweep_script_end_to_end():
    import sweep
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "run.csv")
        argv = ["--sim", "--sim-field", "2", "--start", "2800", "--stop", "2940", "--step", "2",
                "--sweeps", "2", "--avg", "2", "--out", out]
        try:
            import matplotlib  # noqa: F401
            argv.append("--plot")
        except ImportError:
            pass
        with contextlib.redirect_stdout(open(os.devnull, "w")):
            assert sweep.main(argv) == 0
        rows = open(out).read().splitlines()
        assert rows[0].startswith("#,time,")
        assert rows[1] == "freq_MHz,V_on,V_off,contrast"
        assert len(rows) == 2 + 71
        if "--plot" in argv:
            assert os.path.getsize(out.replace(".csv", ".png")) > 1000


# =============================================================================
# check_hw.py's summary
# =============================================================================

def test_readiness_without_amp():
    import check_hw
    from gem.report import READY, Check
    checks = [Check("Readout", "ADS1115 ADC", READY), Check("Synthesizer", "ADF4351 lock", READY)]
    steps = {name: (ok, why) for name, ok, why in check_hw.readiness(checks, {"led"})}
    assert steps["Synthesizer locks"][0]
    assert not steps["RF chain to the diamond"][0]
    assert "amp" in steps["RF chain to the diamond"][1]
    assert not steps["First real sweep: sweep.py --plot"][0]


def test_readiness_everything_fitted():
    import check_hw
    from gem.report import READY, Check
    checks = [Check("Readout", "ADS1115 ADC", READY), Check("Synthesizer", "ADF4351 lock", READY)]
    steps = check_hw.readiness(checks, {"amp", "loop", "led", "diamond"})
    assert all(ok for _, ok, _ in steps)


# =============================================================================
# Runner
# =============================================================================

TESTS = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]


def main(argv):
    from gem.report import HAVE_RICH, console
    pattern = argv[0] if argv else ""
    tests = [t for t in TESTS if pattern in t.__name__]
    failed = []
    t_all = time.monotonic()
    for t in tests:
        name = t.__name__[5:].replace("_", " ")
        t0 = time.monotonic()
        try:
            t()
            ok, err = True, ""
        except Exception as e:  # noqa: BLE001
            ok, err = False, traceback.format_exc() if not isinstance(e, AssertionError) else str(e)
            failed.append((name, err, traceback.format_exc()))
        ms = (time.monotonic() - t0) * 1000
        if HAVE_RICH:
            mark = "[bold green]✔[/]" if ok else "[bold red]✘[/]"
            console.print(f" {mark} {name} [dim]{ms:.0f} ms[/]")
        else:
            print(f" {'PASS' if ok else 'FAIL'}  {name}  ({ms:.0f} ms)")
    for name, err, tb in failed:
        print(f"\n--- {name} ---\n{tb}")
    total = f"{len(tests) - len(failed)}/{len(tests)} passed in {time.monotonic() - t_all:.1f} s"
    if HAVE_RICH:
        console.print(f"\n[bold {'red' if failed else 'green'}]{total}[/]")
    else:
        print("\n" + total)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
