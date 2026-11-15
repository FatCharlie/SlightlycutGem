"""Every pin, address and constant the build uses, in one place.

Pin numbers in comments are physical header pins; the values are BCM GPIO
numbers, which is what gpiozero and spidev expect.
"""

# --- ADF4351 synthesizer (SPI0) ---------------------------------------------
SPI_BUS = 0
SPI_DEVICE = 0            # CE0 = GPIO8 = pin 24, wired to the board's LE
SPI_HZ = 1_000_000
CE_GPIO = 25              # pin 22 -> CE (chip enable)
LD_GPIO = 24              # pin 18 <- LD (lock detect)
REF_MHZ = 25.0            # reference crystal on the EVAL board
CHANNEL_KHZ = 10.0        # frequency grid; gives MOD = 2500 at a 25 MHz PFD
SYNTH_MIN_MHZ = 35.0
SYNTH_MAX_MHZ = 4400.0
LOCK_TIMEOUT_S = 0.01     # PLL usually locks in well under 1 ms

# --- ADS1115 ADC (I2C1) -----------------------------------------------------
I2C_BUS = 1               # SDA pin 3, SCL pin 5
ADC_ADDR = 0x48           # ADDR tied to GND
ADC_CHANNEL = 0           # A0 <- photodiode amp output
ADC_RATE = 860            # samples/s, the chip's fastest

# --- NV physics -------------------------------------------------------------
D_MHZ = 2870.0            # zero-field splitting
GAMMA_MHZ_PER_MT = 28.0   # electron gyromagnetic ratio

# --- default sweep ----------------------------------------------------------
SWEEP_START_MHZ = 2614.0  # D - 256 MHz
SWEEP_STOP_MHZ = 3126.0   # D + 256 MHz
SWEEP_STEP_MHZ = 4.0
