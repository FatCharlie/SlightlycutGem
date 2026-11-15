# SlightlyCutGem for Dummies: the assembly

This guide walks through building the hardware from a pile of parts, assuming you've never wired electronics before. It covers only the physical build. The [README](README.md) covers the software, and how to check that each part works once it's wired.

You don't need to understand the physics to build this. The short version is in the README.

---

## 1. What you're building

Two chains meet at a diamond.

```text
  MICROWAVE CHAIN (makes the radio signal)        LIGHT CHAIN (watches the diamond)

  Raspberry Pi                                    green LED ──► shines on the diamond
     │ tells it which frequency                                     │
     ▼                                                              ▼ diamond glows red
  ADF4351 synthesizer board                                     red filter (lets only red through)
     │ coax cable                                                   │
     ▼                                                              ▼
  RF amplifier board                                            photodiode (light → tiny current)
     │ coax cable                                                   │
     ▼                                                              ▼
  wire loop antenna ──► sits against the diamond                op-amp (tiny current → voltage)
                                                                    │
                                                                    ▼
                                                                ADS1115 (voltage → number)
                                                                    │
                                                                    ▼
                                                                Raspberry Pi
```

You'll build it in this order: the light-chain electronics on a breadboard first (nothing in it can hurt anything), then the synthesizer, then the amplifier and antenna, then the diamond mount.

---

## 2. Safety, before anything else

* **Unplug the Pi before you change any wire.** Every time. Most beginner damage comes from moving a wire while the power is on and brushing the wrong pin.
* **Never connect 5 V to anything marked 3.3 V, or to any Pi pin other than the 5 V and GND pins.** The Pi's signal pins are 3.3 V only, and 5 V kills them instantly with no warning.
* **The green LED is bright.** Don't look straight into it.
* **The amplifier radiates up to about 100 mW at 2.9 GHz** (similar to a Wi-Fi router). Keep the loop away from your face while it runs.
* **Soldering irons run at about 350 °C.** Use the stand, solder in a ventilated spot, and wash your hands after handling solder.

---

## 3. Connectors, wires and other new words

### Header pins

A **header** is a row of metal pins (male) or sockets (female) spaced 2.54 mm (0.1 inch) apart. The Pi has a 40-pin male header along one edge. The synth board has a 10-pin male header (P2). The ADS1115 module usually arrives with a loose strip of header pins that you solder on yourself.

### Jumper wires ("Dupont wires")

These are what plug into header pins. Each end is one of two kinds:

* **Male:** a pin. It plugs into a female socket or a breadboard hole.
* **Female:** a socket. It slides onto a male pin.

They're sold as **M-M, M-F and F-F**, and you need all three. Buy a mixed kit; search for **"Dupont jumper wire kit 120 pcs 20 cm"** (about $7). The colours mean nothing electrically, but if you use red for 5 V and 3.3 V, black for GND, and other colours for signals, mistakes become easy to spot.

### Breadboard

A **solderless breadboard** is a plastic block full of holes. Push a wire or a part's leg into a hole and it grips it. Hidden metal strips connect certain holes together:

```text
   + ─────────────────────────────────────  ◄ power rail: the whole line is connected
   − ─────────────────────────────────────  ◄ ground rail: the whole line is connected

     1   2   3   4   5   6   7   8 ...
  a  ●   ●   ●   ●   ●   ●   ●   ●
  b  ●   ●   ●   ●   ●   ●   ●   ●      Each numbered COLUMN of a-e is one connection:
  c  ●   ●   ●   ●   ●   ●   ●   ●      a1, b1, c1, d1, e1 are all joined.
  d  ●   ●   ●   ●   ●   ●   ●   ●
  e  ●   ●   ●   ●   ●   ●   ●   ●
     ══════════ centre trench ═════════    Nothing crosses the trench.
  f  ●   ●   ●   ●   ●   ●   ●   ●
  g  ●   ●   ●   ●   ●   ●   ●   ●      f1, g1, h1, i1, j1 are joined,
  h  ●   ●   ●   ●   ●   ●   ●   ●      but NOT to a1 to e1.
  i  ●   ●   ●   ●   ●   ●   ●   ●
  j  ●   ●   ●   ●   ●   ●   ●   ●

   + ─────────────────────────────────────
   − ─────────────────────────────────────
```

