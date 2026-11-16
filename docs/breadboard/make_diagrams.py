#!/usr/bin/env python3
"""Draws the breadboard wiring diagrams as SVG files in this folder.

    python3 docs/breadboard/make_diagrams.py

One overview plus one page per section. The layout lives in the PARTS,
WIRES and COMPONENTS tables below; change a column there and every page
follows.
"""
import os
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- geometry --
P = 18                      # hole pitch, px
NCOL = 63
X0 = 330                    # x of column 1
ROWS = "abcdefghij"
Y_TOP_PLUS = 150            # top rail, + (3.3 V)
Y_TOP_GND = Y_TOP_PLUS + P  # top rail, GND
Y_A = Y_TOP_GND + 2 * P     # row a
Y_F = Y_A + 5 * P + P       # row f (trench between e and f)
Y_BOT_GND = Y_F + 4 * P + 2 * P
Y_BOT_PLUS = Y_BOT_GND + P  # bottom rail, + (5 V)
BOARD_L, BOARD_R = X0 - 40, X0 + (NCOL - 1) * P + 40
BOARD_T, BOARD_B = Y_TOP_PLUS - 34, Y_BOT_PLUS + 34
W, H = 1620, 1000

COL = {"3v3": "#e8730c", "5v": "#d62728", "gnd": "#222222", "sig": "#1f77b4",
       "i2c": "#2ca02c", "spi": "#9467bd", "ctl": "#8c564b", "ana": "#e377c2",
       "short": "#bcbd22"}


def hx(c):
    return X0 + (c - 1) * P


def hy(r):
    i = ROWS.index(r)
    return (Y_A + i * P) if i < 5 else (Y_F + (i - 5) * P)


RAIL_Y = {"top+": Y_TOP_PLUS, "topG": Y_TOP_GND, "botG": Y_BOT_GND, "bot+": Y_BOT_PLUS}


def pt(spec):
    """(col, row) | ('rail', name, col) | ('off', x, y) -> (x, y)."""
    if spec[0] == "rail":
        return hx(spec[2]), RAIL_Y[spec[1]]
    if spec[0] == "off":
        return spec[1], spec[2]
    return hx(spec[0]), hy(spec[1])


# ----------------------------------------------------------- off-board boxes --
SYNTH_X, SYNTH_Y = 40, 300          # ADF4351 P2 header box (left)
SYNTH_W, SYNTH_H = 170, 175
SYN_PIN = {}                         # name -> (x, y)
_p2_top = ["LE", "CLK", "DAT", "GD", "3V3"]
_p2_bot = ["MUX", "LD", "PDR", "CE", "GD2"]
for i, n in enumerate(_p2_top):
    SYN_PIN[n] = (SYNTH_X + SYNTH_W - 18, SYNTH_Y + 50 + i * 24)
for i, n in enumerate(_p2_bot):
    SYN_PIN[n] = (SYNTH_X + 70, SYNTH_Y + 50 + i * 24)

LED_BOX = (hx(30) - 10, BOARD_B + 70)
PD_BOX = (hx(38) - 10, BOARD_B + 70)
AMP_BOX = (hx(48) - 10, BOARD_B + 70)
OFF = {
    "LED+": (LED_BOX[0] + 20, LED_BOX[1]), "LED-": (LED_BOX[0] + 70, LED_BOX[1]),
    "PDK": (PD_BOX[0] + 70, PD_BOX[1]), "PDA": (PD_BOX[0] + 20, PD_BOX[1]),
    "AMP+": (AMP_BOX[0] + 20, AMP_BOX[1]), "AMP-": (AMP_BOX[0] + 70, AMP_BOX[1]),
}

