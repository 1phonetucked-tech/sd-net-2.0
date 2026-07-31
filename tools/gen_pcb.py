#!/usr/bin/env python3
"""Bootstrap hardware/sd-net.kicad_pcb: outline, stackup, placement and nets.

One-time generator, like gen_schematic.py. It produces an unrouted board with
every footprint placed and every pad assigned to the right net, ready to route
in KiCad. Do not re-run it once you have started routing by hand.

The board outline is the triangle from rev 1.5, taken from
Gerber_BoardOutlineLayer.GKO: a flat base, two 4.846 mm corner fillets, two
diagonals rising inward, and a 13.544 mm-radius arc across the apex.

It deliberately EXCLUDES the 12.40 x 15.40 mm rectangle that also appears on
that Gerber layer. That rectangle is centred on USB1, overlaps the board edge by
about a millimetre, and matches the AM90's plastic housing — it marks the
connector body, not board material, and leaked into the outline layer as an
EasyEDA export artifact. Including it would produce an open, unroutable profile.

    ./tools/gen_pcb.py
"""

import math
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(HERE, "hardware")
PRETTY = os.path.join(HW, "sd-net.pretty")
SHARED = "/Applications/KiCad/KiCad.app/Contents/SharedSupport"

sys.path.insert(0, os.path.join(HERE, "tools"))
from gen_schematic import NETS, PARTS, LCSC  # noqa: E402

PCB_VERSION = 20260206

# Gerber frame (Y-up) -> KiCad frame (Y-down). Puts the board comfortably on
# an A3 sheet without negative coordinates.
OX, OY = 20.0, 120.0


def g2k(p):
    return (round(p[0] + OX, 4), round(OY - p[1], 4))


def uid():
    return str(uuid.uuid4())


# --- outline, in the Gerber frame -------------------------------------------
# Endpoints snapped where the Gerber's aperture rounding left sub-0.3 mm gaps.
P1 = (13.181, 20.612)    # base, left end
P2 = (9.801, 29.067)     # top of the left corner fillet
P3 = (58.012, 80.810)    # apex arc, left end
P4 = (78.586, 80.810)    # apex arc, right end
P5 = (123.655, 28.864)   # top of the right corner fillet
P6 = (120.451, 20.519)   # base, right end

ARCS = [
    (P1, P2, (13.034, 25.456), "cw"),     # bottom-left fillet,  r 4.846
    (P4, P3, (68.299, 72.000), "ccw"),    # apex,                r 13.544
    (P6, P5, (120.304, 25.363), "ccw"),   # bottom-right fillet, r 4.846
]
LINES = [(P2, P3), (P4, P5), (P1, P6)]    # diagonals + base


def arc_mid(start, end, centre, direction):
    """Point halfway along the arc, which is how KiCad stores arcs."""
    a0 = math.atan2(start[1] - centre[1], start[0] - centre[0])
    a1 = math.atan2(end[1] - centre[1], end[0] - centre[0])
    if direction == "ccw":
        while a1 <= a0:
            a1 += 2 * math.pi
    else:
        while a1 >= a0:
            a1 -= 2 * math.pi
    am = (a0 + a1) / 2
    r = math.hypot(start[0] - centre[0], start[1] - centre[1])
    return (centre[0] + r * math.cos(am), centre[1] + r * math.sin(am))


def edge_cuts():
    out = ""
    for a, b in LINES:
        (x1, y1), (x2, y2) = g2k(a), g2k(b)
        out += (f'\t(gr_line\n\t\t(start {x1} {y1})\n\t\t(end {x2} {y2})\n'
                f'\t\t(stroke (width 0.1) (type default))\n'
                f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid()}")\n\t)\n')
    for start, end, centre, direction in ARCS:
        (x1, y1) = g2k(start)
        (xm, ym) = g2k(arc_mid(start, end, centre, direction))
        (x2, y2) = g2k(end)
        out += (f'\t(gr_arc\n\t\t(start {x1} {y1})\n\t\t(mid {round(xm,4)} {round(ym,4)})\n'
                f'\t\t(end {x2} {y2})\n'
                f'\t\t(stroke (width 0.1) (type default))\n'
                f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid()}")\n\t)\n')
    return out