Two things to watch:

* On some breadboards the power rails are split in the middle (look for a gap in the printed red/blue line). If yours is split, bridge the gap with a short wire.
* "Connected" means connected. Two part legs in the same 5-hole group are wired together, whether you meant it or not.

Buy an **830-point breadboard** (about $6). The README says perfboard, which is for a permanent soldered version later. A breadboard needs no soldering and is easy to change, which is what you want for a first build.

### GPIO breakout ("T-Cobbler")

This is strongly recommended. A **T-Cobbler** (Adafruit "Pi T-Cobbler Plus", or a generic "GPIO T-type breakout board with 40-pin ribbon cable", about $7) carries the Pi's 40 pins onto your breadboard through a ribbon cable. Its biggest advantage is that **every pin is labelled in print**, so you're not counting pins on the Pi.

### Coax and SMA

**Coax** is the round cable with a centre wire inside a woven shield (the copper-coloured RG316 you bought). Microwaves have to travel in coax; an ordinary wire would radiate them away.

**SMA** is the small threaded gold connector on the coax ends and on the RF boards.

* **SMA male (plug):** a pin in the centre, with the threads on the inside of a turning nut. All your cables have this.
* **SMA female (jack):** a hole in the centre, with the threads on the outside. The boards have this.

To connect one, line it up straight, then turn **only the nut** (not the cable) until it's finger-tight, then about 1/8 turn more. Don't force it. Cross-threading ruins the connector.

### Barrel jack

The round power socket on the synth board. Your board came with a cable that has a USB-A plug at one end and the barrel plug at the other.

### Polarity

Some parts only work one way round, and some are damaged if reversed: the LED, photodiode, op-amp chip, ADS1115 and amp board. Each one's markings are explained when you meet it.

---

## 4. The Pi's 40 pins: how to read "Pi pin 19 (GPIO10, MOSI)"

**The pins are not labelled on the Pi.** You find them by position. Every pin has three names, and the README gives all three:

| Name type | Example | What it means |
|---|---|---|
| **Physical pin number** | pin 19 | Its position on the header: count to it. **This is the one you wire by.** |
| **GPIO number** | GPIO10 | The name the processor (and the software) uses. Has nothing to do with position. |
| **Function** | MOSI | The special job that pin can do. MOSI = "master out, slave in", the SPI data line from the Pi. |

So "Pi pin 19 (GPIO10, MOSI)" means: the 19th pin on the header, which the software calls GPIO10, and which carries SPI data out.

### Finding pin 1

Lay the Pi flat, components up, with the 40-pin header along the **top** edge and the USB and Ethernet ports on the **right**. Then:

```text
                    the board edge is up here
     pin 2 ► ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ● ◄ pin 40     ┌──────┐
     pin 1 ► ■  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ● ◄ pin 39     │ USB  │
                                                                                     │ ETH  │
             (towards the middle of the board)                                       └──────┘
```

* **Pin 1** is the end furthest from the USB ports, on the row nearer the middle of the board.
* **Odd pins (1, 3, 5 … 39)** are on that inner row; **even pins (2, 4, 6 … 40)** are on the outer row along the board edge.
* Pin 1 is the only one soldered to a **square pad**; turn the Pi over and look.
* To double-check, run `pinout` in a terminal on the Pi. It draws this map with the names.

### The pins this build uses

Pins sit in pairs across the two rows (1 and 2, 3 and 4, and so on). Only the first 24 pins are used; `·` means "not used".

```text
 pin pair →   1/2   3/4   5/6   7/8   9/10  11/12 13/14 15/16 17/18 19/20 21/22 23/24
 outer row:   5V    5V    GND   ·     ·     ·     ·     ·     LD    ·     CE    LE
   (pin no.)  2     4     6                                   18          22    24
 inner row:   3V3   SDA   SCL   ·     ·     ·     ·     ·     ·     DAT   ·     CLK
   (pin no.)  1     3     5                                         19          23
```

