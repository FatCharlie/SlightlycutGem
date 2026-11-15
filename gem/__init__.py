"""SlightlyCutGem: ODMR on NV diamond with a Raspberry Pi.

    config.py    every pin, address and constant, in one place
    adf4351.py   microwave synthesizer: register math + SPI driver
    ads1115.py   16-bit ADC on I2C
    hardware.py  the Pi rig and a simulated rig behind one interface
    odmr.py      the sweep itself, CSV and plot output
    report.py    status tables for the terminal (rich, with a plain fallback)
"""
