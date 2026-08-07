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
about a millimetre, and matches the AM90's plastic housing, it marks the
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
#
# Rev 1.5's outline was meant to be symmetric about X = 68.3 -- the axis the apex
# arc and U1, USB1 and CARD1 all sit on -- and wasn't. The apex was centred but
# the base was not, which left the left side 1.95 mm longer than the right and
# the two base angles 2.03 degrees apart, on a board 107 mm wide. Visible.
#
# Rebuilt symmetric, using the average of each mismatched pair so neither side
# simply won: fillet-centre half-offset 53.635, base levelled at Y 20.5655,
# fillet radius 4.8465, apex half-span 10.287. The two diagonals are then
# constructed as true tangents from the apex endpoints to the fillet circles,
# which also removes a 2.4 degree kink where rev 1.5's left diagonal met the
# apex arc. Both sides now 70.175 mm at 48.007 degrees.
AX = 68.3                # axis of symmetry; everything below is mirrored on it
P1 = (14.665, 20.5655)   # base, left end   (below the left fillet centre)
P2 = (11.063, 28.6545)   # left diagonal, tangent to the left fillet
P3 = (58.013, 80.810)    # apex arc, left end
P4 = (78.587, 80.810)    # apex arc, right end
P5 = (125.537, 28.6545)  # right diagonal, tangent to the right fillet
P6 = (121.935, 20.5655)  # base, right end

ARCS = [
    (P1, P2, (14.665, 25.412), "cw"),     # bottom-left fillet,  r 4.8465
    (P4, P3, (68.300, 72.000), "ccw"),    # apex,                r 13.544
    (P6, P5, (121.935, 25.412), "ccw"),   # bottom-right fillet, r 4.8465
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
    "USB1": (68.250, 25.146, 0),      # centred on the board axis
    "CARD1": (67.999, 59.099, 180),   # raised from rev 1.5 by hand
    "U1": (68.285, 38.000, 270),
}

# U1 sits at 270 degrees so its pin rows run HORIZONTALLY rather than as
# vertical columns:  pins 1-8 (almost all SD) face CARD1 above, pins 9-16 (USB
# and power) face USB1 below.
#
# That orientation is what makes the board route. Six of the seven signals leave
# the socket in the same left-to-right order they arrive at U1, so straight
# diagonals between them cannot cross. Only VCARD is out of order.
#
#   top row    y 79.375:  8 VCARD | 7 D2 | 6 D3 | 5 CMD | 4 CLK | 3 D0 | 2 D1 | 1 GND
#   bottom row y 84.625:  9 VDD | 10 +5V | 11 GPIO | 12 LED | 13 VDDA | 14 GND | 15 DP | 16 DM
#
# x is chosen so U1's signal span centres on CARD1's (88.285 in KiCad frame).
#
# Note KiCad's rotation matrix is [[cos,sin],[-sin,cos]] -- opposite handedness
# to the standard form. At 0 and 180 the sine term vanishes, so a wrong
# transform still validates; 90 and 270 are where it bites.
PLACE = {
    # HF decoupling under U1's bottom row, pad 1 upward at 270, clear of its
    # courtyard (which reaches y 85.7 in KiCad frame)
    "C5": (65.2, 32.4, 270),   # VDD  -> pin 9
    "C4": (67.0, 32.4, 270),   # +5V  -> pin 10
    "C6": (68.8, 32.4, 270),   # VDDA -> pin 13, the USB PHY rail
    # bulk one row further out
    "C2": (63.4, 29.2, 270),
    "C1": (66.1, 29.2, 270),
    "C8": (68.8, 29.2, 270),
    # VCARD pair, out to the right clear of CARD1's courtyard
    "C7": (80.0, 43.5, 270),
    "C3": (80.0, 39.5, 270),
    # LED chain along the base
    "R1": (36.675, 26.0, 0),
    "LED1": (16.712, 26.0, 0),
}
PLACE.update(FIXED)



STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (thickness 0.1855) (material "FR4") (epsilon_r 4.74) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 2" (type "core") (thickness 1.03) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 3" (type "prepreg") (thickness 0.1855) (material "FR4") (epsilon_r 4.74) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)
"""

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
    # KiCad stores pad angles ABSOLUTELY, with the footprint's rotation baked
    # in. Rotating a footprint without also stamping the angle onto every pad
    # moves the pad positions but leaves the pad shapes unrotated -- which at 90
    # or 270 degrees lays 1.65 mm pads across a 0.635 mm pitch and shorts the
    # part to itself. Invisible at 0/180, where a rectangle maps onto itself.
    if rot:
        body = re.sub(r'(\(pad "[^"]*"[^\n]*\n\s*)\(at ([-\d.]+) ([-\d.]+)\)',
                      lambda m: f'{m.group(1)}(at {m.group(2)} {m.group(3)} {rot:g})',
                      body)
    # A .kicad_mod's Value field holds the *footprint* name. On the board it has
    # to hold the component value, or every part is labelled C_0805_2012Metric
    # and the fab BOM is meaningless.
    body = re.sub(r'\(property "Value" "[^"]*"',
                  f'(property "Value" "{value}"', body, count=1)

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
           f'\t(setup\n\t\t(pad_to_mask_clearance 0)\n'
           f'\t\t(allow_soldermask_bridges_in_footprints no)\n' + STACKUP + '\t)\n'
           + nets
           + fps
           + edge_cuts()
           + "\t(embedded_fonts no)\n)\n")
    open(os.path.join(HW, "sd-net.kicad_pcb"), "w").write(pcb)
    print(f"wrote {len(PARTS)} footprints, {len(netnames)} nets, "
          f"{len(LINES)} lines + {len(ARCS)} arcs of Edge.Cuts")


if __name__ == "__main__":
    main()
