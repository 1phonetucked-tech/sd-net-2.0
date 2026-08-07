#!/usr/bin/env python3
"""Generate the three KiCad footprints this project needs and KiCad does not ship.

KiCad ships no footprint matching any of the three parts on this board. It does
carry six full-size SD sockets, but none match the SD-006M's contact count or
mounting; it has USB-A receptacles rather than a board-mounted male plug; and an
0804 LED is outside the metric chip series. All three are defined here.

Every dimension below is taken from the manufacturer's recommended land pattern:

  SD-006M         SOFNG, LCSC C125615, datasheet page 2 "CIRCUIT BOARD SIZE"
  USB-AM90        Shou Han, LCSC C404965, drawing A/0 dated 2018.07.10
  LED-12-215SYGC  Everlight 12-215SYGC/S530-E2/TR8, LCSC C131283, 0804 body

Conventions:

  Coordinates are millimetres in the footprint's own frame, Y positive downward.
  Pad 1 of the LED is the cathode, matching KiCad's Device:LED symbol.
  Slots are plated oval openings given as (width, height).

    ./tools/gen_footprints.py        # writes hardware/sd-net.pretty/

Verified geometry and the reasoning behind each correction: docs/LAND-PATTERNS.md
"""

import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRETTY = os.path.join(HERE, "hardware", "sd-net.pretty")
FP_VERSION = 20260206


def pad(name, x, y, w, h, shape="rect", drill=0.0, slot=None):
    return {"name": name, "x": x, "y": y, "w": w, "h": h,
            "shape": shape, "drill": drill, "slot": slot}


# --- SD-006M ----------------------------------------------------------------
# Eleven contacts in one row, two shell tabs, two non-plated locating pegs.
#
# The contact row sits 24.60 mm from the peg holes, which are 24.20 mm apart and
# define where the socket actually lands. Contact X positions are referenced to
# pad 9: #1 at 2.50, #2 at 5.00, CD at 6.43, #3 at 8.30, #4 at 10.00, then 2.50
# to #5 and to #6, 2.43 to #7, 1.70 to #8, and 3.25 to WP.
#
# Contact pads are drawn 2.1996 mm tall against a specified 2.00, and the shell
# tabs 1.999 x 2.3012 against 1.70 x 2.00. The extra length is solder fillet and
# is deliberate; DRC clearance is unaffected.
_SD_PEG_Y = 13.076
_SD_ROW_Y = round(_SD_PEG_Y - 24.60, 4)
_SD_W, _SD_H = 1.1989, 2.1996
# Listed in pad-number order; physical order along the row is
# WP, 8, 7, 6, 5, 4, 3, CD, 2, 1, 9.
_SD_X = {"1": 6.7793, "2": 4.2799, "3": 0.9804, "4": -0.7214, "5": -3.2207,
         "6": -5.7201, "7": -8.1509, "8": -9.8501, "9": 9.2786,
         "CD": 2.8486, "WP": -13.1014}

SD_006M = [pad(n, x, _SD_ROW_Y, _SD_W, _SD_H) for n, x in _SD_X.items()]
SD_006M += [
    # Shell tabs. Not mirror images of each other: the right tab sits further
    # out and 1.20 mm nearer the contact row than the left.
    pad("12", 14.582, 9.7739, 1.999, 2.3012),
    pad("13", -14.0005, 10.9753, 1.999, 2.3012),
]
SD_006M_NPTH = [(12.100, _SD_PEG_Y, 1.6), (-12.100, _SD_PEG_Y, 1.6)]

# --- USB-AM90 ---------------------------------------------------------------
# Four signal pins at 2.50 / 2.00 / 2.50, spanning 7.00 overall, in 1.00 mm
# holes. The locating pegs and the shell tabs share one line 2.00 mm from the
# pin row.
#
# The shell ends in two flat 0.86 mm tabs, not mounting posts. They belong in
# slots at +/-5.855, cut here 0.04 mm over the specified 0.86 x 2.20 to leave
# room for hole plating. These tabs are the board's only mechanical anchorage.
#
# Peg clearance is tight: a 0.85 mm peg in a 1.00 mm hole leaves 0.05-0.075 mm
# radially, so the 2.00 mm offset has to be exact or the plug will not seat.
_USB_ROW_Y = -1.0008
_USB_TAB_Y = 1.0008

