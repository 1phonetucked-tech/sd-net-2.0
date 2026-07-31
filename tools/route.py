#!/usr/bin/env python3
"""Add copper to hardware/sd-net.kicad_pcb: ground pours, then routed nets.

Unlike gen_pcb.py this is *additive* and idempotent-ish: it strips anything it
previously added (tagged by uuid prefix) and re-adds, so hand placement and hand
routing done in KiCad are preserved. It never touches footprints.

KiCad 10 note: the numeric net table is gone. Tracks, vias and zones all refer
to nets by name -- (net "GND") -- not by index.

    ./tools/route.py
"""

import os
import sys
import uuid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, "hardware", "sd-net.kicad_pcb")

# Everything this script generates carries this uuid prefix so it can be
# removed and regenerated without disturbing hand-drawn copper.
TAG = "5d4e7000"

# Signal routing is parked. The generated paths connect correctly -- they took
# unconnected items from 37 to 6 -- but escaping a 0.635 mm-pitch part by
# computing coordinates blind produced ~150 clearance and short violations from
# traces clipping neighbouring pads. That last mile wants interactive routing
# with push-and-shove. Ground pours and the stackup stay; flip this to False to
# get the signal paths back as a starting point.
GROUND_ONLY = True

# Board bounding box in KiCad coordinates; zones get clipped to Edge.Cuts.
BBOX = (29.0, 38.0, 144.5, 100.5)


def tagged_uuid():
    return TAG + "-" + str(uuid.uuid4())[9:]


def zone(layer, net, pts):
    xy = " ".join(f"(xy {x} {y})" for x, y in pts)
    return f"""\t(zone
\t\t(layers "{layer}")
\t\t(uuid "{tagged_uuid()}")
\t\t(net "{net}")
\t\t(hatch edge 0.508)
\t\t(connect_pads
\t\t\t(clearance 0.5)
\t\t)
\t\t(min_thickness 0.25)
\t\t(filled_areas_thickness no)
\t\t(fill
\t\t\t(thermal_gap 0.5)
\t\t\t(thermal_bridge_width 0.5)
\t\t)
\t\t(polygon
\t\t\t(pts {xy})
\t\t)
\t)
"""


def segment(a, b, net, layer, width=0.25):
    return f"""\t(segment
\t\t(start {round(a[0],4)} {round(a[1],4)})
\t\t(end {round(b[0],4)} {round(b[1],4)})
\t\t(width {width})
\t\t(layer "{layer}")
\t\t(net "{net}")
\t\t(uuid "{tagged_uuid()}")
\t)
"""


def via(p, net, size=0.6, drill=0.3, layers=('F.Cu', 'B.Cu')):
    return f"""\t(via
\t\t(at {round(p[0],4)} {round(p[1],4)})
\t\t(size {size})
\t\t(drill {drill})
\t\t(layers "{layers[0]}" "{layers[1]}")
\t\t(net "{net}")
\t\t(uuid "{tagged_uuid()}")
\t)
"""


def path(points, net, layer, width=0.25):
    return "".join(segment(points[i], points[i + 1], net, layer, width)
                   for i in range(len(points) - 1))


# --- ground -----------------------------------------------------------------
# Poured on all four layers. The F.Cu pour connects every surface-mount GND pad
# directly, which removes the need for a via at each one; In1/In2 give the USB
# pair a solid reference plane; stitching vias tie the layers together.
GND_LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

STITCH = [
    (78.0, 76.0), (98.0, 76.0), (78.0, 92.0), (98.0, 92.0),
    (68.0, 86.0), (108.0, 86.0), (88.0, 66.0), (88.0, 98.0),
    (60.0, 92.0), (116.0, 92.0),
]


