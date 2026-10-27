"""Minimal ADS1115 reader over I2C (no Adafruit/Blinka dependency).

Single-ended input AINx against GND. Full-scale ranges (volts) per PGA code:
    0: 6.144  1: 4.096  2: 2.048  3: 1.024  4: 0.512  5: 0.256
Volts per count = FSR / 32768. Only 0 V to VDD is a legal input; with VDD =
3.3 V, the 6.144 and 4.096 ranges just let 3.3 V read without clipping.
"""
import time

FSR = {0: 6.144, 1: 4.096, 2: 2.048, 3: 1.024, 4: 0.512, 5: 0.256}
RATE_CODE = {8: 0, 16: 1, 32: 2, 64: 3, 128: 4, 250: 5, 475: 6, 860: 7}


class ADS1115:
    def __init__(self, bus=1, address=0x48, channel=0, pga=1, rate=860):
        try:
            from smbus2 import SMBus
        except ImportError:
            from smbus import SMBus
        self.bus = SMBus(bus)
        self.addr = address
        self.channel = channel
        self.rate = rate
        self.set_pga(pga)

    def set_pga(self, pga):
        self.pga = pga
        mux = 0b100 + self.channel                     # AINx vs GND
        config = ((0 << 15)                            # no single-shot trigger
                  | (mux << 12)
                  | (pga << 9)
                  | (0 << 8)                           # continuous conversion
                  | (RATE_CODE[self.rate] << 5)
                  | 0b00011)                           # comparator off
        self.bus.write_i2c_block_data(self.addr, 0x01, [config >> 8, config & 0xFF])
        time.sleep(3.0 / self.rate)                    # let the new setting settle

    def read_volts(self):
        hi, lo = self.bus.read_i2c_block_data(self.addr, 0x00, 2)
        raw = (hi << 8) | lo
        if raw & 0x8000:
            raw -= 1 << 16
        return raw * FSR[self.pga] / 32768.0

    def average(self, n):
        """Average n fresh conversions (one per conversion period)."""
        period = 1.0 / self.rate
        total = 0.0
        for _ in range(n):
            time.sleep(period)
            total += self.read_volts()
        return total / n

    def autorange(self, volts):
        """Pick the most sensitive range that still holds `volts` with 20% headroom."""
        for pga in (5, 4, 3, 2, 1):
            if volts * 1.2 < FSR[pga]:
                return pga
        return 1