USB_AM90 = [
    pad("1", 3.5001, _USB_ROW_Y, 1.6002, 1.6002, "circle", drill=1.0008),
    pad("2", 1.0008, _USB_ROW_Y, 1.6002, 1.6002, "circle", drill=1.0008),
    pad("3", -0.9982, _USB_ROW_Y, 1.6002, 1.6002, "circle", drill=1.0008),
    pad("4", -3.5001, _USB_ROW_Y, 1.6002, 1.6002, "circle", drill=1.0008),
    pad("MH1", 5.855, _USB_TAB_Y, 1.70, 3.05, drill=2.601, slot=(0.90, 2.25)),
    pad("MH2", -5.855, _USB_TAB_Y, 1.70, 3.05, drill=2.601, slot=(0.90, 2.25)),
]
USB_AM90_NPTH = [(2.250, _USB_TAB_Y, 1.0), (-2.250, _USB_TAB_Y, 1.0)]

# --- LED-12-215SYGC ---------------------------------------------------------
# An 0804 body, 2.0 x 1.0 mm, a size outside the metric chip series. The
# terminals sit 0.60-1.00 mm out from the centre, which a stock 0603 land does
# not reach. Pad 1 is the cathode and is placed on -x.
LED_12_215SYGC = [
    pad("2", 1.0503, 0.0, 0.8992, 0.8001),
    pad("1", -1.0503, 0.0, 0.8992, 0.8001),
]


def npth_sexp(x, y, d):
    return (f'\t(pad "" np_thru_hole circle\n'
            f'\t\t(at {x} {y})\n'
            f'\t\t(size {d} {d})\n'
            f'\t\t(drill {d})\n'
            f'\t\t(layers "F&B.Cu" "*.Mask")\n'
            f'\t)\n')


def pad_sexp(p):
    if p.get("slot"):
        sw, sh = p["slot"]
        return (f'\t(pad "{p["name"]}" thru_hole oval\n'
                f'\t\t(at {p["x"]} {p["y"]})\n'
                f'\t\t(size {p["w"]} {p["h"]})\n'
                f'\t\t(drill oval {sw} {sh})\n'
                f'\t\t(layers "*.Cu" "*.Mask")\n'
                f'\t)\n')
    if p["drill"] > 0:
        return (f'\t(pad "{p["name"]}" thru_hole {p["shape"]}\n'
                f'\t\t(at {p["x"]} {p["y"]})\n'
                f'\t\t(size {p["w"]} {p["h"]})\n'
                f'\t\t(drill {p["drill"]})\n'
                f'\t\t(layers "*.Cu" "*.Mask")\n'
                f'\t)\n')
    return (f'\t(pad "{p["name"]}" smd {p["shape"]}\n'
            f'\t\t(at {p["x"]} {p["y"]})\n'
            f'\t\t(size {p["w"]} {p["h"]})\n'
            f'\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n'
            f'\t)\n')


def courtyard(pads, margin=0.5):
    xs = [p["x"] - p["w"] / 2 for p in pads] + [p["x"] + p["w"] / 2 for p in pads]
    ys = [p["y"] - p["h"] / 2 for p in pads] + [p["y"] + p["h"] / 2 for p in pads]
    x0, x1 = min(xs) - margin, max(xs) + margin
    y0, y1 = min(ys) - margin, max(ys) + margin
    out = ""
    for layer, width in (("F.CrtYd", 0.05), ("F.Fab", 0.1)):
        out += (f'\t(fp_rect\n\t\t(start {x0:.3f} {y0:.3f})\n'
                f'\t\t(end {x1:.3f} {y1:.3f})\n'
                f'\t\t(stroke (width {width}) (type default))\n'
                f'\t\t(fill no)\n\t\t(layer "{layer}")\n\t)\n')
    return out, (x0, y0, x1, y1)


