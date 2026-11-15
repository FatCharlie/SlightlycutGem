# SlightlyCutGem

### Current Stage: 0 - all parts ordered and waiting on deliveries

**A Raspberry Pi port of the amazing [**Quantum Village's Uncut Gem**](https://github.com/QuantumVillage/UncutGem)**. This is aimed as a learning resource to understand the entire pipeline before building the PCB for UncutGem.

## Here’s the whole build

Think of it as two loops that meet at the diamond: a microwave path that pokes the spins, and an optical path that watches them.

```text
                    ┌────────────────────────────────┐
                    │     Raspberry Pi 4 Model B     │
                    │        (runs sweep.py)         │
                    └──┬──────────┬───────────────▲──┘
       SPI + CE + LD   │          │ 5 V (pins 2,4)│  I2C (SDA/SCL)
       via header P2   │          │ + USB barrel  │
                       ▼          │               │
   ┌───────────────────────┐      │      ┌────────┴────────┐
   │ ADF4351 EVAL synth    │◄─────┤      │ ADS1115 ADC     │
   │ sweeps 2614-3126 MHz  │      │      │ 16-bit, 0x48    │
   └──┬─────────────────┬──┘      │      └────────▲────────┘
  OUT+│             OUT−│         │               │ A0 (volts)
      │          50 Ω terminator  │      ┌────────┴────────┐
      │ 15 cm SMA jumper          │      │ MCP6002 op-amp  │
      ▼                           │      │ 10 MΩ ∥ 10 pF   │
   ┌───────────────────────┐      │      └────────▲────────┘
   │ 40 dB RF amp          │◄─────┘               │ photocurrent
   │ about +20 dBm out     │             ┌────────┴────────┐
   └──────────┬────────────┘             │ BPW34 photodiode│
              │ RG316 pigtail            └────────▲────────┘
              ▼                                   │ red only
        2-3 mm wire loop                 ┌────────┴────────┐
              │ microwaves               │ LEE 106 red gel │
              ▼                          └────────▲────────┘
   ┌───────────────────────────────────┐          │ red glow
   │  ENMDNV800 diamond block          ├──────────┘
   │  dims at the 2.87 GHz resonance   │
   └───────────────────────────────────┘
              ▲ green light
   ┌──────────┴────────────┐
   │ green LED + 100 Ω     │  5 V from Pi pin 4
   └───────────────────────┘
```

Left column: the microwave chain, from the Pi down to the diamond. Right column: the light readout, from the diamond back up to the Pi.

---

## How it works

An NV center is a defect in diamond: a nitrogen atom next to a missing carbon. Its trapped electrons form a spin-1 system with three states, m\_s = 0, +1 and −1. The microwave frequencies that flip the spin out of m\_s = 0 are

**f± = D ± γ·B∥**

* **D ≈ 2.87 GHz:** the zero-field splitting, set by the diamond itself.
* **γ ≈ 28 MHz/mT:** the electron gyromagnetic ratio; it converts magnetic field to frequency shift.
* **B∥:** the magnetic field component along the NV axis.

With no magnet, both transitions sit at 2.87 GHz: one dip. With a field, they split by 2γB∥: two dips. Example: 3 mT gives dips at 2870 ± 84 MHz.

Green light pumps the spins into the bright m\_s = 0 state. Microwaves at resonance move them into the dimmer m\_s = ±1 states, so the red fluorescence drops by a few percent at most. A single crystal has its NV centers along just four directions, so a magnet splits the dip into up to four separate pairs, one per direction, each at D ± γB∥ for that direction's share of the field. (Microdiamond powder has every orientation at once and gives one broad, smeared dip instead.)


SlightlyCutGem detects the electron spin resonance of nitrogen-vacancy (NV) centers in diamond, using optically detected magnetic resonance (ODMR). Shine green light on NV diamond and it glows red. Sweep a microwave frequency past 2.87 GHz and the glow dims slightly at resonance. Bring a magnet close and that dip splits in two. 

The original Uncut Gem runs on an ESP32 with a custom PCB. SlightlyCutGem keeps the same physics and the same RF modules, but moves the brains to a Raspberry Pi 4:

* **Python, not firmware.** Sweeps, averaging, CSV logging and plotting all happen in one script.
* **A 16-bit external ADC** in place of the ESP32's 12-bit one, for a clean signal.
* **Drift cancellation built in.** Every point is measured with the microwaves on and off.
* **A simulation mode**, so you can run the whole pipeline before buying anything.

> **Status:** the software runs end to end in simulation, and the synthesizer register math is checked against an independent library. Real-hardware bring-up is in progress. Reports, fixes and photos are very welcome.

## Hardware

### Parts

Status: **Received** = in hand, **Purchased** = ordered and on the way, **Needed** = still to buy.

|Item|Part|Notes|Status|
|-|-|-|-|
|Computer|Raspberry Pi 4 Model B and official 5.1 V / 3 A supply|Other Pis with SPI and I2C should work; untested|Received|
|Microwave synthesizer|"ADF435X EVAL Board" clone (ADF4351 with a CY7C68013A USB chip, 25 MHz reference, OUT+/OUT− SMA, barrel jack)|Pull the three P3 jumpers and drive it from the Pi through header P2. Avoid versions with an STM32 controller or touchscreen|Received|
|RF amplifier|30 to 4000 MHz, 40 dB broadband amplifier board, 5 V, SMA in and out|The same type the original Uncut Gem V1 used; check it's the 5 V version, not 12 V|Purchased|
|RF cabling|SMA male-male cable (10 to 15 cm); SMA male to bare-wire pigtail (RG316)|Pigtail carries the antenna loop|Received|
|Terminator|SMA **male** 50 Ω terminator, DC to 6 GHz (any power rating)|Caps the synth's unused OUT−; not RP-SMA. Optional, but keeps OUT+ power flat across the sweep|Purchased|
|ADC|ADS1115 module, pre-soldered header (Adafruit 1085 or generic)|16-bit, I2C|Purchased|
|Op-amp|Microchip MCP6002-I/P (DIP-8)|Rail-to-rail, runs on 3.3 V. The **-I/P** suffix is the through-hole version|Purchased|
|Photodiode|Vishay BPW34S (same part as BPW34, packed in tubes)|Through-hole, 430 to 1100 nm|Purchased|
|Light source|Cree C503B-GCN-CY0C0791 green 5 mm LED (527 nm, 30°) plus 100 Ω resistor|The default build|Purchased|
|Light source upgrade|520 nm **direct-diode** green **dot** laser module, 5 mW, 3 to 5 V with built-in driver, adjustable focus (6 × 27 mm brass)|Puts most of its 5 mW on the crystal for several times better sensitivity than the LED. Not 532 nm DPSS (leaks infrared), not a line laser|Purchased|
|Laser safety glasses|OD 4+ at 520 nm, rating printed on the frame|Required whenever the laser is powered; not needed for the LED build|Purchased|
|Red filter|Red lighting gel: LEE 106 Primary Red, or Rosco Roscolux #27 Medium Red (equivalent)|Blocks the green, passes the red fluorescence. Sold by photo and stage-lighting stores (B&H, Adorama, Full Compass, LEE Filters USA), not electronics suppliers. Two layers block more green than one|Purchased|
|NV diamond|Adámas [ENMDNV800](https://www.adamasnano.com/single-particle-sensors): 800 µm NV crystal in a 12.5 × 12.5 × 7 mm clear block|Single crystal, so a magnet gives separate dip pairs|Purchased|
|Capacitors|KEMET C315C100J5G5TA (10 pF C0G, 50 V, radial; or Vishay K100J15C0GF5TL2) and C320C104K5R5TA (100 nF X7R, radial)|Through-hole; surface-mount sizes (0402, 0603) won't fit a breadboard|Purchased|
|Resistors|100 Ω, 10 kΩ, 100 kΩ, 1 MΩ, 10 MΩ, ¼ W through-hole|LED; LE pull-down; and the photodiode amp feedback (10 MΩ, with 1 MΩ and 100 kΩ as fallbacks if it saturates)|Purchased|
|Breadboard and wiring|830-point solderless breadboard; Dupont jumper kit (M-M, M-F, F-F, 20 cm); GPIO T-Cobbler with 40-pin ribbon|See [for_dummies.md](for_dummies.md). Perfboard and a DIP-8 socket only for a later permanent build|Purchased|
|Tools|Multimeter, soldering iron, wire strippers, flush cutters, craft knife, heat-shrink|For the antenna loop and checks during assembly|Needed|
|Magnet|Small neodymium disc, about 6 to 10 mm|For the magnet test: splits the dip into pairs. Field falls off as about 1/distance³, so distance sets the splitting|Purchased|
|ESD wrist strap|Antistatic wrist strap with coiled cord and clip|The MCP6002 and ADF4351 are static-sensitive; dry winter air makes it worse. Clip to a grounded point; no mat needed|Purchased|
|Helping hands|Clamp stand with alligator clips|Holds the LED or laser aimed at the crystal, and the coax while soldering the loop|Purchased|
|Optional|Clear 2-part epoxy|Fixes the block, gel and photodiode once everything works; Blu Tack or tape until then|Needed|

**Still to buy:** nothing, apart from any tools you don't already own. Everything else for the first build is ordered or in hand.

**On the diamond:** you need diamond with a meaningful concentration of NV centers; ordinary gem or industrial diamond won't do. Fluorescent NV microdiamond from a specialist supplier is the practical route. If you find a cheaper or hobby-friendly source, please open an issue.

### Wiring

New to wiring? [for_dummies.md](for_dummies.md) walks through the whole assembly step by step, including how to find each Pi pin and which connectors to buy.

Pi pins are physical header numbers; the same assignments live in code in `gem/config.py`. Wire the synth by the silkscreen labels on its 10-pin header P2 (LE, CLK, DAT, GD, 3V3 on one row; MUX, LD, PDR, CE, GD on the other). Before wiring, pull the three green jumpers on header P3: they connect the board's own USB chip to the same control lines. Leave P2's 3V3, MUX and PDR unconnected.

|From|To|Notes|
|-|-|-|
|Pi USB port|ADF4351 board barrel jack|The included USB-to-barrel cable; about 110 to 145 mA|
|Pi pin 2 (5 V)|Amp board 5 V|About 135 mA|
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
|ADF4351 OUT+|Amp IN|Short SMA male-male cable|
|ADF4351 OUT−|50 Ω SMA terminator|Never put the terminator on the amp output|
|Amp OUT|Antenna pigtail|RG316 pigtail: cut off any bare-wire leads and bend the coax's centre conductor into a 2 to 3 mm loop soldered to the braid; lay it flat against the diamond|

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

---

## Software

```
RPI4b_SETUP.sh one-time Pi setup: SPI, I2C, packages (run with sudo)
check_hw.py    hardware check: tests every part and shows what's ready
sweep.py       runs ODMR sweeps, writes CSV, finds dips, optional PNG plot
selftest.py    checks the software with no hardware attached (fake SPI/GPIO/I2C)
gem/
  config.py    every pin, address and constant, in one place
  adf4351.py   synthesizer register math and SPI driver
  ads1115.py   16-bit ADC on I2C, with auto-ranging
  hardware.py  the real rig and a simulated one behind the same interface
  odmr.py      the sweep loop, dip finder, CSV and plot
  report.py    terminal tables (rich if installed, plain text if not)
```

No Adafruit/Blinka dependency and no test framework: everything is a plain `python3 <script>.py`. The ADF4351 register words match the open-source [adf435x](https://github.com/Ho-Ro/adf435x) library at 5,049 test frequencies; the only deliberate difference is the lock-detect timing bits, set per the ADF4351 datasheet.

### Setup (Raspberry Pi OS Bookworm)

From the repo folder:

```bash
sudo ./RPI4b_SETUP.sh
sudo reboot
```

`RPI4b_SETUP.sh` turns on SPI and I2C with `raspi-config`, installs the apt packages (spidev, smbus2, gpiozero, lgpio, matplotlib, rich, i2c-tools, git), and adds your user to the spi, i2c and gpio groups. It has to run as root; without `sudo` it stops with "You need to run as root for raspi-config".

Then, from the repo folder:

```bash
python3 selftest.py                              # software check, no hardware needed
python3 sweep.py --sim --plot                    # one dip at 2870 MHz
python3 sweep.py --sim --sim-field 3 --plot      # four dips: 2870 ± 84 and 2870 ± 28 MHz
```

### Hardware check

`check_hw.py` tests each part and prints a table of what's ready, with the fix for anything that isn't, then a summary of which bring-up steps you can do now.

```bash
python3 check_hw.py                     # everything
python3 check_hw.py --only adf4351      # just the synthesizer (also: pi, packages, adc, manual)
python3 check_hw.py --interactive       # adds a cover-the-photodiode test
python3 check_hw.py --have amp,loop,led # parts you've fitted that nothing can detect
```

* **Pi:** board, Python version, SPI and I2C enabled, packages installed (with one `apt` line for anything missing).
* **ADS1115:** probes all four addresses its ADDR pin can select, so a wrong ADDR is called out, then reads A0 and flags dark or saturated.
* **ADF4351:** SPI is write-only on this chip, so the evidence is the lock-detect pin. The check programs 2614, 2870 and 3126 MHz and requires LD to go high at each, then pulls CE low and requires LD to drop. That second step proves LD really comes from the chip and isn't floating high or tied to 3.3 V. The RF output stays off the whole time.
* **RF amp, loop, terminator, LED, diamond:** no digital interface, so they can't be detected. List the fitted ones with `--have`; the summary then knows what you're still waiting on.

It exits non-zero if anything failed, so it can gate other scripts.

### Running

```bash
python3 sweep.py --sweeps 10 --plot              # 2614 to 3126 MHz, 4 MHz steps
python3 sweep.py --start 2820 --stop 2920 --step 0.5 --sweeps 20 --plot
python3 sweep.py --sweeps 10 --temp 21 --note "magnet 2 cm away" --plot
```

Ctrl-C stops early and still saves the sweeps that finished. After each run the script lists the dips it found and, if there are at least two, the field along the most-aligned NV axis.

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
|`--sim`, `--sim-field`|off, 0|Simulated single crystal; field in mT along one NV axis|

### Reading the output

Each frequency is measured with the microwaves on and off, and reported as contrast:

**C(f) = (V\_on(f) − V\_off(f)) / V\_off(f)**

* **V\_on:** photodiode voltage with microwaves on at frequency f.
* **V\_off:** the same measurement with microwaves off, taken moments later.
* **C:** fractional change; a resonance shows as a negative dip.

Dividing by V\_off cancels slow changes in LED brightness and temperature, a cheap version of what a lock-in amplifier does. The CSV has one row per frequency (`freq_MHz, V_on, V_off, contrast`), plus a header line with the run settings.

To turn dip positions into a field, use the formula from earlier: B∥ = (f₊ − f₋) / (2 × 28 MHz/mT). Temperature also shifts D by about −74 kHz per kelvin, so log it.

---

## Bring-up checklist

`check_hw.py` checks steps 2 to 4 for you.

1. `python3 selftest.py` and `python3 sweep.py --sim --plot` work on your Pi.
2. `python3 check_hw.py --only pi --only packages` is all green.
3. `python3 check_hw.py --only adc --interactive`: the ADS1115 answers at 0x48 and the reading drops when you cover the photodiode.
4. `python3 check_hw.py --only adf4351`: the synth locks at 2614, 2870 and 3126 MHz, and LD drops when it's powered down.
5. The LED makes the diamond glow red through red film.
6. First sweep in a dim room shows a dip near 2870 MHz.
7. A small magnet splits the dip into pairs, and it recovers when the magnet is removed.
8. Blocking the light makes the dip vanish. This proves you're seeing fluorescence, not electrical pickup.

## Troubleshooting

* **Nothing at 0x48:** check SDA/SCL, 3.3 V, ADDR to GND, and that I2C is enabled.
* **"PLL reported unlocked" or `check_hw.py` says no lock:** check the barrel power, that the three P3 jumpers are out, the LE pull-down, and that DATA and CLK aren't swapped.
* **`check_hw.py` says LD is stuck high:** the LD wire is on the wrong header pin (3V3 or MUX).
* **Reading stuck near 3.3 V:** the photodiode amp is saturated; use 1 MΩ feedback or shade stray light.
* **Reading stuck near 0 V:** photodiode reversed or not lit; the cathode goes to op-amp pin 2.
* **No dip:** check the amp has power, the SMA joints are tight and the loop is close. Then narrow the sweep and add more sweeps.

## Safety

* Treat a bright green LED like a laser for your eyes; never look into it or aim it at anyone.
* **With the laser:** wear OD 4+ at 520 nm glasses whenever it's powered. Even 5 mW reflected off the polymer block can damage your eye faster than you can blink. Remove watches and rings, keep the beam below eye level, and put something matte behind the block to catch whatever passes through.
* The amplifier puts out up to about 100 mW at 2.9 GHz; keep the antenna loop away from your face while running.
* Neodymium magnets pinch, chip, and wipe cards.
* Power down before rewiring anything on the Pi header.

---

## Credits

SlightlyCutGem is a port of [Uncut Gem](https://github.com/QuantumVillage/UncutGem) by [Quantum Village](https://quantumvillage.org). The physics approach, optical design, diamond mount and choice of RF modules are theirs; the full design is described in their [arXiv paper](https://arxiv.org/abs/2509.18329). This port replaces the ESP32 firmware and PCB with Raspberry Pi software and off-the-shelf modules. All credit for the original idea goes to them; go star their repo.

## License

AGPL-3.0, matching the upstream Uncut Gem project.

