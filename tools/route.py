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
GROUND_ONLY = False

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
# Six straight point-to-point diagonals. They leave CARD1 in the same
# left-to-right order they arrive at U1, so they provably cannot cross.
# Each signal fans diagonally to a common y, then drops STRAIGHT DOWN into its
# pad. A pure diagonal arrives at an angle and clips the neighbouring pad on the
# way in -- the pads are 0.4 mm wide on a 0.635 mm pitch, so there is no room to
# come in sideways. The verticals sit one pad pitch apart and cannot touch.
# Both ends need a straight exit: leaving the socket at an angle clips the
# neighbouring contact just as arriving at U1 at an angle clips the next pad.
# So each signal drops clear of the contact row, fans diagonally, then drops
# straight into its pad.
SD_EXIT_Y = 73.8
SD_FAN_Y = 77.6
SD = {
    "SD_DAT2": [(79.021, 71.876), (79.021, SD_EXIT_Y), (86.712, SD_FAN_Y), (86.712, 79.375)],
    "SD_DAT3": [(81.521, 71.876), (81.521, SD_EXIT_Y), (87.347, SD_FAN_Y), (87.347, 79.375)],
    "SD_CMD":  [(84.020, 71.876), (84.020, SD_EXIT_Y), (87.983, SD_FAN_Y), (87.983, 79.375)],
    "SD_CLK":  [(91.521, 71.876), (91.521, SD_EXIT_Y), (88.617, SD_FAN_Y), (88.617, 79.375)],
    "SD_DAT0": [(96.451, 71.876), (96.451, SD_EXIT_Y), (89.252, SD_FAN_Y), (89.252, 79.375)],
    "SD_DAT1": [(98.150, 71.876), (98.150, SD_EXIT_Y), (89.888, SD_FAN_Y), (89.888, 79.375)],
}

# VCARD is the one out-of-order signal: 4th from the left at the socket, leftmost
# at U1. It drops to B.Cu to cross under DAT2/DAT3/CMD.
VCARD_F1 = [(89.021, 71.876), (88.000, 75.025)]     # socket -> C7 pad 1
VCARD_F2 = [(88.400, 73.700), (88.000, 75.025)]     # stub to the via
VCARD_B  = [(88.400, 73.700), (84.800, 73.700), (84.800, 78.800)]
VCARD_F3 = [(84.800, 78.800), (86.078, 79.375)]     # via -> U1 pin 8
VCARD_F4 = [(83.950, 77.900), (84.800, 78.800)]     # C3 pad 1 -> via
VCARD_VIAS = [(88.400, 73.700), (84.800, 78.800)]

# --- USB pair ---------------------------------------------------------------
# DP and DM are adjacent on U1's bottom row, so the pair runs straight down at
# the native 0.634 mm pitch -- essentially the 0.646 mm solved for 90 ohm on
# PCBWay's stackup -- then fans to the plug. No vias, no layer change.
DIFF_W = 0.30
USB_DP_PATH = [(89.888, 84.625), (89.888, 90.500), (87.302, 93.853)]
USB_DM_PATH = [(90.522, 84.625), (90.522, 91.200), (89.301, 93.853)]

# --- short power hops -------------------------------------------------------
# The whole point of wrapping the caps around U1: these are now millimetres.
HOPS = {
    "VDD":  [[(84.500, 86.625), (86.078, 84.625)],      # C5 -> pin 9
             [(83.950, 84.500), (84.500, 86.625)]],     # C2 -> C5
    "+5V":  [[(86.500, 86.625), (86.712, 84.625)]],     # C4 -> pin 10
    "VDDA": [[(88.500, 86.625), (88.617, 84.625)]],     # C6 -> pin 13
    "LED_A": [[(36.788, 94.000), (46.000, 94.000), (46.000, 96.200),
               (56.825, 96.200), (56.825, 94.000)]],    # around R1's other pad
}

# --- long hauls on B.Cu -----------------------------------------------------
# Anything that has to cross the board goes underneath, where the layer is empty
# apart from VCARD's short hop. Each entry is (net, B.Cu path, vias, F.Cu stubs).
LONG = [
    ("+5V",  [(91.800, 93.853), (91.800, 89.000), (85.500, 89.000),
              (85.500, 81.600), (83.950, 81.600)],
             [(85.500, 87.000), (83.950, 81.600)],
             [[(85.500, 87.000), (86.500, 86.625)],       # via -> C4 pad 1
              [(83.950, 81.600), (83.950, 82.300)]]),     # via -> C1 pad 1
    ("VDD",  [(55.175, 90.800), (83.950, 90.800), (83.950, 85.500)],
             [(55.175, 90.800), (83.950, 85.500)],
             [[(55.175, 94.000), (55.175, 90.800)],       # R1 pad 1 -> via
              [(83.950, 85.500), (83.950, 84.500)]]),     # via -> C2 pad 1
    ("VDDA", [(85.200, 80.100), (86.800, 80.100), (86.800, 86.300),
              (87.500, 86.300)],
             [(85.200, 80.100), (87.500, 86.300)],
             [[(83.775, 80.100), (85.200, 80.100)],       # C8 pad 1 -> via
              [(87.500, 86.300), (88.500, 86.625)]]),     # via -> C6 pad 1
]


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
    out = path(USB_DP_PATH, "USB_DP", "F.Cu", DIFF_W)
    out += path(USB_DM_PATH, "USB_DM", "F.Cu", DIFF_W)
    for net, pts in SD.items():
        out += path(pts, net, "F.Cu", 0.2)
    for seg in (VCARD_F1, VCARD_F2, VCARD_F3, VCARD_F4):
        out += path(seg, "VCARD", "F.Cu")
    out += path(VCARD_B, "VCARD", "B.Cu")
    out += "".join(via(p, "VCARD") for p in VCARD_VIAS)
    for net, runs in HOPS.items():
        for r in runs:
            out += path(r, net, "F.Cu")
    for net, bot, vias, stubs in LONG:
        out += path(bot, net, "B.Cu")
        out += "".join(via(p, net) for p in vias)
        for st in stubs:
            out += path(st, net, "F.Cu")
    return out


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
    i = s.rstrip().rindex(")")
    s = s[:i] + build() + s[i:]
    open(PCB, "w").write(s)
    after = s.count("(segment") + s.count("(via") + s.count("(zone")
    print(f"copper elements: {before} -> {after}")


if __name__ == "__main__":
    main()
