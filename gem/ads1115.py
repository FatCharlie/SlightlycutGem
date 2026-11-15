"""Minimal ADS1115 reader over I2C (no Adafruit/Blinka dependency).

Single-ended input AINx against GND. Full-scale ranges (volts) per PGA code:

    0: 6.144  1: 4.096  2: 2.048  3: 1.024  4: 0.512  5: 0.256

Volts per count = FSR / 32768. Only 0 V to VDD is a legal input; with VDD =
3.3 V, the 6.144 and 4.096 ranges simply let 3.3 V read without clipping.
"""
import time

from . import config

FSR = {0: 6.144, 1: 4.096, 2: 2.048, 3: 1.024, 4: 0.512, 5: 0.256}
RATE_CODE = {8: 0, 16: 1, 32: 2, 64: 3, 128: 4, 250: 5, 475: 6, 860: 7}
REG_CONVERSION, REG_CONFIG = 0x00, 0x01


def open_bus(bus=config.I2C_BUS):
    try:
        from smbus2 import SMBus
    except ImportError:
        try:
            from smbus import SMBus
        except ImportError:
            raise ImportError("smbus2 isn't installed (sudo apt install -y python3-smbus2)") from None
    return SMBus(bus)


def config_word(channel, pga, rate):
    """Continuous conversion of AIN<channel> vs GND, comparator off."""
    mux = 0b100 + channel
    return ((mux << 12) | (pga << 9) | (0 << 8)       # bit 8 = 0: continuous
            | (RATE_CODE[rate] << 5) | 0b00011)


def counts_to_volts(hi, lo, pga):
    raw = (hi << 8) | lo
    if raw & 0x8000:
        raw -= 1 << 16
    return raw * FSR[pga] / 32768.0


def probe(addresses=(0x48, 0x49, 0x4A, 0x4B), bus=config.I2C_BUS):
    """Return the addresses (of the four ADDR can select) that answer."""
    b = open_bus(bus)
    found = []
    try:
        for addr in addresses:
            try:
                b.read_i2c_block_data(addr, REG_CONFIG, 2)
                found.append(addr)
            except OSError:
                pass
    finally:
        b.close()
    return found


class ADS1115:
    def __init__(self, channel=config.ADC_CHANNEL, pga=1, rate=config.ADC_RATE,
                 address=config.ADC_ADDR, bus=config.I2C_BUS):
        self.bus = open_bus(bus)
        self.addr = address
        self.channel = channel
        self.rate = rate
        self.pga = None
        self.set_pga(pga)

    def set_pga(self, pga):
        self.pga = pga
        word = config_word(self.channel, pga, self.rate)
        self.bus.write_i2c_block_data(self.addr, REG_CONFIG, [word >> 8, word & 0xFF])
        time.sleep(3.0 / self.rate)                    # let the new setting settle

    @property
    def full_scale(self):
        return FSR[self.pga]

    def read_volts(self):
        hi, lo = self.bus.read_i2c_block_data(self.addr, REG_CONVERSION, 2)
        return counts_to_volts(hi, lo, self.pga)

    def average(self, n):
        """Average n fresh conversions (one per conversion period)."""
        period = 1.0 / self.rate
        total = 0.0
        for _ in range(n):
            time.sleep(period)
            total += self.read_volts()
        return total / n

    def autorange(self, n=8):
        """Pick the most sensitive range that holds the signal with 20% headroom."""
        self.set_pga(1)
        v = self.average(n)
        for pga in (5, 4, 3, 2, 1):
            if v * 1.2 < FSR[pga]:
                self.set_pga(pga)
                break
        return v

    def close(self):
        self.bus.close()
