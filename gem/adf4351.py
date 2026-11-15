"""ADF4351 register math and a Raspberry Pi SPI driver.

Frequency model (fundamental feedback):

    f_out = f_PFD * (INT + FRAC / MOD) / RF_DIV
    f_PFD = f_REF / R

    f_REF   reference crystal, 25 MHz on the EVAL board
    R       reference divider, 1 here, so f_PFD = 25 MHz
    INT     integer part of the feedback divider (>= 75 with the 8/9 prescaler)
    FRAC/MOD  fractional part; MOD = f_PFD / channel spacing = 2500 for 10 kHz
    RF_DIV  output divider (1, 2, 4 ... 64) keeping the VCO in 2200-4400 MHz

The register words match the open-source adf435x library at 5,049 test
frequencies; the only deliberate difference is the lock-detect timing bits,
set per the ADF4351 datasheet.
"""
import time
from math import gcd

from . import config

OUTPUT_POWER_CODE = {-4: 0, -1: 1, 2: 2, 5: 3}  # dBm -> R4 bits [4:3]


def calc(freq_mhz, ref_mhz=config.REF_MHZ, r_counter=1, spacing_khz=config.CHANNEL_KHZ):
    """Return (INT, FRAC, MOD, rf_div, pfd_mhz) for a target frequency."""
    if not config.SYNTH_MIN_MHZ <= freq_mhz <= config.SYNTH_MAX_MHZ:
        raise ValueError(f"{freq_mhz} MHz is outside {config.SYNTH_MIN_MHZ:.0f} to "
                         f"{config.SYNTH_MAX_MHZ:.0f} MHz")
    pfd = ref_mhz / r_counter
    rf_div = 1
    while freq_mhz * rf_div < 2200.0:  # VCO runs 2200 to 4400 MHz
        rf_div *= 2
    n = freq_mhz * rf_div / pfd
    mod = int(round(pfd * 1000.0 / spacing_khz))
    if mod > 4095:
        raise ValueError("MOD > 4095: use a coarser channel spacing")
    INT = int(n)
    frac = int(round((n - INT) * mod))
    if frac == mod:  # rounding pushed us to the next integer
        INT, frac = INT + 1, 0
    g = gcd(mod, frac) or mod
    mod, frac = mod // g, frac // g
    if mod == 1:
        mod = 2
    if INT < 75:  # 8/9 prescaler needs INT >= 75
        raise ValueError(f"INT={INT} < 75; lower the PFD (raise r_counter)")
    return INT, frac, mod, rf_div, pfd


def registers(freq_mhz, power_dbm=5, rf_on=True, ref_mhz=config.REF_MHZ, r_counter=1,
              spacing_khz=config.CHANNEL_KHZ):
    """Return [R0..R5] as 32-bit ints."""
    if power_dbm not in OUTPUT_POWER_CODE:
        raise ValueError(f"power must be one of {sorted(OUTPUT_POWER_CODE)} dBm")
    INT, frac, mod, rf_div, pfd = calc(freq_mhz, ref_mhz, r_counter, spacing_khz)
    int_n = frac == 0
    r0 = (INT << 15) | (frac << 3) | 0
    r1 = (1 << 27) | (1 << 15) | (mod << 3) | 1           # 8/9 prescaler, phase=1
    r2 = ((6 << 26)                                      # MUXOUT: digital lock detect
          | (r_counter << 14)
          | (7 << 9)                                     # charge pump 2.5 mA
          | ((1 if int_n else 0) << 8)                   # LDF: 0 frac-N, 1 int-N
          | ((1 if int_n else 0) << 7)                   # LDP: 10 ns frac, 6 ns int
          | (1 << 6)                                     # PD polarity positive
          | 2)
    r3 = ((1 if int_n else 0) << 22) | (150 << 3) | 3    # ABP; clock divider 150
    band_div = min(255, -(-int(pfd * 1000) // 125))      # band-select clock <= 125 kHz
    rf_div_sel = rf_div.bit_length() - 1
    r4 = ((1 << 23)                                      # fundamental feedback
          | (rf_div_sel << 20)
          | (band_div << 12)
          | ((1 if rf_on else 0) << 5)
          | (OUTPUT_POWER_CODE[power_dbm] << 3)
          | 4)
    r5 = (1 << 22) | (3 << 19) | 5                       # LD pin: digital lock detect
    return [r0, r1, r2, r3, r4, r5]


def actual_freq(freq_mhz, **kw):
    """The frequency the chip really makes for a requested one (grid-rounded)."""
    INT, frac, mod, rf_div, pfd = calc(freq_mhz, **kw)
    return pfd * (INT + frac / mod) / rf_div


class ADF4351:
    """Drive the ADF4351 over the Pi's SPI0.

    CE0 (GPIO8) acts as LE: spidev holds it low while clocking a word and
    raises it after, which latches the word into the register its 3 control
    bits name. SPI is write-only on this chip; the LD pin is the only way to
    see that it's alive.
    """

    def __init__(self, power_dbm=5, ref_mhz=config.REF_MHZ):
        import spidev
        from gpiozero import DigitalInputDevice, DigitalOutputDevice
        if power_dbm not in OUTPUT_POWER_CODE:
            raise ValueError(f"power must be one of {sorted(OUTPUT_POWER_CODE)} dBm")
        self.spi = spidev.SpiDev()
        self.spi.open(config.SPI_BUS, config.SPI_DEVICE)
        self.spi.mode = 0
        self.spi.max_speed_hz = config.SPI_HZ
        self._ce = DigitalOutputDevice(config.CE_GPIO, initial_value=True)
        self._ld = DigitalInputDevice(config.LD_GPIO)   # pulled down: floating reads 0
        self.power_dbm = power_dbm
        self.ref_mhz = ref_mhz
        self._regs = None

    # -- low level --
    def _write(self, word):
        self.spi.xfer2(list(word.to_bytes(4, "big")))

    # -- control --
    def set_freq(self, freq_mhz, rf_on=True, full=False):
        """Program a frequency. Only changed registers are sent, R0 last."""
        regs = registers(freq_mhz, self.power_dbm, rf_on, self.ref_mhz)
        if full or self._regs is None:
            order = [5, 4, 3, 2, 1, 0]           # full init, R5 first
        else:
            order = [i for i in (4, 3, 2, 1) if regs[i] != self._regs[i]] + [0]
        for i in order:
            self._write(regs[i])
        self._regs = regs

    def rf_enable(self, on):
        """Toggle only the RF output stage (R4); the PLL stays locked."""
        if self._regs is None:
            return
        r4 = self._regs[4]
        r4 = (r4 | (1 << 5)) if on else (r4 & ~(1 << 5))
        self._write(r4)
        self._regs[4] = r4

    def chip_enable(self, on):
        """Power the chip up or down through its CE pin. Powering down drops lock."""
        self._ce.value = bool(on)
        if not on:
            self._regs = None          # force a full rewrite after power-up

    def locked(self):
        return bool(self._ld.value)

    def wait_lock(self, timeout_s=config.LOCK_TIMEOUT_S):
        t_end = time.monotonic() + timeout_s
        while time.monotonic() < t_end:
            if self.locked():
                return True
            time.sleep(0.0002)
        return self.locked()

    def close(self):
        """RF off, then release SPI and both GPIO pins."""
        try:
            self.rf_enable(False)
        finally:
            for part in (self.spi, self._ce, self._ld):
                try:
                    part.close()
                except Exception:  # noqa: BLE001
                    pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