# --- USB 2.0 differential pair ----------------------------------------------
# The only net where geometry genuinely matters. 480 Mbps wants a ~90 ohm
# coupled pair over unbroken reference plane, which In1.Cu now provides, so both
# legs stay on F.Cu the whole way -- no vias, no layer changes, no plane splits.
#
# The pair has to invert: at U1 the pins are stacked vertically 0.635 mm apart
# (DP above DM), while at USB1 they sit side by side 2.0 mm apart with DP to the
# LEFT of DM. Running DM on the outside of the turn gets them there without a
# crossing, and lands the lengths within 0.7 mm of each other.
# Geometry solved for PCBWay's standard 4-layer 1.6 mm stackup: F.Cu sits over
# 7628 prepreg, 0.1855 mm after lamination, Dk 4.74. By IPC-2141 microstrip that
# gives Z0 48.9 ohm at 0.30 mm width, and 0.346 mm edge-to-edge spacing lands
# Zdiff on 90.0 ohm.
#
# The first cut used 0.20 mm traces at 0.25 mm spacing, which computes to
# 105.9 ohm -- far off 90 and the kind of error that only shows up as marginal
# enumeration on a finished board.
#
# The pair threads the 1.475 mm corridor between C6's pad (right edge 83.450)
# and U1's pads (left edge 84.925). At 0.946 mm total width that leaves 0.265 mm
# either side, clear of the 0.2 mm rule but with nothing to spare -- do not
# widen further without moving C6.
DIFF_WIDTH = 0.30

# U1 at 90 degrees puts DP and DM adjacent on the bottom row at the native
# 0.635 mm pad pitch -- which is within a hundredth of the 0.646 mm solved for
# 90 ohm -- so the pair simply runs straight down before fanning to the plug.
USB_DP_PATH = [(89.8725, 84.625), (89.8725, 91.00), (87.25, 93.85)]
USB_DM_PATH = [(90.5075, 84.625), (90.5075, 91.50), (89.25, 93.85)]



# --- SD bus -----------------------------------------------------------------
# With U1 at 90 degrees the six SD signals leave CARD1 in the same left-to-right
# order they arrive at U1, so straight point-to-point diagonals provably cannot
# cross. Separation is widest at the socket and narrows to the 0.635 mm pad
# pitch at the chip, which is the tightest point and still clears.
SD = {
    "SD_DAT2": [(78.72, 71.88), (86.6975, 79.375)],
    "SD_DAT3": [(81.22, 71.88), (87.3325, 79.375)],
    "SD_CMD":  [(83.72, 71.88), (87.9675, 79.375)],
    "SD_CLK":  [(91.22, 71.88), (88.6025, 79.375)],
    "SD_DAT0": [(96.15, 71.88), (89.2375, 79.375)],
    "SD_DAT1": [(97.85, 71.88), (89.8725, 79.375)],
}

# VCARD is the one signal whose order does not match -- it starts 4th from the
# left at the socket and lands leftmost at U1, so it must cross DAT2/DAT3/CMD.
# It drops to B.Cu to do it, and picks up its two decoupling caps on the way.
VCARD_BOT = [(88.72, 73.20), (84.50, 73.20), (84.50, 80.60)]
VCARD_CAPS = [(88.72, 73.20), (100.0, 73.20), (100.0, 76.05)]
VCARD_VIAS = [(88.72, 73.20), (84.50, 80.60), (100.0, 73.725), (100.0, 76.05)]
VCARD_STUB_CARD = [(88.72, 71.88), (88.72, 73.20)]
VCARD_STUB_U1 = [(84.50, 80.60), (86.0625, 79.375)]

# --- power and LED ----------------------------------------------------------
# Each high-frequency cap now sits directly under the pin it serves, so these
# are millimetres rather than the 5 mm they were before the rotation.
SHORT = {
    "VDD":  [[(85.20, 86.225), (86.0625, 84.625)],          # C5.1 -> pin 9
             [(83.40, 89.25), (85.20, 86.225)]],            # C2.1 -> C5.1
    "+5V":  [[(87.00, 86.225), (86.6975, 84.625)],          # C4.1 -> pin 10
             [(86.10, 89.25), (85.60, 88.20), (85.60, 86.90),
              (87.00, 86.225)]],                            # C1.1 -> C4.1
    "VDDA": [[(88.80, 86.225), (88.6025, 84.625)],          # C6.1 -> pin 13
             [(88.80, 89.25), (88.80, 86.225)]],            # C8.1 -> C6.1
    "LED_A": [[(37.50, 94.00), (50.00, 94.00), (50.00, 96.20),
               (57.50, 96.20), (57.50, 94.00)]],                # around R1.1
}