# --- placement --------------------------------------------------------------
# Held from rev 1.5 (docs/REV1.5-BASELINE.md) because they are mechanical fits.
FIXED = {
    "USB1": (67.818, 25.146, 0),
    "CARD1": (68.199, 54.610, 180),
    "U1": (68.326, 34.290, 180),
}

# U1 is SSOP-16, placed at 180 degrees, which MIRRORS which side each pin
# lands on -- easy to get backwards. Verified against the generated board:
#
#   pin 9  VDD   -> (85.701, 83.487)   |  pin 8 PMOS/VCARD -> (90.951, 83.487)
#   pin 10 +5V   -> (85.701, 84.122)   |
#   pin 13 VDDA  -> (85.701, 86.027)   |  CARD1 pin 4 VDD  -> (88.920, 76.365)
#
# So the three supply rails all exit U1's LEFT side and VCARD exits the RIGHT,
# toward the socket. Coordinates below are in the Gerber frame (see g2k).
#
# HF caps go in the inner column nearest the pins; bulk sits one column out.
PLACE = {
    # +5V / VDD / VDDA -- inner column of 100 nF, outer column of bulk,
    # both to the left of U1 where those pins actually are.
    "C5": (62.5, 38.0, 0),   # VDD  100nF, nearest pin 9
    "C4": (62.5, 35.6, 0),   # +5V  100nF, nearest pin 10
    "C6": (62.5, 33.2, 0),   # VDDA 100nF, nearest pin 13 -- the PHY rail
    "C2": (59.0, 38.0, 0),   # VDD  10uF
    "C1": (59.0, 35.6, 0),   # +5V  10uF
    "C8": (59.0, 33.2, 0),   # VDDA 100nF, second
    # VCARD -- in the corridor between U1 pin 8 and the socket's VDD contact
    "C7": (73.5, 41.0, 0),   # 100nF, nearest CARD1
    "C3": (73.5, 38.8, 0),   # 10uF bulk for card inrush
    # LED chain, out toward the lower left as in rev 1.5
    "R1": (37.719, 25.400, 0),
    "LED1": (17.653, 25.273, 0),
}
PLACE.update(FIXED)


def load_footprint(lib_id):
    lib, name = lib_id.split(":", 1)
    if lib == "sd-net":
        path = os.path.join(PRETTY, name + ".kicad_mod")
    else:
        path = os.path.join(SHARED, "footprints", lib + ".pretty", name + ".kicad_mod")
    return open(path).read()


def place(ref, lib_id, value, x, y, rot, netmap, netnames):
    """Emit a footprint instance with pads bound to nets."""
    src = load_footprint(lib_id)
    body = src[src.index("\n") + 1:src.rstrip().rindex(")")]
    # Strip fields the board file supplies itself.
    body = re.sub(r'\t\(version \d+\)\n', '', body)
    body = re.sub(r'\t\(generator[^\n]*\n', '', body)
    body = re.sub(r'\t\(generator_version[^\n]*\n', '', body)
    body = re.sub(r'\t\(embedded_fonts \w+\)\n', '', body)
    body = re.sub(r'\t\(layer "F\.Cu"\)\n', '', body, count=1)
    body = body.replace('"REF**"', f'"{ref}"')

    # Bind each pad to its net.
    def bind(m):
        padname = m.group(1)
        key = (ref, padname)
        net = netmap.get(key)
        if net is None:
            return m.group(0)
        return m.group(0).rstrip() + f'\n\t\t(net {netnames[net]} "{net}")'

    body = re.sub(r'\(pad "([^"]*)"[^\n]*\n(?:\t+\([^\n]*\)\n)+',
                  lambda m: _bind_pad(m, ref, netmap, netnames), body)

    lcsc = LCSC.get(ref, "")
    return (f'\t(footprint "{lib_id}"\n'
            f'\t\t(layer "F.Cu")\n'
            f'\t\t(uuid "{uid()}")\n'
            f'\t\t(at {x} {y}{"" if rot == 0 else " " + str(rot)})\n'
            f'\t\t(property "LCSC" "{lcsc}"\n\t\t\t(at 0 0 0)\n'
            f'\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n'
            f'\t\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t\t)\n'
            + re.sub(r"^\t", "\t\t", body, flags=re.M).rstrip("\n") + "\n"
            + "\t)\n")


