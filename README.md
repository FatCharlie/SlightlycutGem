# SlightlyCutGem

## *WARNING: AI Generated, I will start editing this as I put it together*

**A Raspberry Pi port of** [**Quantum Village's Uncut Gem**](https://github.com/QuantumVillage/UncutGem)**: a room-temperature quantum sensor built from a diamond, some off-the-shelf modules, and a Pi.**

SlightlyCutGem detects the electron spin resonance of nitrogen-vacancy (NV) centers in diamond, using optically detected magnetic resonance (ODMR). Shine green light on NV diamond and it glows red. Sweep a microwave frequency past 2.87 GHz and the glow dims slightly at resonance. Bring a magnet close and that dip splits in two. 

The original Uncut Gem runs on an ESP32 with a custom PCB. SlightlyCutGem keeps the same physics and the same RF modules, but moves the brains to a Raspberry Pi 4:

* **Python, not firmware.** Sweeps, averaging, CSV logging and plotting all happen in one script.
* **A 16-bit external ADC** in place of the ESP32's 12-bit one, for a clean signal.
* **Drift cancellation built in.** Every point is measured with the microwaves on and off.
* **A simulation mode**, so you can run the whole pipeline before buying anything.

> \\\*\\\*Status:\\\*\\\* the software runs end to end in simulation, and the synthesizer register math is checked against an independent library. Real-hardware bring-up is in progress. Reports, fixes and photos are very welcome.

\---

## How it works

An NV center is a defect in diamond: a nitrogen atom next to a missing carbon. Its trapped electrons form a spin-1 system with three states, m\_s = 0, +1 and −1. The microwave frequencies that flip the spin out of m\_s = 0 are

**f± = D ± γ·B∥**

* **D ≈ 2.87 GHz:** the zero-field splitting, set by the diamond itself.
* **γ ≈ 28 MHz/mT:** the electron gyromagnetic ratio; it converts magnetic field to frequency shift.
* **B∥:** the magnetic field component along the NV axis.

With no magnet, both transitions sit at 2.87 GHz: one dip. With a field, they split by 2γB∥: two dips. Example: 3 mT gives dips at 2870 ± 84 MHz.

Green light pumps the spins into the bright m\_s = 0 state. Microwaves at resonance move them into the dimmer m\_s = ±1 states, so the red fluorescence drops by a few percent at most. Microdiamond powder has every crystal orientation at once, so expect a broad dip of around 1% rather than sharp lines.
## Here’s the whole build. 

Think of it as two loops that meet at the diamond: a microwave path that pokes the spins, and an optical path that watches them.

```text
\---
                        ┌────────────────────────────┐
                        │      Raspberry Pi 4        │
                        │  (runs sweep.py)           │
                        └──┬──────┬──────┬───────┬───┘
                   USB port│   SPI │  I2C │  5 V  │ 3.3 V
          (USB-to-barrel)  │  pins │ pins │ pins  │ pin 1
                           │ 19,23,│  3,5 │  2,4  │
                           │ 24,22,│      │       │
                           │  18   │      │       │
                           ▼       ▼      │       │
                  ┌─────────────────┐     │       │
                  │ ADF4351 synth   │     │       │
                  │ (EVAL board)    │     │       │
                  │ 2.6 to 3.1 GHz  │     │       │
                  └────────┬────────┘     │       │
                    OUT+ SMA│             │       │
                           ▼              │       │
                  ┌─────────────────┐     │       │
                  │  RF amplifier   │◄────┼───5 V─┤ (pin 2)
                  │  ~+20 dBm max   │     │       │
                  └────────┬────────┘     │       │
                     SMA pigtail          │       │
                           ▼              │       │
     MICROWAVES ═══►  ( wire loop )       │       │
                    ┌────────────────┐    │       │
     GREEN LED ───► │  polymer block │    │       │
     (pin 4 + 100Ω) │   ◆ diamond    │    │       │
     527 nm         │     crystal    │    │       │
                    └───────┬────────┘    │       │
                     red glow (637-800 nm)│       │
                    ░░░ red gel ░░░       │       │
                     (blocks green)       │       │
                    ┌───────▼────────┐    │       │
                    │ BPW34          │    │       │
                    │ photodiode     │    │       │
                    └───────┬────────┘    │       │
                     tiny current (nA)    │       │
                    ┌───────▼────────┐    │       │
                    │ MCP6002 op-amp │◄───┼──3.3 V┘
                    │ (perfboard)    │    │
                    │ current→voltage│    │
                    └───────┬────────┘    │
                     voltage 0 to 3.3 V   │
                    ┌───────▼────────┐    │
                    │ ADS1115 ADC    │────┘  (I2C back to Pi)
                    │ 16-bit         │
                    └────────────────┘
```

## Hardware

### Parts

|Item|Part|Notes|Status|
|-|-|-|-|
|Computer|Raspberry Pi 4 Model B and official 5.1 V / 3 A supply|Other Pis with SPI and I2C should work; untested|Bought|
|Microwave synthesizer|"35M-4.4GHz ADF4351 development board"|The **bare** board with a control header and 25 MHz reference, not versions with an STM32 controller or touchscreen|Bought|
|RF amplifier|30 to 4000 MHz, 40 dB broadband amplifier board, 5 V|The same type the original Uncut Gem V1 used|Bought|
|RF cabling|SMA male-male cable (10 to 15 cm); SMA male to bare-wire pigtail|Pigtail carries the antenna loop|Needed|
|ADC|ADS1115 module (Adafruit 1085 or generic)|16-bit, I2C|Needed|
|Op-amp|Microchip MCP6002-I/P (DIP-8)|Rail-to-rail, runs on 3.3 V|Needed|
|Photodiode|Vishay BPW34||Needed|
|Light source|Bright green 5 mm LED, about 525 nm (e.g. Cree C503B-GCN-CY0C0791) plus 100 Ω resistor|A green laser module also works and gives a bigger signal|Needed|
|Red filter|Red lighting gel (e.g. LEE 106 Primary Red)|Blocks the green, passes the red fluorescence|Needed|
|NV diamond|Microdiamond with NV centers (e.g. Adámas Nanotechnologies low-nitrogen NV microdiamond)|The hard part to source; see below|Needed|
|Passives|10 MΩ, 1 MΩ, 10 kΩ resistors; 10 pF and 100 nF ceramic capacitors||Needed|
|Misc|Perfboard, DIP-8 socket, jumper wires, enameled copper wire (about 24 AWG), clear 2-part epoxy|Needed|


**On the diamond:** you need diamond with a meaningful concentration of NV centers; ordinary gem or industrial diamond won't do. Fluorescent NV microdiamond from a specialist supplier is the practical route. If you find a cheaper or hobby-friendly source, please open an issue.

### Wiring

Pi pins are physical header numbers. ADF4351 boards differ in header order between versions, so wire by the silkscreen labels.

|From|To|Notes|
|-|-|-|
|Pi pin 2 (5 V)|ADF4351 board 5 V, amp board 5 V|About 280 mA together|
|Pi pin 4 (5 V)|LED anode|LED cathode → 100 Ω → GND|
|Pi pin 6 (GND)|All grounds|One common ground|
|Pi pin 19 (GPIO10, MOSI)|ADF4351 DATA||
|Pi pin 23 (GPIO11, SCLK)|ADF4351 CLK||
|Pi pin 24 (GPIO8, CE0)|ADF4351 LE|Add 10 kΩ from LE to GND|
|Pi pin 22 (GPIO25)|ADF4351 CE|Chip enable, driven high by the software|
|Pi pin 18 (GPIO24)|ADF4351 LD|Lock detect, read by the software|
|Pi pin 1 (3.3 V)|ADS1115 VDD, op-amp pin 8|Leave the ADF4351 board's own 3.3 V pin unconnected|
|Pi pin 3 (GPIO2, SDA)|ADS1115 SDA||
|Pi pin 5 (GPIO3, SCL)|ADS1115 SCL|ADS1115 ADDR to GND (address 0x48)|
|ADF4351 RF out|Amp IN|SMA cable|
|Amp OUT|Antenna pigtail|Small enameled-wire loop right beside the diamond|

The SPI chip-select (CE0) doubles as the ADF4351's load-enable line. spidev holds it low while shifting each 32-bit word and raises it afterward, which latches the word into the register its control bits select.

### Photodiode amplifier

One transimpedance stage on a single 3.3 V supply, photodiode at zero bias. MCP6002 pins: 1 OUTA, 2 INA−, 3 INA+, 4 VSS, 5 INB+, 6 INB−, 7 OUTB, 8 VDD.

* Pin 8 to 3.3 V, pin 4 to GND, 100 nF between them.
* Pin 3 to GND.
* BPW34 cathode to pin 2, anode to GND.
* 10 MΩ and 10 pF in parallel between pin 1 and pin 2.
* Pin 1 to ADS1115 A0.
* Unused half: pin 5 to GND, pin 6 tied to pin 7.

**V\_out = I\_photo × R\_f.** With R\_f = 10 MΩ, 100 nA of photocurrent gives 1 V. Bandwidth is 1 / (2π · R\_f · C\_f) ≈ 1.6 kHz. Because the op-amp runs on 3.3 V, its output physically can't exceed the ADS1115's safe input range. If the baseline reads above about 3 V, swap R\_f for 1 MΩ.

### Diamond mount

Follow the original project's [DiamondMount notes](https://github.com/QuantumVillage/UncutGem/tree/main/hardware/DiamondMount). Embed the diamond in clear epoxy directly on the photodiode, with red gel between them. Diamond sinks in most epoxies, so build it up in layers. Hold the LED on stiff enameled wire so you can aim it at the diamond.

\---

## Software

Three small Python files, no Adafruit/Blinka dependency:

* `adf4351.py`: ADF4351 register math and SPI driver (25 MHz reference, 10 kHz channel grid). Register words match the open-source [adf435x](https://github.com/Ho-Ro/adf435x) library at 5,049 test frequencies; the only deliberate difference is the lock-detect timing bits, set per the ADF4351 datasheet.
* `ads1115.py`: minimal ADS1115 reader with auto-ranging.
* `sweep.py`: runs sweeps, averages, writes CSV, and optionally saves a PNG plot.

### Setup (Raspberry Pi OS Bookworm)

```bash
sudo raspi-config nonint do\\\_spi 0
sudo raspi-config nonint do\\\_i2c 0
sudo apt install -y python3-spidev python3-smbus2 python3-gpiozero python3-lgpio python3-matplotlib i2c-tools
```

Try it with no hardware connected:

```bash
python3 sweep.py --sim --plot                    # one dip at 2870 MHz
python3 sweep.py --sim --sim-field 3 --plot      # two dips, 2870 ± 84 MHz
```

### Running

```bash
i2cdetect -y 1                                   # ADS1115 should appear at 0x48
python3 sweep.py --sweeps 10 --plot              # 2614 to 3126 MHz, 4 MHz steps
python3 sweep.py --start 2820 --stop 2920 --step 0.5 --sweeps 20 --plot
python3 sweep.py --sweeps 10 --temp 21 --note "magnet 2 cm away" --plot
```

Key options:

|Option|Default|Meaning|
|-|-|-|
|`--start`, `--stop`, `--step`|2614, 3126, 4|Sweep range in MHz|
|`--sweeps`|5|Full sweeps to average|
|`--avg`|8|ADC samples per point|
|`--power`|5|Synth output in dBm (−4, −1, 2, 5)|
|`--no-ref`|off|Skip the microwave-off reading (faster, more drift)|
|`--temp`, `--note`|none|Logged in the CSV header|
|`--plot`|off|Save a PNG next to the CSV|
|`--sim`, `--sim-field`|off, 0|Simulated hardware; field in mT|

### Reading the output

Each frequency is measured with the microwaves on and off, and reported as contrast:

**C(f) = (V\_on(f) − V\_off(f)) / V\_off(f)**

* **V\_on:** photodiode voltage with microwaves on at frequency f.
* **V\_off:** the same measurement with microwaves off, taken moments later.
* **C:** fractional change; a resonance shows as a negative dip.

Dividing by V\_off cancels slow changes in LED brightness and temperature, a cheap version of what a lock-in amplifier does. The CSV has one row per frequency (`freq\\\_MHz, V\\\_on, V\\\_off, contrast`), plus a header line with the run settings.

To turn dip positions into a field, use the formula from earlier: B∥ = (f₊ − f₋) / (2 × 28 MHz/mT). Temperature also shifts D by about −74 kHz per kelvin, so log it.

\---

## Bring-up checklist

1. `sweep.py --sim --plot` works on your Pi.
2. Photodiode amp: near 0 V with the photodiode covered, rising in room light.
3. `i2cdetect -y 1` shows 0x48, and the reading changes when you shade the photodiode.
4. The ADF4351 lock-detect line reads high at 2614, 2870 and 3126 MHz.
5. The LED makes the diamond glow red through red film.
6. First sweep in a dim room shows a dip near 2870 MHz.
7. A small magnet widens or splits the dip, and it recovers when the magnet is removed.
8. Blocking the light makes the dip vanish. This proves you're seeing fluorescence, not electrical pickup.

## Troubleshooting

* **Nothing at 0x48:** check SDA/SCL, 3.3 V, ADDR to GND, and that I2C is enabled.
* **"PLL reported unlocked":** check CE is high, the LE pull-down, 5 V at the synth board, and that DATA and CLK aren't swapped. Confirm you have the bare board with a 25 MHz reference.
* **Reading stuck near 3.3 V:** the photodiode amp is saturated; use 1 MΩ feedback or shade stray light.
* **Reading stuck near 0 V:** photodiode reversed or not lit; the cathode goes to op-amp pin 2.
* **No dip:** check the amp has power, the SMA joints are tight and the loop is close. Then narrow the sweep and add more sweeps.

## Safety

* Treat a bright green LED like a laser for your eyes; never look into it or aim it at anyone. Lasers need proper eye protection.
* The amplifier puts out up to about 100 mW at 2.9 GHz; keep the antenna loop away from your face while running.
* Neodymium magnets pinch, chip, and wipe cards.
* Power down before rewiring anything on the Pi header.

\---

## Credits

SlightlyCutGem is a port of [Uncut Gem](https://github.com/QuantumVillage/UncutGem) by [Quantum Village](https://quantumvillage.org). The physics approach, optical design, diamond mount and choice of RF modules are theirs; the full design is described in their [arXiv paper](https://arxiv.org/abs/2509.18329). This port replaces the ESP32 firmware and PCB with Raspberry Pi software and off-the-shelf modules. All credit for the original idea goes to them; go star their repo.

## Contributing

Issues and pull requests are welcome, especially:

* Real-hardware results: sweeps, photos, which modules you used.
* Cheaper or easier NV diamond sources.
* Support for other Pi models or ADCs.
* A live-plot or web interface.

## License

AGPL-3.0, matching the upstream Uncut Gem project.