LD, CE, LE, DAT and CLK are the synth board pins each Pi pin connects to.

| Pin | GPIO | Function | Goes to | T-Cobbler label (wording varies by brand) |
|---|---|---|---|---|
| 1 | | 3.3 V power | ADS1115 VDD, op-amp pin 8 | 3V3 / 3.3V |
| 2 | | 5 V power | Amp board + | 5V / 5.0V |
| 4 | | 5 V power | LED (through its resistor) | 5V |
| 6 | | Ground | Everything's GND | GND |
| 3 | GPIO2 | I2C data (SDA) | ADS1115 SDA | SDA |
| 5 | GPIO3 | I2C clock (SCL) | ADS1115 SCL | SCL |
| 19 | GPIO10 | SPI data out (MOSI) | Synth DAT | MOSI |
| 23 | GPIO11 | SPI clock (SCLK) | Synth CLK | SCLK / SCK |
| 24 | GPIO8 | SPI chip select (CE0) | Synth LE | CE0 / #8 |
| 22 | GPIO25 | plain GPIO | Synth CE | #25 / G25 |
| 18 | GPIO24 | plain GPIO | Synth LD | #24 / G24 |

Pins 9, 14, 20, 25, 30, 34 and 39 are also GND; any of them will do.

With a T-Cobbler you can ignore pin numbers entirely and wire by the printed labels.

---

## 5. Parts tour: what each board is and what's printed on it

| Part | What it does | Labels to look for |
|---|---|---|
| **ADF4351 EVAL board** (synthesizer) | Makes the microwave signal | Header **P2**: `LE CLK DAT GD 3V3` on one row, `MUX LD PDR CE GD` on the other. **P3**: three green jumper caps. SMA jacks **OUT+** and **OUT−**. Barrel jack. |
| **RF amplifier** | Boosts the signal about 10,000× | SMA jacks marked **IN** and **OUT** (or RF IN / RF OUT, or an arrow showing direction). Power pads or pins marked **+ / −** or **VCC / GND**. |
| **ADS1115 module** (ADC) | Turns a voltage into a number for the Pi | `VDD GND SCL SDA ADDR ALRT A0 A1 A2 A3` |
| **MCP6002** (op-amp) | Turns the photodiode's tiny current into a voltage | A black 8-leg chip; a notch or dot marks the pin 1 end |
| **BPW34** (photodiode) | Turns light into a tiny current | A small flat square with two legs; find which leg is which with a multimeter (Step 3) |
| **Green LED** | Lights the diamond | Long leg = + (anode). Flat edge on the rim = − (cathode). |
| **Resistors** | Limit current / set gain | Coloured stripes (table below) |
| **Capacitors** | Smooth power / limit noise | A printed number code (table below) |
| **RG316 pigtail** | Feeds the antenna loop | SMA plug at one end; coax then red/black wires at the other |
| **SMA jumper** | Synth to amp | SMA plug at both ends |
| **50 Ω terminator** | Caps the synth's unused output | A short gold plug with no cable |
| **Diamond** | The sensor | A clear 12.5 × 12.5 × 7 mm block with a tiny crystal inside |
| **Red gel** | Blocks green, passes red | A sheet of red plastic film |

### Reading resistors

Read the stripes from the end opposite the gold one. The first two stripes are digits; the third says how many zeros to add.

| Value | Stripes | Used for |
|---|---|---|
| 100 Ω | brown, black, brown | LED |
| 10 kΩ | brown, black, orange | Synth LE pull-down |
| 1 MΩ | brown, black, green | Op-amp, if 10 MΩ is too much |
| 10 MΩ | brown, black, blue | Op-amp feedback |

Colour codes are easy to misread. If you're not sure, measure it: set the multimeter to Ω (resistance) and touch the probes to the two legs.

### Reading capacitors

Small ceramic capacitors carry a number code. The first two digits are the value; the third is how many zeros to add; the unit is picofarads (pF).

| Value | Printed code |
|---|---|
| 10 pF | `100` or just `10` |
| 100 nF (= 100,000 pF) | `104` |