def _bind_pad(m, ref, netmap, netnames):
    block = m.group(0)
    padname = m.group(1)
    net = netmap.get((ref, padname))
    if net is None:
        return block
    return block.rstrip("\n") + f'\n\t\t(net {netnames[net]} "{net}")\n'


def main():
    # net number 0 is the unconnected net and must exist
    netnames = {name: i + 1 for i, name in enumerate(sorted(NETS))}
    netmap = {}
    for name, members in NETS.items():
        for ref, pad in members:
            netmap[(ref, pad)] = name

    nets = '\t(net 0 "")\n' + "".join(
        f'\t(net {n} "{name}")\n' for name, n in sorted(netnames.items(), key=lambda kv: kv[1]))

    fps = ""
    for ref, (lib_id, value, fp, _sx, _sy) in PARTS.items():
        if ref not in PLACE:
            raise SystemExit(f"no placement for {ref}")
        gx, gy, rot = PLACE[ref]
        kx, ky = g2k((gx, gy))
        fps += place(ref, fp, value, kx, ky, rot, netmap, netnames)

    pcb = (f'(kicad_pcb\n\t(version {PCB_VERSION})\n'
           f'\t(generator "sd-net gen_pcb.py")\n'
           f'\t(generator_version "10.0")\n'
           f'\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)\n'
           f'\t(paper "A3")\n'
           f'\t(layers\n'
           f'\t\t(0 "F.Cu" signal)\n'
           f'\t\t(1 "In1.Cu" signal)\n'
           f'\t\t(2 "In2.Cu" signal)\n'
           f'\t\t(31 "B.Cu" signal)\n'
           f'\t\t(32 "B.Adhes" user "B.Adhesive")\n'
           f'\t\t(33 "F.Adhes" user "F.Adhesive")\n'
           f'\t\t(34 "B.Paste" user)\n'
           f'\t\t(35 "F.Paste" user)\n'
           f'\t\t(36 "B.SilkS" user "B.Silkscreen")\n'
           f'\t\t(37 "F.SilkS" user "F.Silkscreen")\n'
           f'\t\t(38 "B.Mask" user)\n'
           f'\t\t(39 "F.Mask" user)\n'
           f'\t\t(40 "Dwgs.User" user "User.Drawings")\n'
           f'\t\t(41 "Cmts.User" user "User.Comments")\n'
           f'\t\t(42 "Eco1.User" user "User.Eco1")\n'
           f'\t\t(43 "Eco2.User" user "User.Eco2")\n'
           f'\t\t(44 "Edge.Cuts" user)\n'
           f'\t\t(45 "Margin" user)\n'
           f'\t\t(46 "B.CrtYd" user "B.Courtyard")\n'
           f'\t\t(47 "F.CrtYd" user "F.Courtyard")\n'
           f'\t\t(48 "B.Fab" user)\n'
           f'\t\t(49 "F.Fab" user)\n'
           f'\t)\n'
           f'\t(setup\n\t\t(pad_to_mask_clearance 0)\n\t\t(allow_soldermask_bridges_in_footprints no)\n\t)\n'
           + nets
           + fps
           + edge_cuts()
           + "\t(embedded_fonts no)\n)\n")
    open(os.path.join(HW, "sd-net.kicad_pcb"), "w").write(pcb)
    print(f"wrote {len(PARTS)} footprints, {len(netnames)} nets, "
          f"{len(LINES)} lines + {len(ARCS)} arcs of Edge.Cuts")


if __name__ == "__main__":
    main()