# ------------------------------------------------------------------- wires --
# (id, from, to, colour key, kind, label, section)
WIRES = [
    (1, (3, "a"), ("rail", "top+", 2), "3v3", "M-M", "Cobbler 3V3 → top + rail (3.3 V)", "power"),
    (2, (7, "a"), ("rail", "topG", 8), "gnd", "M-M", "Cobbler GND → top GND rail", "power"),
    (3, (3, "j"), ("rail", "bot+", 2), "5v", "M-M", "Cobbler 5V → bottom + rail (5 V)", "power"),
    (4, (5, "j"), ("rail", "botG", 6), "gnd", "M-M", "Cobbler GND → bottom GND rail", "power"),

    (5, (40, "a"), ("rail", "top+", 40), "3v3", "M-M", "Op-amp pin 8 (VDD) → 3.3 V", "opamp"),
    (6, (43, "a"), ("rail", "topG", 44), "gnd", "M-M", "Op-amp pin 5 → GND (parks unused half)", "opamp"),
    (7, (42, "c"), (41, "c"), "short", "M-M", "Op-amp pin 6 ↔ pin 7 (parks unused half)", "opamp"),
    (8, (42, "j"), ("rail", "botG", 42), "gnd", "M-M", "Op-amp pin 3 (IN A+) → GND", "opamp"),
    (9, (43, "j"), ("rail", "botG", 44), "gnd", "M-M", "Op-amp pin 4 (VSS) → GND", "opamp"),
    (10, ("off",) + OFF["PDK"], (41, "g"), "ana", "M-F", "Photodiode CATHODE → op-amp pin 2", "opamp"),
    (11, ("off",) + OFF["PDA"], ("rail", "botG", 37), "gnd", "M-F", "Photodiode ANODE → GND", "opamp"),

    (12, (50, "a"), ("rail", "top+", 50), "3v3", "M-M", "ADS1115 VDD → 3.3 V", "adc"),
    (13, (51, "a"), ("rail", "topG", 51), "gnd", "M-M", "ADS1115 GND → GND", "adc"),
    (14, (5, "a"), (52, "b"), "i2c", "M-M", "Cobbler SCL → ADS1115 SCL", "adc"),
    (15, (4, "b"), (53, "c"), "i2c", "M-M", "Cobbler SDA → ADS1115 SDA", "adc"),
    (16, (54, "a"), ("rail", "topG", 55), "gnd", "M-M", "ADS1115 ADDR → GND (address 0x48)", "adc"),
    (17, (40, "g"), (56, "d"), "ana", "M-M", "Op-amp pin 1 (OUT) → ADS1115 A0", "adc"),

    (18, (12, "a"), ("off",) + SYN_PIN["DAT"], "spi", "M-F", "Cobbler MOSI → synth DAT", "synth"),
    (19, (14, "b"), ("off",) + SYN_PIN["CLK"], "spi", "M-F", "Cobbler SCLK → synth CLK", "synth"),
    (20, (14, "j"), (28, "g"), "spi", "M-M", "Cobbler CE0 → LE junction (col 28)", "synth"),
    (21, (28, "i"), ("off",) + SYN_PIN["LE"], "spi", "M-F", "LE junction → synth LE", "synth"),
    (22, (13, "j"), ("off",) + SYN_PIN["CE"], "ctl", "M-F", "Cobbler #25 → synth CE", "synth"),
    (23, (11, "i"), ("off",) + SYN_PIN["LD"], "ctl", "M-F", "Cobbler #24 → synth LD", "synth"),
    (24, ("rail", "botG", 24), ("off",) + SYN_PIN["GD"], "gnd", "M-F", "GND rail → synth GD", "synth"),

    (25, ("off",) + OFF["LED+"], ("rail", "bot+", 30), "5v", "M-F", "LED ANODE (long leg) → 5 V", "light"),
    (26, ("off",) + OFF["LED-"], (33, "g"), "sig", "M-F", "LED CATHODE (short leg) → col 33", "light"),
    (27, ("off",) + OFF["AMP+"], ("rail", "bot+", 47), "5v", "M-F", "RF amp + → 5 V", "light"),
    (28, ("off",) + OFF["AMP-"], ("rail", "botG", 49), "gnd", "M-F", "RF amp − → GND", "light"),
]

