# Uncut Gem on a Raspberry Pi 4

ODMR sweep software and wiring for the Pi version of the NV diamond Stage 1 build. The Pi replaces the Uncut Gem's ESP32; the RF hardware is the same module pair V1 used (ADF4351 dev board plus a 40 dB amplifier board).

## Files

- `adf4351.py`: register math and SPI driver for the ADF4351 (25 MHz reference, 10 kHz grid). Register words are cross-checked against the open-source `adf435x` library at 5,049 frequencies with zero mismatches; the only deliberate difference is the lock-detect timing bits, set per the ADF4351 datasheet.
- `ads1115.py`: minimal I2C reader for the ADS1115 (no Adafruit/Blinka needed).
- `sweep.py`: runs sweeps, averages, writes CSV, optional PNG plot. `--sim` runs with fake hardware.

## Setup (Raspberry Pi OS Bookworm)

```
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo apt install -y python3-spidev python3-smbus2 python3-gpiozero python3-lgpio python3-matplotlib i2c-tools
i2cdetect -y 1        # ADS1115 should show at 0x48
python3 sweep.py --sim --plot
```

## Wiring

Pi header pins are physical pin numbers. Match the ADF4351 board by its silkscreen labels; pin order differs between board versions.

| From | To | Notes |
|---|---|---|
| Pi pin 2 (5 V) | ADF4351 board 5 V in, amp board 5 V | About 280 mA together |
| Pi pin 4 (5 V) | LED anode | LED cathode → 100 Ω → GND |
| Pi pin 6 (GND) | ADF4351 GND, amp GND, ADS1115 GND, op-amp pin 4 | One common ground |
| Pi pin 19 (GPIO10, MOSI) | ADF4351 DATA | |
| Pi pin 23 (GPIO11, SCLK) | ADF4351 CLK | |
| Pi pin 24 (GPIO8, CE0) | ADF4351 LE | Add 10 kΩ from LE to GND |
| Pi pin 22 (GPIO25) | ADF4351 CE | Chip enable, driven high by the script |
| Pi pin 18 (GPIO24) | ADF4351 LD | Lock detect, read by the script |
| Pi pin 1 (3.3 V) | ADS1115 VDD, op-amp pin 8 | Do not connect the ADF4351 board's own 3.3 V pin |
| Pi pin 3 (GPIO2, SDA) | ADS1115 SDA | |
| Pi pin 5 (GPIO3, SCL) | ADS1115 SCL | ADS1115 ADDR to GND (address 0x48) |
| ADF4351 RFout+ (SMA) | Amp IN (SMA) | Short SMA male-male cable |
| Amp OUT (SMA) | Antenna loop | SMA pigtail with a small enameled-wire loop by the diamond |

## Photodiode amplifier (perfboard)

One stage, zero bias, single 3.3 V supply. MCP6002 (DIP-8) pins: 1 OUTA, 2 INA−, 3 INA+, 4 VSS, 5 INB+, 6 INB−, 7 OUTB, 8 VDD.

- Pin 8 to 3.3 V, pin 4 to GND, 100 nF from pin 8 to pin 4.
- Pin 3 to GND.
- BPW34 cathode to pin 2, anode to GND.
- 10 MΩ and 10 pF in parallel between pin 1 and pin 2.
- Pin 1 to ADS1115 A0.
- Unused half: pin 5 to GND, pin 6 tied to pin 7.

Output: V = I_photo × R_f. With R_f = 10 MΩ, 100 nA of photocurrent gives 1 V. Bandwidth f = 1 / (2π R_f C_f) ≈ 1.6 kHz. The output can only swing 0 to 3.3 V, which is exactly the ADS1115's legal input range on a 3.3 V supply. If the baseline sits above about 3 V, swap R_f to 1 MΩ.

## Running

```
python3 sweep.py --start 2614 --stop 3126 --step 4 --sweeps 10 --temp 21 --plot
python3 sweep.py --start 2820 --stop 2920 --step 0.5 --sweeps 20 --plot
```

By default each point is read with the microwaves on and off, and the script reports contrast C = (V_on − V_off) / V_off. A dip near 2870 MHz shows as negative contrast; a magnet splits it into two dips at 2870 ± 28·B∥ MHz (B∥ in mT).