# Long hauls go on B.Cu, which is otherwise empty.
LONG = [
    # +5V from the USB plug, under the differential pair, up beside C1
    ("+5V",   [(91.75, 93.85), (97.00, 93.85), (97.00, 98.00),
               (86.10, 98.00), (86.10, 91.60)], [(86.10, 91.60)], [(86.10, 91.60), (86.10, 89.25)]),
    # VDD out to R1 at the far left
    ("VDD",   [(55.85, 93.00), (81.50, 93.00), (81.50, 90.00)],
              [(55.85, 93.00), (81.50, 90.00)], [(81.50, 90.00), (83.40, 89.25)]),
    # LED cathode back from LED1 to pin 12
    ("LED_K", [(35.92, 91.00), (87.9675, 91.00), (87.9675, 87.20)],
              [(35.92, 91.00), (87.9675, 87.20)], [(87.9675, 87.20), (87.9675, 84.625)]),
]
LONG_STUBS = {
    "VDD_R1": [(55.85, 94.00), (55.85, 93.00)],
    "LED_K1": [(35.92, 94.00), (35.92, 91.00)],
}


def length(pts):
    return sum(((pts[i + 1][0] - pts[i][0]) ** 2 +
                (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
               for i in range(len(pts) - 1))


def build():
    x0, y0, x1, y1 = BBOX
    rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out = "".join(zone(L, "GND", rect) for L in GND_LAYERS)
    out += "".join(via(p, "GND") for p in STITCH)
    if not GROUND_ONLY:
        out += _signals()
    return out


def _signals():
    out = path(USB_DP_PATH, "USB_DP", "F.Cu", DIFF_WIDTH)
    out += path(USB_DM_PATH, "USB_DM", "F.Cu", DIFF_WIDTH)
    for net, pts in SD.items():
        out += path(pts, net, "F.Cu")
    out += path(VCARD_STUB_CARD, "VCARD", "F.Cu")
    out += path(VCARD_BOT, "VCARD", "B.Cu")
    out += path(VCARD_CAPS, "VCARD", "B.Cu")
    out += path(VCARD_STUB_U1, "VCARD", "F.Cu")
    out += "".join(via(p, "VCARD") for p in VCARD_VIAS)
    for net, runs in SHORT.items():
        for r in runs:
            out += path(r, net, "F.Cu")
    for net, bot, vias, top in LONG:
        out += path(bot, net, "B.Cu")
        out += path(top, net, "F.Cu")
        out += "".join(via(p, net) for p in vias)
    out += path(LONG_STUBS["VDD_R1"], "VDD", "F.Cu")
    out += path(LONG_STUBS["LED_K1"], "LED_K", "F.Cu")
    return out


# PCBWay standard 4-layer, 1.6 mm finished. Recorded on the board so KiCad's
# impedance tooling and any future recalculation use the real numbers rather
# than KiCad's generic defaults.
STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 1" (type "prepreg") (thickness 0.1855) (material "FR4") (epsilon_r 4.74) (loss_tangent 0.02))
\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 2" (type "core") (thickness 1.03) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "dielectric 3" (type "prepreg") (thickness 0.1855) (material "FR4") (epsilon_r 4.74) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)
"""


def ensure_stackup(s):
    if "(stackup" in s:
        return s
    i = s.index("\t(setup")
    j = s.index("\n", i)
    return s[:j + 1] + STACKUP + s[j + 1:]


def strip_previous(s):
    """Remove top-level elements whose uuid carries our tag."""
    keep, i, n = [], 0, len(s)
    while i < n:
        j = s.find("\n\t(", i)
        if j < 0:
            keep.append(s[i:])
            break
        keep.append(s[i:j + 1])
        # find the matching close paren for this top-level element
        d, instr, k = 0, False, j + 1
        while k < n:
            c = s[k]
            if c == '"':
                instr = not instr
            elif not instr:
                if c == "(":
                    d += 1
                elif c == ")":
                    d -= 1
                    if d == 0:
                        break
            k += 1
        blk = s[j + 1:k + 1]
        if f'"{TAG}-' not in blk:
            keep.append(blk)
        i = k + 1
    return "".join(keep)


def main():
    s = open(PCB).read()
    before = s.count("(segment") + s.count("(via") + s.count("(zone")
    s = strip_previous(s)
    s = ensure_stackup(s)
    i = s.rstrip().rindex(")")
    s = s[:i] + build() + s[i:]
    open(PCB, "w").write(s)
    after = s.count("(segment") + s.count("(via") + s.count("(zone")
    print(f"copper elements: {before} -> {after}")


if __name__ == "__main__":
    main()