# components plugged into the board: (id, kind, a, b, label, value, section)
COMPONENTS = [
    ("C1", "cap", (40, "b"), ("rail", "topG", 41), "100 nF", "code 104", "opamp"),
    ("R1", "res", (40, "h"), (41, "h"), "10 MΩ", "brown-black-blue", "opamp"),
    ("C2", "cap", (40, "i"), (41, "i"), "10 pF", "code 100", "opamp"),
    ("R2", "res", (28, "h"), ("rail", "botG", 29), "10 kΩ", "brown-black-orange", "synth"),
    ("R3", "res", (33, "h"), ("rail", "botG", 34), "100 Ω", "brown-black-brown", "light"),
]

COBBLER_TOP = ["3V3", "SDA", "SCL", "#4", "GND", "#17", "#27", "#22", "3V3", "MOSI",
               "MISO", "SCLK", "GND", "ID_SD", "#5", "#6", "#13", "#19", "#26", "GND"]
COBBLER_BOT = ["5V", "5V", "GND", "TXD", "RXD", "#18", "GND", "#23", "#24", "GND",
               "#25", "CE0", "CE1", "ID_SC", "GND", "#12", "GND", "#16", "#20", "#21"]
COBBLER_C0 = 3
OPAMP_C0 = 40      # notch on the left: pins 1-4 in row f, pins 8-5 in row e
ADS_C0 = 50
ADS_PINS = ["VDD", "GND", "SCL", "SDA", "ADDR", "ALRT", "A0", "A1", "A2", "A3"]

SECTIONS = {
    "overview": ("Full breadboard: every wire", None),
    "power": ("Page 1: power rails from the T-Cobbler", "power"),
    "opamp": ("Page 2: photodiode amplifier (MCP6002)", "opamp"),
    "adc": ("Page 3: ADS1115 analog-to-digital converter", "adc"),
    "synth": ("Page 4: ADF4351 synthesizer control lines", "synth"),
    "light": ("Page 5: LED and RF amplifier power", "light"),
}
ZOOM = {  # page -> (first column, last column) shown magnified
    "power": (1, 9), "opamp": (37, 45), "adc": (47, 60), "synth": (9, 30), "light": (27, 50),
}


# --------------------------------------------------------------- drawing ----
class SVG:
    def __init__(self, w, h):
        self.w, self.h, self.out = w, h, []

    def add(self, s):
        self.out.append(s)

    def text(self, x, y, s, size=12, anchor="start", weight="normal", fill="#111",
             rotate=None, family="Helvetica, Arial, sans-serif"):
        tr = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-family="{family}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" fill="{fill}"{tr}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill="none", stroke="#000", sw=1, rx=0, op=1):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')

    def line(self, x1, y1, x2, y2, stroke="#000", sw=1, dash=None, op=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{sw}" opacity="{op}"{d}/>')

    def circle(self, x, y, r, fill="#fff", stroke="#000", sw=1, op=1):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{sw}" opacity="{op}"/>')

    def path(self, d, stroke, sw, op=1, fill="none"):
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                 f'stroke-linecap="round" opacity="{op}"/>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">\n<rect width="100%" height="100%" fill="#ffffff"/>\n'
                + "\n".join(self.out) + "\n</svg>\n")