Neither kind has a + or − side; either way round works.

---

## 6. Tools and supplies

**Tools:**

* A multimeter with continuity (beep), resistance (Ω), DC volts and diode test. A cheap one is fine.
* A soldering iron and stand (temperature-controlled is best), rosin-core solder, and a wet sponge or brass wool.
* Wire strippers, flush cutters, tweezers.
* A craft knife, for the coax.

**Supplies, if you don't have them:**

* A Dupont jumper wire kit (M-M, M-F, F-F)
* An 830-point solderless breadboard
* A T-Cobbler breakout with 40-pin ribbon cable
* Heat-shrink tubing (assorted kit) and a lighter or heat gun
* Masking tape and a pen, for labelling the breadboard rails
* Small zip ties or Blu Tack, to hold things in place

---

## 7. Assembly

Do the steps in order. Each one ends with a check; don't move on until it passes.

### Step 1: Solder the header onto the ADS1115

**Skip this step if your module came pre-soldered** (pins already fixed in a straight row). The module's holes need pins so jumper wires can grip them.

1. Push the strip of header pins, **long side down**, into the breadboard, so the breadboard holds them straight.
2. Lay the ADS1115 on top, with its labelled holes over the short ends of the pins.
3. Heat one joint: touch the iron to both the pin and the pad for about 2 seconds, feed in a little solder, then remove the solder, then the iron. A good joint is a small shiny cone, not a ball.
4. Do the far-end pin next so the board can't tilt, then all the rest.
5. Pull the module out of the breadboard.

**Check:** set the multimeter to continuity. Touch neighbouring pins two at a time; none should beep. A beep means a solder bridge; reheat it and drag the extra solder away.

### Step 2: Set up the breadboard and T-Cobbler

1. Plug the T-Cobbler into the breadboard so it straddles the centre trench, at one end of the board.
2. Plug the ribbon cable into the T-Cobbler; the socket is keyed so it only fits one way.
3. **With the Pi unplugged**, plug the other end of the ribbon cable onto the Pi's 40 pins. The coloured stripe on the cable (usually red) goes to **pin 1**, the end away from the USB ports. Make sure all 40 pins are inside the socket, not offset by one row.
4. Use the breadboard's rails like this, and label them with tape:

```text
  top rails:     + = 3.3 V      − = GND
  bottom rails:  + = 5 V        − = GND
```

5. Jumper (M-M) from the cobbler's **3V3** to the top **+** rail.
6. Jumper from a cobbler **GND** to the top **−** rail.
7. Jumper from the cobbler's **5V** to the bottom **+** rail.
8. Jumper from a cobbler **GND** to the bottom **−** rail.

**Check (power on):** plug in the Pi's power. Set the multimeter to DC volts and put the black probe on a − rail. The top + rail should read about 3.3 V, and the bottom + rail about 5 V. **Unplug again** before continuing. If anything is wrong, find out why before going on: a wrong rail at this stage would damage the parts you add next.

### Step 3: Build the photodiode amplifier

This is the most detailed step, so take it slowly.

**3a. Place the op-amp chip.** Find the notch or dot at one end of the MCP6002. Pins are numbered counter-clockwise looking from above, starting at the notch:

```text
              notch
            ┌───U───┐
    OUT A  1│●      │8  VDD (power)
    IN A−  2│       │7  OUT B
    IN A+  3│       │6  IN B−
    VSS    4│       │5  IN B+
   (ground) └───────┘
```

Press it into the breadboard straddling the trench, notch to the left, so it occupies columns 20 to 23 (any spot works; these column numbers are just for this guide):

```text
         col 20   21   22   23
  row e    1    2    3    4      ◄ chip pins 1 to 4 (above the trench)
         ════════ trench ════════
  row f    8    7    6    5      ◄ chip pins 8 to 5 (below the trench)
```

Now column 20 above the trench is pin 1, column 20 below it is pin 8, and so on. Each leg shares its column with four free holes.

**3b. Wire the chip.** Every connection lands in that leg's column:

| From | To | How |
|---|---|---|
| Pin 8 (col 20, below) | 3.3 V rail | Jumper wire |
| Pin 4 (col 23, above) | GND rail | Jumper wire |
| Pin 8 | Pin 4 | **100 nF** capacitor (`104`), as close to the chip as you can reach. It smooths the chip's power. |
| Pin 3 (col 22, above) | GND rail | Jumper wire |
| Pin 1 (col 20, above) | Pin 2 (col 21, above) | **10 MΩ** resistor (brown-black-blue) |
| Pin 1 | Pin 2 | **10 pF** capacitor (`100`), beside the resistor: both bridge the same two columns |
| Pin 5 (col 23, below) | GND rail | Jumper wire. This turns off the unused second half of the chip. |
| Pin 6 (col 22, below) | Pin 7 (col 21, below) | Short jumper wire. Also part of turning off the unused half. |

**3c. Identify the photodiode's legs.** Set the multimeter to diode test (the diode symbol, ─▶|─). Touch the probes to the two legs. One way round it reads about 0.3 to 0.6 V; the other way it reads OL (open). When it reads a voltage, **the red probe is on the anode and the black probe is on the cathode.** Mark the cathode with a dot of marker pen.

**3d. Connect the photodiode on wires.** The photodiode has to sit under the diamond, away from the breadboard, so connect it with two **M-F** jumpers: the female ends slide onto its legs, and the male ends go into the breadboard.

* **Cathode** (the marked leg) → op-amp **pin 2** column
* **Anode** → **GND** rail

Reversed, the circuit just reads 0 V and nothing is damaged.

**Check:** with the Pi powered, put the multimeter's black probe on GND and the red probe in the **pin 1** column. In normal room light it should read somewhere between 0.1 and 3 V. Cover the photodiode with your thumb and it should drop close to 0. If it's stuck near 3.3 V even when covered, swap the 10 MΩ for 1 MΩ (brown-black-green). If it's stuck at 0 in bright light, check that the photodiode isn't reversed and that pin 3 really goes to GND.

### Step 4: Add the ADS1115

1. Push the ADS1115 into the breadboard with its pins in row **e**, each pin in its own column, away from the op-amp. The module's body hangs out over the trench; that's fine, and it leaves holes a to d in each pin's column free for wires.
2. Wire it:

| ADS1115 pin | Goes to |
|---|---|
| VDD | 3.3 V rail. **Not** 5 V. |
| GND | GND rail |
| SCL | cobbler **SCL** (Pi pin 5) |
| SDA | cobbler **SDA** (Pi pin 3) |
| ADDR | GND rail. This sets its address to 0x48. |
| A0 | op-amp **pin 1** column |
| ALRT, A1, A2, A3 | nothing |

**Check:** the README's software check confirms the Pi can see it. Without software, all you can do here is re-check every wire against the table.

### Step 5: Wire the LED

The LED has to point at the diamond, so put it on wires too.

1. Slide two **F-M** jumpers onto the LED's legs.
2. **Long leg (anode, +)** → the **5 V** rail.
3. **Short leg (cathode, −; the flat edge of the rim)** → an empty breadboard column. From that column, put the **100 Ω resistor** (brown-black-brown) across to the **GND** rail.

The resistor limits the current to about 18 mA. Without it the LED burns out in a moment.