def cathode_silk(pads, margin=0.35, half=0.65, width=0.12):
    """Silkscreen bar outside pad 1, marking the cathode.

    Chip LEDs carry no legible marking once placed, so the board has to state
    polarity or assembly is guessing.
    """
    k = next(p for p in pads if p["name"] == "1")
    x = k["x"] + math.copysign(k["w"] / 2 + margin, k["x"])
    return (f'\t(fp_line\n\t\t(start {x:.4f} {-half})\n\t\t(end {x:.4f} {half})\n'
            f'\t\t(stroke (width {width}) (type solid))\n'
            f'\t\t(layer "F.SilkS")\n\t)\n')


def build(name, pads, descr, tags, holes=(), silk=None, attr=None):
    holes = list(holes)
    body, (x0, y0, x1, y1) = courtyard(
        pads + [{"x": hx, "y": hy, "w": hd, "h": hd} for hx, hy, hd in holes])
    if attr is None:
        attr = "through_hole" if any(p["drill"] > 0 for p in pads) else "smd"
    fp = (f'(footprint "{name}"\n'
          f'\t(version {FP_VERSION})\n'
          f'\t(generator "sd-net gen_footprints.py")\n'
          f'\t(layer "F.Cu")\n'
          f'\t(descr "{descr}")\n'
          f'\t(tags "{tags}")\n'
          f'\t(attr {attr})\n'
          f'\t(property "Reference" "REF**"\n\t\t(at 0 {y0 - 1:.3f} 0)\n'
          f'\t\t(layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t)\n'
          f'\t(property "Value" "{name}"\n\t\t(at 0 {y1 + 1:.3f} 0)\n'
          f'\t\t(layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t)\n'
          + body
          + (silk(pads) if silk else "")
          + "".join(pad_sexp(p) for p in pads)
          + "".join(npth_sexp(*h) for h in holes)
          + "\t(embedded_fonts no)\n"
          + f'\t(model "${{KIPRJMOD}}/sd-net.3dshapes/{name}.wrl"\n'
          + '\t\t(offset (xyz 0 0 0))\n'
          + '\t\t(scale (xyz 1 1 1))\n'
          + '\t\t(rotate (xyz 0 0 0))\n'
          + '\t)\n)\n')
    os.makedirs(PRETTY, exist_ok=True)
    open(os.path.join(PRETTY, name + ".kicad_mod"), "w").write(fp)
    print(f"{name}: {len(pads)} pads + {len(holes)} NPTH, "
          f"extent {x1 - x0:.2f} x {y1 - y0:.2f} mm")


def main():
    build("USB-AM90", USB_AM90,
          "USB 2.0 type-A male plug, right angle, through hole (LCSC C404965). "
          "Geometry from Shou Han drawing A/0. MH1/MH2 are plated slots for the "
          "shell tabs, not mounting posts.",
          "usb type-a plug right-angle tht", holes=USB_AM90_NPTH)
    build("SD-006M", SD_006M,
          "Full-size SD card socket, push-push, 11 contacts + 2 shell tabs "
          "(LCSC C125615). Geometry from the SOFNG datasheet land pattern.",
          "sd card socket push-push", holes=SD_006M_NPTH, attr="smd")
    build("LED-12-215SYGC", LED_12_215SYGC,
          "Everlight 12-215SYGC/S530-E2/TR8 yellow-green chip LED, 2.0 x 1.0 mm "
          "body (LCSC C131283). Pad 1 is the cathode. Do NOT substitute a stock "
          "0603 land: the terminals sit 0.60-1.00 mm out from the centre, which "
          "a 1.6 mm land does not reach properly.",
          "led chip yellow-green", silk=cathode_silk)

    tbl = ('(fp_lib_table\n  (version 7)\n'
           '  (lib (name "sd-net")(type "KiCad")'
           '(uri "${KIPRJMOD}/sd-net.pretty")(options "")'
           '(descr "sd - net project footprints"))\n)\n')
    open(os.path.join(HERE, "hardware", "fp-lib-table"), "w").write(tbl)


if __name__ == "__main__":
    main()