def draw_board(s):
    s.rect(BOARD_L, BOARD_T, BOARD_R - BOARD_L, BOARD_B - BOARD_T, fill="#f4f1ea",
           stroke="#bbb", sw=1.5, rx=10)
    # rails
    for y, col, lab in ((Y_TOP_PLUS, COL["3v3"], "+3.3 V"), (Y_TOP_GND, COL["gnd"], "GND"),
                        (Y_BOT_GND, COL["gnd"], "GND"), (Y_BOT_PLUS, COL["5v"], "+5 V")):
        s.line(hx(1) - 10, y + (-9 if y in (Y_TOP_PLUS, Y_BOT_GND) else 9),
               hx(NCOL) + 10, y + (-9 if y in (Y_TOP_PLUS, Y_BOT_GND) else 9), col, 2)
        s.text(BOARD_L + 4, y + 4, lab, 11, weight="bold", fill=col)
        s.text(BOARD_R - 4, y + 4, lab, 11, anchor="end", weight="bold", fill=col)
        for c in range(1, NCOL + 1):
            s.rect(hx(c) - 2.5, y - 2.5, 5, 5, fill="#555", stroke="none")
    # trench
    yt = (hy("e") + hy("f")) / 2
    s.rect(hx(1) - 10, yt - 4, hx(NCOL) - hx(1) + 20, 8, fill="#e2ddd1", stroke="none")
    # holes and labels
    for r in ROWS:
        y = hy(r)
        s.text(BOARD_L + 22, y + 4, r, 11, anchor="middle", fill="#777")
        s.text(BOARD_R - 22, y + 4, r, 11, anchor="middle", fill="#777")
        for c in range(1, NCOL + 1):
            s.rect(hx(c) - 2.5, y - 2.5, 5, 5, fill="#666", stroke="none")
    for c in [1] + list(range(5, NCOL + 1, 5)):
        s.text(hx(c), hy("a") - 10, str(c), 10, anchor="middle", fill="#777")
        s.text(hx(c), hy("j") + 18, str(c), 10, anchor="middle", fill="#777")


def draw_cobbler(s, op):
    x1, x2 = hx(COBBLER_C0) - 9, hx(COBBLER_C0 + 19) + 9
    s.rect(x1, hy("c") - 9, x2 - x1, hy("h") - hy("c") + 18, fill="#1b1b1b", stroke="#000",
           rx=4, op=0.92 * op)
    s.text((x1 + x2) / 2, hy("e") + (hy("f") - hy("e")) / 2 + 4, "T-COBBLER  (ribbon cable plugs in here)",
           10, anchor="middle", fill="#fff", weight="bold")
    for i, (t, b) in enumerate(zip(COBBLER_TOP, COBBLER_BOT)):
        c = COBBLER_C0 + i
        s.circle(hx(c), hy("e"), 3, fill="#d4af37", stroke="none", op=op)
        s.circle(hx(c), hy("f"), 3, fill="#d4af37", stroke="none", op=op)
        s.text(hx(c) + 3, hy("e") - 7, t, 8, rotate=-90, fill="#fff")
        s.text(hx(c) + 3, hy("f") + 7, b, 8, rotate=-90, anchor="end", fill="#fff")


def draw_opamp(s, op, big=False):
    x1, x2 = hx(OPAMP_C0) - 7, hx(OPAMP_C0 + 3) + 7
    s.rect(x1, hy("e") - 4, x2 - x1, hy("f") - hy("e") + 8, fill="#222", stroke="#000", rx=2, op=op)
    s.add(f'<path d="M {x1} {(hy("e")+hy("f"))/2 - 5} a 5 5 0 0 1 0 10" fill="#888" opacity="{op}"/>')
    s.text((x1 + x2) / 2, (hy("e") + hy("f")) / 2 + 4, "MCP6002", 8, anchor="middle", fill="#fff")
    for i in range(4):
        s.text(hx(OPAMP_C0 + i), hy("f") + 4 + 9, str(i + 1), 9, anchor="middle", weight="bold", fill="#c00")
        s.text(hx(OPAMP_C0 + i), hy("e") - 7, str(8 - i), 9, anchor="middle", weight="bold", fill="#c00")