**Check:** power on. The LED lights. If it doesn't, it's probably reversed: swap its two wires (a reversed LED isn't damaged at 5 V through a resistor).

### Step 6: Wire the synthesizer board

**6a. Pull the P3 jumpers.** On the synth board, find the three small green caps on header **P3**. Pull them straight off with tweezers or fingernails and keep them in a bag; you can put them back to use the board over USB some day. They connect the board's own USB chip to the same control lines the Pi will drive, so they have to come off.

**6b. Check the P3 jumpers didn't do the board's job too.** Set the multimeter to continuity. Touch one probe to P2's **LE** pin and the other to the matching pin on the synth chip's side of P3; it should beep. Do the same for **CLK** and **DAT**. If a pin doesn't beep, stop: your board is wired differently from the one this guide was written for, so check its schematic before going on.

**6c. The LE pull-down resistor.** LE needs a 10 kΩ resistor to ground so it stays low while the Pi boots. Pick an empty breadboard column and call it the **LE column**. Put the **10 kΩ** resistor (brown-black-orange) from the LE column to the **GND** rail.

**6d. Wire header P2 to the Pi.** Use **M-F** jumpers: the female end goes onto the P2 pin; the male end goes into the breadboard.

| P2 pin | Goes to |
|---|---|
| **DAT** | cobbler **MOSI** (Pi pin 19) |
| **CLK** | cobbler **SCLK** (Pi pin 23) |
| **LE** | the **LE column**, then an M-M jumper from the LE column to cobbler **CE0** (Pi pin 24) |
| **CE** | cobbler **#25 / GPIO25** (Pi pin 22) |
| **LD** | cobbler **#24 / GPIO24** (Pi pin 18) |
| **GD** (either one) | **GND** rail |
| **3V3, MUX, PDR** | **nothing**. Leave them bare. |

**6e. Power.** Plug the barrel end of the board's USB-to-barrel cable into the synth board, and the USB end into one of the Pi's USB ports.

**6f. Terminator.** Screw the **50 Ω terminator** onto **OUT−**, finger-tight plus 1/8 turn.

**Check:** power on. The synth board's power LED (if it has one) lights. Nothing gets warm. The README's software check then confirms it locks.

### Step 7: Connect the amplifier

1. **Power leads.** If the amp has pins, use two F-M jumpers. If it has pads or holes, solder about 15 cm of wire to each: red to **+ / VCC**, black to **− / GND**. Check the markings twice; reversing power can destroy this board.
2. **Red** → the **5 V** rail. **Black** → the **GND** rail.
3. **Coax.** Screw one end of the **15 cm SMA jumper** onto the synth's **OUT+**, and the other onto the amp's **IN**. Make sure it's IN and not OUT.

**Check:** before powering, use continuity to confirm that the amp's + and − are **not** connected to each other (no beep). Then power on: the amp may have a power LED; it shouldn't get more than slightly warm.

**Never run the amp with nothing on its OUT jack for long**, and never put the terminator on the amp. Its OUT is for the antenna only.

### Step 8: Make the antenna loop

You bought a pack of two; use one, and keep the other as a spare.

```text
  SMA plug ════════════ coax (57 cm) ═══════════[heat-shrink]──── red/black wires (19 cm)
                                              ▲
                                     cut about 1 cm on THIS side of the heat-shrink
```

1. **Cut** the coax about 1 cm before the black heat-shrink, on the coax side. Throw away the red/black end. Those loose wires are about twice the microwave wavelength and would radiate the signal everywhere except into the loop.
2. **Strip the outer jacket.** With the craft knife, score lightly around the jacket about 15 mm from the end, then slit along it to the score and peel it off. Don't cut into the braid underneath.
3. **Fold the braid back.** Push the woven braid back along the cable and twist it into a short tail, about 8 mm long.
4. **Strip the inner insulation.** You'll see white plastic (PTFE) around the centre wire. Remove about 7 mm with the strippers, exposing the centre conductor.
5. **Form the loop.** Bend the centre conductor round something about 2 to 3 mm across (a small drill bit or a jeweller's screwdriver) so it curls back towards the braid tail.
6. **Solder** the tip of the centre conductor to the braid tail. Keep the joint small.
7. Optionally, slide heat-shrink over the braid joint (not over the loop) and shrink it.

```text
         braid tail
            │
   coax ════╪══ ─╮
            └────╯ ◄ centre conductor bent into a 2 to 3 mm loop, tip soldered to the braid
```

**Check:** continuity between the SMA plug's centre pin and its outer shell should **beep**: the loop is a deliberate short. Then screw the pigtail onto the amp's **OUT**.

### Step 9: Mount the diamond

The diamond sits in its clear block. The crystal inside is tiny, and the whole point of this step is to get the light, the loop and the photodiode all close to it.

```text
  side view

                    loop, flat on top face
                      ─╮
               ┌──────────────┐
  green LED ►  │      ◆       │   ◄ diamond block (◆ = the crystal)
               │              │
               └──────────────┘
                ░░░░░░░░░░░░░░   ◄ square of red gel
                   [BPW34]       ◄ photodiode, centred under the crystal
```

1. **Find the crystal.** Look through the block in good light; Adámas also marked which face it's nearest. The crystal sits a few millimetres inside.
2. **Cut a square of red gel**, slightly bigger than the photodiode.
3. **Stack them:** photodiode face up, gel on top, block on top with the crystal centred over the photodiode. Hold the stack with a dab of Blu Tack or a strip of tape around the sides. (Epoxy is for later, once everything works.)
4. **Aim the LED** at the crystal through a **side** face, not the top, so its green light doesn't shine straight down into the photodiode. The red gel blocks most green, but not all.
5. **Lay the loop flat** on the face nearest the crystal, centred over it. Tape the coax down a few centimetres back so its weight doesn't drag the loop off.

**Check:** dim the room. Look at the block through a spare piece of red gel. With the LED on, the crystal should glow faintly red. If it doesn't, re-aim the LED.

### Step 10: The final once-over

With everything **unplugged**:

1. **No shorts on the power:** continuity between the 3.3 V rail and GND: no beep. Between the 5 V rail and GND: no beep. Between the 3.3 V and 5 V rails: no beep. (A brief beep that stops straight away can be the capacitors charging; a steady beep is a short.)
2. **Nothing 5 V goes to a 3.3 V part:** the ADS1115 VDD and op-amp pin 8 are on the 3.3 V rail.
3. **Synth:** P3 jumpers out; terminator on OUT−; 3V3, MUX and PDR bare.
4. **RF:** synth OUT+ → amp IN; amp OUT → loop.
5. **Every GND is on a GND rail, and both GND rails are joined through the cobbler.**

Then power up and move on to the README's software check.

---

## 8. Common mistakes

| Symptom | Likely cause |
|---|---|
| The Pi won't boot, or reboots | A short between 5 V and GND; or the ribbon cable is offset by one row on the Pi. |
| A part gets hot | Reversed power. Unplug at once. |
| LED dark | LED reversed; or its resistor is in the wrong column and doesn't reach GND. |
| Op-amp output stuck near 3.3 V | Too much light (swap 10 MΩ for 1 MΩ), or pin 3 not on GND. |
| Op-amp output stuck near 0 V | Photodiode reversed; or pin 8 isn't on 3.3 V. |
| The ADC isn't found | VDD/GND swapped; SDA/SCL swapped; ADDR not on GND. |
| Synth won't lock | Barrel cable not plugged in; P3 jumpers still on; DAT and CLK swapped; the 10 kΩ isn't in the LE column. |

---

## 9. Glossary

| Word | Meaning |
|---|---|
| **Anode / cathode** | The + and − legs of a diode or LED. Current flows anode to cathode. |
| **GND (ground)** | The common 0 V reference. Everything's GND has to be joined. |
| **Header** | A row of pins (male) or sockets (female) on a 2.54 mm grid. |
| **Dupont / jumper wire** | A wire with a pin or socket on each end, for headers and breadboards. |
| **I2C** | A two-wire bus (SDA data, SCL clock) the Pi uses to talk to the ADS1115. |
| **SPI** | A bus (data, clock and a select line) the Pi uses to program the synth. |
| **GPIO** | A general-purpose input/output pin on the Pi. |
| **Pull-down resistor** | A resistor to GND that holds a line at 0 V when nothing is driving it. |
| **Op-amp** | A chip that amplifies; here it turns a nanoamp current into volts. |
| **ADC** | Analog-to-digital converter: turns a voltage into a number. |
| **Coax** | Cable with a centre wire inside a shield, for radio frequencies. |
| **SMA** | Small threaded connector for coax. |
| **Terminator** | A plug containing a 50 Ω resistor, which soaks up signal from an unused output. |
| **Lock / LD** | The synth's "I'm on frequency" signal. |
| **dBm** | Radio power on a log scale: 0 dBm = 1 mW, +20 dBm = 100 mW. |
