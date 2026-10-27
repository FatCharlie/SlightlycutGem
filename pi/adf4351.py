"""ADF4351 register math and a Raspberry Pi SPI driver.

Frequency model (fundamental feedback):
    f_out = f_PFD * (INT + FRAC / MOD) / RF_DIV
    f_PFD = f_REF * (1 + doubler) / (R * (1 + rdiv2))

Defaults suit the common "35M-4.4GHz ADF4351 dev board": 25 MHz reference,
R = 1, so f_PFD = 25 MHz and a 10 kHz channel grid gives MOD = 2500.
"""
from math import gcd

REF_MHZ = 25.0
OUTPUT_POWER_CODE = {-4: 0, -1: 1, 2: 2, 5: 3}  # dBm -> R4 bits [4:3]


def calc(freq_mhz, ref_mhz=REF_MHZ, r_counter=1, spacing_khz=10.0):
    """Return (INT, FRAC, MOD, rf_div, pfd_mhz) for a target frequency."""
    if not 35.0 <= freq_mhz <= 4400.0:
        raise ValueError(f"{freq_mhz} MHz is outside 35 to 4400 MHz")
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


def registers(freq_mhz, power_dbm=5, rf_on=True, ref_mhz=REF_MHZ, r_counter=1,
              spacing_khz=10.0):
    """Return [R0..R5] as 32-bit ints."""
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
    INT, frac, mod, rf_div, pfd = calc(freq_mhz, **kw)
    return pfd * (INT + frac / mod) / rf_div


class ADF4351:
    """Drive the ADF4351 over the Pi's SPI0. CE0 (GPIO8) acts as LE:
    spidev holds it low while clocking a word and raises it after, which
    latches the word into the register its control bits name."""

    def __init__(self, bus=0, device=0, ce_gpio=25, ld_gpio=24, power_dbm=5,
                 ref_mhz=REF_MHZ, speed_hz=1_000_000):
        import spidev
        from gpiozero import DigitalInputDevice, DigitalOutputDevice
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.mode = 0
        self.spi.max_speed_hz = speed_hz
        self.chip_enable = DigitalOutputDevice(ce_gpio, initial_value=True)
        self.lock = DigitalInputDevice(ld_gpio) if ld_gpio is not None else None
        self.power_dbm = power_dbm
        self.ref_mhz = ref_mhz
        self._regs = None

    def _write(self, word):
        self.spi.xfer2(list(word.to_bytes(4, "big")))

    def set_freq(self, freq_mhz, rf_on=True):
        regs = registers(freq_mhz, self.power_dbm, rf_on, self.ref_mhz)
        if self._regs is None:
            order = [5, 4, 3, 2, 1, 0]          # full init, R5 first
        else:
            # R0 must come last; it starts the VCO band select.
            order = [i for i in (4, 3, 2, 1) if regs[i] != self._regs[i]] + [0]
        for i in order:
            self._write(regs[i])
        self._regs = regs

    def rf_enable(self, on):
        """Toggle only the RF output (R4), keeping the PLL locked."""
        r4 = self._regs[4]
        r4 = (r4 | (1 << 5)) if on else (r4 & ~(1 << 5))
        self._write(r4)
        self._regs[4] = r4

    def locked(self):
        return True if self.lock is None else bool(self.lock.value)

    def close(self):
        if self._regs is not None:
            self.rf_enable(False)
        self.spi.close()