def draw_ads(s, op):
    x1, x2 = hx(ADS_C0) - 9, hx(ADS_C0 + 9) + 9
    s.rect(x1, hy("e") - 8, x2 - x1, hy("i") - hy("e") + 14, fill="#1d4f91", stroke="#0e2f5a", rx=4, op=0.92 * op)
    s.text((x1 + x2) / 2, hy("h") + 2, "ADS1115 module", 9,
           anchor="middle", fill="#fff", weight="bold")
    for i, n in enumerate(ADS_PINS):
        s.circle(hx(ADS_C0 + i), hy("e"), 3, fill="#d4af37", stroke="none", op=op)
        s.text(hx(ADS_C0 + i) + 3, hy("e") + 8, n, 8, rotate=90, fill="#fff")


def draw_synth(s, op):
    cx = SYNTH_X + SYNTH_W / 2
    s.rect(SYNTH_X, SYNTH_Y, SYNTH_W, SYNTH_H, fill="#e9f2e4", stroke="#5a7d4b", sw=1.5, rx=6, op=op)
    s.text(cx, SYNTH_Y - 24, "ADF4351 board (off the breadboard)", 12, anchor="middle", weight="bold")
    s.text(cx, SYNTH_Y - 9, "its 10-pin header P2", 10, anchor="middle", fill="#444")
    s.text(cx, SYNTH_Y + 24, "P2: wire by these labels", 10, anchor="middle", weight="bold", fill="#5a7d4b")
    for n, (x, y) in SYN_PIN.items():
        unused = n in ("3V3", "MUX", "PDR", "GD2")
        s.rect(x - 5, y - 5, 10, 10, fill="#bbb" if unused else "#d4af37", stroke="#555", op=op)
        lab = "GD" if n == "GD2" else n
        s.text(x - 10, y + 4, lab, 11, anchor="end", fill="#aaa" if unused else "#111", weight="bold")
    s.text(cx, SYNTH_Y + SYNTH_H + 14, "grey pins: leave empty", 10, anchor="middle", fill="#777")


def draw_offboard(s, ops):
    def box(xy, title, lines, op):
        x, y = xy
        s.rect(x - 10, y, 100, 58, fill="#fdf6e3", stroke="#a08c5b", sw=1.2, rx=6, op=op)
        s.text(x + 40, y + 18, title, 11, anchor="middle", weight="bold")
        for i, ln in enumerate(lines):
            s.text(x + 40, y + 33 + i * 12, ln, 9, anchor="middle", fill="#444")
    box(LED_BOX, "Green LED", ["long leg = anode (+)", "short leg = cathode"], ops["light"])
    box(PD_BOX, "BPW34", ["photodiode, under", "the diamond"], ops["opamp"])
    box(AMP_BOX, "RF amplifier", ["+ and − power", "leads"], ops["light"])
    for k, (x, y) in OFF.items():
        s.circle(x, y, 4, fill="#d4af37", stroke="#555")


BADGE_T = 0.5


def wire_path(a, b):
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < 3 * P and abs(dy) < 3 * P:          # short hop: gentle arc
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 10 - abs(dx) * 0.15
        return f"M {x1} {y1} Q {mx} {my} {x2} {y2}", (mx, my + 5)
    # longer: leave vertically, arrive vertically (like a real jumper)
    up1 = -1 if y1 < (Y_A + Y_F) / 2 else 1
    up2 = -1 if y2 < (Y_A + Y_F) / 2 else 1
    lift = 40 + min(abs(dx), 600) * 0.12
    c1 = (x1 + dx * 0.15, y1 + up1 * lift)
    c2 = (x2 - dx * 0.15, y2 + up2 * lift)
    t = BADGE_T
    u = 1 - t
    mid = (u**3 * x1 + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * x2,
           u**3 * y1 + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * y2)
    return f"M {x1} {y1} C {c1[0]} {c1[1]} {c2[0]} {c2[1]} {x2} {y2}", mid


