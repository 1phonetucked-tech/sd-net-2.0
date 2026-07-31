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
DIFF_WIDTH = 0.2

# Pitch is 0.45 mm (0.25 mm gap between 0.2 mm traces) so the pair clears the
# board's 0.2 mm default rule without needing a custom net class. The turns sit
# well clear of USB1 pin 4, whose ground pad needs room for its thermal spokes.
USB_DP_PATH = [(85.75, 85.81), (84.00, 85.81), (84.00, 91.30),
               (87.25, 91.30), (87.25, 93.85)]
USB_DM_PATH = [(85.75, 86.44), (84.45, 86.44), (84.45, 90.70),
               (89.25, 90.70), (89.25, 93.85)]


def length(pts):
    return sum(((pts[i + 1][0] - pts[i][0]) ** 2 +
                (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
               for i in range(len(pts) - 1))


def build():
    x0, y0, x1, y1 = BBOX
    rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out = "".join(zone(L, "GND", rect) for L in GND_LAYERS)
    out += "".join(via(p, "GND") for p in STITCH)
    out += path(USB_DP_PATH, "USB_DP", "F.Cu", DIFF_WIDTH)
    out += path(USB_DM_PATH, "USB_DM", "F.Cu", DIFF_WIDTH)
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