def wire_path_off(a, b):
    """Off-board run to the synth box on the left: out over the board edge."""
    (x1, y1), (x2, y2) = a, b
    top = y1 < (Y_A + Y_F) / 2
    edge_y = (BOARD_T - 30) if top else (BOARD_B + 30)
    d = (f"M {x1} {y1} C {x1} {edge_y} {x1} {edge_y} {x1 - 40} {edge_y} "
         f"L {BOARD_L - 20} {edge_y} C {x2 + 60} {edge_y} {x2 + 60} {y2} {x2} {y2}")
    return d, (x1 - 40 - (x1 - 40 - BOARD_L) * BADGE_T, edge_y)


def draw_component(s, comp, op):
    cid, kind, a, b, label, value, _ = comp
    (x1, y1), (x2, y2) = pt(a), pt(b)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    s.line(x1, y1, x2, y2, "#777", 1.6, op=op)
    if kind == "res":
        s.rect(mx - 9, my - 4, 18, 8, fill="#e8d3a9", stroke="#8a6d3b", rx=3, op=op)
    else:
        s.rect(mx - 6, my - 6, 12, 12, fill="#e4b54f" if label == "100 nF" else "#f0c070",
               stroke="#8a6d3b", rx=6, op=op)
    if op > 0.5:
        tx, ty = TAG_POS.get(cid, (mx + 12, my - 8))
        s.rect(tx - 2, ty - 11, 24, 14, fill="#fff", stroke="#8a6d3b", rx=3)
        s.text(tx + 10, ty, cid, 10, anchor="middle", weight="bold", fill="#5a3d0b")


BADGE_AT = {18: 0.25, 19: 0.6, 21: 0.75, 22: 0.75, 23: 0.15, 24: 0.4, 14: 0.4, 15: 0.6,
            20: 0.5, 17: 0.65}

TAG_POS = {"C1": (hx(38) - 6, hy("b") - 14), "R1": (hx(37) - 4, hy("h") + 4),
           "C2": (hx(37) - 4, hy("i") + 10), "R2": (hx(29) + 4, hy("i") + 6),
           "R3": (hx(34) + 4, hy("i") + 6)}


def badge(s, x, y, n, colour):
    s.circle(x, y, 9, fill="#fff", stroke=colour, sw=2)
    s.text(x, y + 4, str(n), 10, anchor="middle", weight="bold", fill=colour)


def page(name):
    title, focus = SECTIONS[name]
    s = SVG(W, H if focus is None else 1480)
    s.text(W / 2, 40, title, 22, anchor="middle", weight="bold")
    s.text(W / 2, 62, "830-point breadboard seen from above. Column numbers and row letters are printed "
           "on most breadboards; the cobbler's labels are what matter.", 12, anchor="middle", fill="#555")
    ops = {k: (1.0 if focus in (None, k) else 0.25) for k in ("power", "opamp", "adc", "synth", "light")}
    draw_board(s)
    draw_synth(s, ops["synth"] if focus else 1)
    draw_offboard(s, ops if focus else {k: 1 for k in ops})
    draw_cobbler(s, 1)
    draw_opamp(s, 1)
    draw_ads(s, 1)
    for comp in COMPONENTS:
        draw_component(s, comp, 1.0 if focus in (None, comp[6]) else 0.2)
    # dimmed wires first, highlighted on top
    order = sorted(WIRES, key=lambda w: (focus is None or w[6] == focus))
    for wid, a, b, ck, kind, lab, sec in order:
        on = focus is None or sec == focus
        pa, pb = pt(a), pt(b)
        to_synth = b[0] == "off" and pb[0] < BOARD_L
        global BADGE_T
        BADGE_T = BADGE_AT.get(wid, 0.5)
        d, mid = wire_path_off(pa, pb) if to_synth else wire_path(pa, pb)
        s.path(d, COL[ck], 3.2 if on else 2, op=1 if on else 0.18)
        if on:
            for x, y in (pa, pb):
                s.circle(x, y, 4, fill=COL[ck], stroke="#fff", sw=1.2)
            badge(s, mid[0], mid[1], wid, COL[ck])
    # legend
    rows = [w for w in WIRES if focus is None or w[6] == focus]
    comps = [c for c in COMPONENTS if focus is None or c[6] == focus]
    ly = BOARD_B + 150
    s.text(40, ly, "Wires" if rows else "", 14, weight="bold")
    colw = 400
    per_col = 10 if focus is None else 20
    for i, (wid, a, b, ck, kind, lab, sec) in enumerate(rows):
        x = 40 + (i // per_col) * colw
        y = ly + 22 + (i % per_col) * 19
        badge(s, x + 9, y - 4, wid, COL[ck])
        s.line(x + 24, y - 4, x + 44, y - 4, COL[ck], 4)
        s.text(x + 52, y, f"{lab}", 12)
        s.text(x + colw - 30, y, kind, 11, anchor="end", fill="#777")
    if comps:
        cx = 40 + ((len(rows) - 1) // per_col + 1) * colw if focus else 40 + 3 * colw + 20
        s.text(cx, ly, "Parts in the board", 14, weight="bold")
        for i, (cid, kind, a, b, label, value, sec) in enumerate(comps):
            y = ly + 22 + i * 19
            s.text(cx, y, f"{cid}  {label}", 12, weight="bold")
            s.text(cx + 80, y, value, 11, fill="#555")
    if focus in ZOOM:
        c1, c2 = ZOOM[focus]
        zx1, zx2 = hx(c1) - 14, hx(c2) + 14
        zy1, zy2 = Y_TOP_PLUS - 16, Y_BOT_PLUS + 16
        bx, by, bw, bh = 640, 620, 940, 810
        k = min(2.6, (bw - 120) / (zx2 - zx1), (bh - 60) / (zy2 - zy1))
        ox = bx + (bw - (zx2 - zx1) * k) / 2 - zx1 * k
        oy = by + 40 - zy1 * k
        body = s.out
        s.out = [f'<g id="main">'] + body + ["</g>"]
        s.add(f'<clipPath id="zc"><rect x="{zx1}" y="{zy1}" width="{zx2 - zx1}" height="{zy2 - zy1}"/></clipPath>')
        s.rect(bx, by, bw, bh, fill="#fbfbfb", stroke="#ccc", rx=8)
        s.text(bx + 14, by + 24, f"Zoomed in: columns {c1} to {c2}", 15, weight="bold")
        s.add(f'<g transform="translate({ox:.1f} {oy:.1f}) scale({k:.3f})" clip-path="url(#zc)">'
              f'<use href="#main"/></g>')
        lx = ox + zx1 * k - 14
        for r in ROWS:
            s.text(lx, oy + hy(r) * k + 5, r, 14, anchor="end", weight="bold", fill="#777")
        for y, lab, colr in ((Y_TOP_PLUS, "3.3 V", COL["3v3"]), (Y_TOP_GND, "GND", COL["gnd"]),
                             (Y_BOT_GND, "GND", COL["gnd"]), (Y_BOT_PLUS, "5 V", COL["5v"])):
            s.text(lx, oy + y * k + 5, lab, 13, anchor="end", weight="bold", fill=colr)
        for c in range(c1, c2 + 1):
            s.text(ox + hx(c) * k, oy + Y_TOP_PLUS * k - 22, str(c), 12, anchor="middle", fill="#777")
    s.text(40, (H if focus is None else 1480) - 22, "Wire types: M-M = male both ends; M-F = male into the breadboard, female onto a "
           "part's leg or header pin.  Colours are suggestions; any colour works electrically.",
           11, fill="#555")
    return s.svg()


def main():
    for name in SECTIONS:
        with open(os.path.join(HERE, f"{name}.svg"), "w") as fh:
            fh.write(page(name))
    print("wrote", ", ".join(f"{n}.svg" for n in SECTIONS))


if __name__ == "__main__":
    main()
