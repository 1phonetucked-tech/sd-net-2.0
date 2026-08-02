#!/usr/bin/env python3
"""Derive KiCad footprints for SD-006M, USB-AM90 and LED1 from the rev 1.5 board.

KiCad has no stock footprint for any of these parts. Rather than draw them by
hand against a datasheet, take the pad geometry straight out of the Altium ASCII
export of the board that was actually fabricated.

The original reasoning was that those pads are known to match the physical
parts, because boards were built with them. That reasoning is weaker than it
looks: rev 1.5 never enumerated, so nothing about it was ever really proven, and
an audit against the manufacturers' own recommended land patterns found three
places where rev 1.5's library is wrong. Those are corrected here, via NPTH and
PAD_FIXES below, the rev 1.5 export is the starting point, not the authority.

Coordinate frames, since three conventions collide here:
  * Altium pad coordinates are absolute, in mils, Y-up.
  * A footprint is defined in the component's own frame, so the component's
    placement rotation has to be undone.
  * KiCad footprints are mm, Y-down.

    ./tools/gen_footprints.py        # writes hardware/sd-net.pretty/
"""

import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCBDOC = os.path.join(HERE, "fab", "v1.5-easyeda", "altium-export",
                      "sd - net 1.5.pcbdoc")
PRETTY = os.path.join(HERE, "hardware", "sd-net.pretty")

MIL = 39.3701  # mils per mm
FP_VERSION = 20260206


def mil2mm(v):
    return (float(v[:-3]) if v.endswith("mil") else float(v)) / MIL


def records(path):
    data = open(path, encoding="latin-1").read()
    for chunk in data.split("|RECORD="):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        fields = {}
        for p in parts[1:]:
            if "=" in p:
                k, _, v = p.partition("=")
                fields.setdefault(k, v)
        yield parts[0], fields


def extract(ref):
    """Return (rotation, [pad dicts]) in the component's local KiCad frame."""
    comps, pads = {}, []
    for kind, f in records(PCBDOC):
        if kind == "Component":
            comps[int(f["ID"])] = f
        elif kind == "Pad":
            pads.append(f)

    cid = next(i for i, f in comps.items() if f.get("SOURCEDESIGNATOR") == ref)
    c = comps[cid]
    cx, cy = mil2mm(c["X"]), mil2mm(c["Y"])
    rot = float(c.get("ROTATION", 0))
    # Undo the placement rotation to get the component's own frame.
    t = math.radians(-rot)
    cos_t, sin_t = math.cos(t), math.sin(t)

    out = []
    for p in pads:
        if int(p.get("COMPONENT", -1)) != cid:
            continue
        dx = mil2mm(p["X"]) - cx
        dy = mil2mm(p["Y"]) - cy
        lx = dx * cos_t - dy * sin_t
        ly = dx * sin_t + dy * cos_t
        out.append({
            "name": p["NAME"],
            "x": round(lx, 4),
            "y": round(-ly, 4),          # Altium Y-up -> KiCad Y-down
            "w": round(mil2mm(p["XSIZE"]), 4),
            "h": round(mil2mm(p["YSIZE"]), 4),
            "drill": round(mil2mm(p.get("HOLESIZE", "0mil")), 4),
            "shape": p.get("SHAPE", "RECTANGLE"),
            "layer": p.get("LAYER", "TOP"),
        })
    return rot, out


# Non-plated mounting/locating holes. EasyEDA exported these as board-level
# NPTH drills rather than component pads, so they do not appear in the Pad
# records and have to be added by hand. Coordinates are taken from
# Drill_NPTH_Through.DRL and expressed in each footprint's own frame:
#
#   USB1  1.0 mm @ (70.068, 23.971) and (65.568, 23.971) -- AM90 locating pegs
#         origin (67.818, 25.146), rotation 0
#   CARD1 1.6 mm @ (56.099, 67.686) and (80.299, 67.686) -- SD socket pegs
#         origin (68.199, 54.610), rotation 180
#
# Without these neither connector seats on the board.
#
# CORRECTION, USB-AM90 (Shou Han drawing A/0, 2018.07.10): the peg holes belong
# 2.00 mm from the pin row, on the same line as the shell tabs. Rev 1.5 drilled
# them at 2.175 -- pins at board Y 26.146, pegs at 23.971. The peg is 0.85 mm in
# a 1.00 mm hole, so there is 0.05-0.075 mm of radial clearance and a 0.175 mm
# error is an interference fit: the pegs bind and the plug does not seat flat.
# Corrected to y = 1.0008, matching MH1/MH2. Nothing routes to NPTH, so this
# costs no copper.
NPTH = {
    "USB-AM90": [(2.250, 1.0008, 1.0), (-2.250, 1.0008, 1.0)],
    "SD-006M": [(12.100, 13.076, 1.6), (-12.100, 13.076, 1.6)],
}

# Overrides applied to pads taken from the rev 1.5 export, keyed by footprint
# then pad name. Each entry may set x/y/w/h and "slot" (a plated oval opening,
# width x height) in place of the extracted round drill.
#
# USB-AM90 MH1/MH2: the AM90 has no mounting posts. Its shell ends in two flat
# tabs that the datasheet wants in 0.86 x 2.20 mm slots at +/-5.855. Rev 1.5
# put 2.601 mm round holes at +/-6.0 instead -- a tab rattling in a hole three
# times its width, with solder asked to bridge ~0.9 mm on each side. Those tabs
# are the only thing anchoring a board that cantilevers ~75 mm out of a USB
# port, so the joint is worth getting right. Slots are opened 0.04 mm over the
# recommended 0.86 x 2.20 to leave room for hole plating.

# SD-006M contacts belong 24.60 mm from the mounting pegs, which sit at
# y = +13.076 in this frame. Rev 1.5 has them at 24.05. The pegs locate the
# socket, so a 0.55 mm error puts the real part's tails ~78% onto the pads --
# marginal rather than fatal, which is why nothing ever caught it.
_SD_CONTACT_Y = round(13.076 - 24.60, 4)
_SD_CONTACTS = "1 2 3 4 5 6 7 8 9 CD WP".split()

PAD_FIXES = {
    # Nine of the eleven SD contact X positions already match the datasheet to
    # under 2 um. The two that do not are CD and WP -- the only two contacts
    # this design leaves unconnected, which is its own small piece of evidence
    # about how rev 1.5's library was drawn. Pad 12 (the right-hand shell tab)
    # was drawn as a mirror of pad 13; the real part is not symmetric there.
    # Pad 12's position has no printed dimension on the drawing and was
    # measured off it, so it is the least certain number here -- but our pad is
    # 2.00 mm wide against a 1.70 mm land, so at the corrected centre it covers
    # the specified land completely either way.
    "SD-006M": {
        **{n: {"y": _SD_CONTACT_Y} for n in _SD_CONTACTS},
        "CD": {"y": _SD_CONTACT_Y, "x": 2.8486},
        "WP": {"y": _SD_CONTACT_Y, "x": -13.1014},
        "12": {"x": 14.582},
    },
    "USB-AM90": {
        "MH1": {"x": 5.855, "w": 1.70, "h": 3.05, "slot": (0.90, 2.25)},
        "MH2": {"x": -5.855, "w": 1.70, "h": 3.05, "slot": (0.90, 2.25)},
    },
    # Rev 1.5 placed the two LED terminals 2.6 um apart in Y and 2.6 um apart
    # in |X|. That is EasyEDA placement noise on a symmetric chip part, not
    # geometry worth preserving, so square it up. Pad 1 is the cathode (rev 1.5
    # netlist: LED1.1 -> U1.12 open drain, LED1.2 -> R1), which matches KiCad's
    # Device:LED symbol. Cathode is put on -x to match how rev 2.0 already
    # placed and routed LED1.
    "LED-12-215SYGC": {
        "1": {"x": -1.0503, "y": 0.0},
        "2": {"x": 1.0503, "y": 0.0},
    },
}


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
        shape = "circle" if p["shape"] == "ROUND" else "rect"
        return (f'\t(pad "{p["name"]}" thru_hole {shape}\n'
                f'\t\t(at {p["x"]} {p["y"]})\n'
                f'\t\t(size {p["w"]} {p["h"]})\n'
                f'\t\t(drill {p["drill"]})\n'
                f'\t\t(layers "*.Cu" "*.Mask")\n'
                f'\t)\n')
    shape = "circle" if p["shape"] == "ROUND" else "rect"
    return (f'\t(pad "{p["name"]}" smd {shape}\n'
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
    """A silkscreen bar just outside pad 1, marking the cathode.

    Chip LEDs arrive on tape with no legible marking of their own once placed,
    so the board has to say which end is which or assembly is guessing.
    """
    k = next(p for p in pads if p["name"] == "1")
    x = k["x"] + math.copysign(k["w"] / 2 + margin, k["x"])
    return (f'\t(fp_line\n\t\t(start {x:.4f} {-half})\n\t\t(end {x:.4f} {half})\n'
            f'\t\t(stroke (width {width}) (type solid))\n'
            f'\t\t(layer "F.SilkS")\n\t)\n')


def build(name, ref, descr, tags, silk=None):
    rot, pads = extract(ref)
    for pad_name, fix in PAD_FIXES.get(name, {}).items():
        pad = next(p for p in pads if p["name"] == pad_name)
        pad.update(fix)
    holes = NPTH.get(name, [])
    # Mounting holes count toward the courtyard extent.
    body, (x0, y0, x1, y1) = courtyard(
        pads + [{"x": hx, "y": hy, "w": hd, "h": hd} for hx, hy, hd in holes])
    fp = (f'(footprint "{name}"\n'
          f'\t(version {FP_VERSION})\n'
          f'\t(generator "sd-net gen_footprints.py")\n'
          f'\t(layer "F.Cu")\n'
          f'\t(descr "{descr}")\n'
          f'\t(tags "{tags}")\n'
          f'\t(attr {"through_hole" if any(p["drill"] > 0 for p in pads) else "smd"})\n'
          f'\t(property "Reference" "REF**"\n\t\t(at 0 {y0 - 1:.3f} 0)\n'
          f'\t\t(layer "F.SilkS")\n\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t)\n'
          f'\t(property "Value" "{name}"\n\t\t(at 0 {y1 + 1:.3f} 0)\n'
          f'\t\t(layer "F.Fab")\n\t\t(effects (font (size 1 1) (thickness 0.15)))\n\t)\n'
          + body
          + (silk(pads) if silk else "")
          + "".join(pad_sexp(p) for p in pads)
          + "".join(npth_sexp(*h) for h in holes)
          + "\t(embedded_fonts no)\n"
          # KiCad ships no 3D model that fits any of these three parts, so
          # tools/gen_3dmodels.py builds them. Authored in KiCad's 0.1 inch
          # VRML convention, hence scale 1.
          + f'\t(model "${{KIPRJMOD}}/sd-net.3dshapes/{name}.wrl"\n'
          + '\t\t(offset (xyz 0 0 0))\n'
          + '\t\t(scale (xyz 1 1 1))\n'
          + '\t\t(rotate (xyz 0 0 0))\n'
          + '\t)\n)\n')
    os.makedirs(PRETTY, exist_ok=True)
    open(os.path.join(PRETTY, name + ".kicad_mod"), "w").write(fp)
    print(f"{name}: {len(pads)} pads + {len(holes)} NPTH, rev1.5 rotation {rot:g}, "
          f"extent {x1 - x0:.2f} x {y1 - y0:.2f} mm")
    return rot, pads


def main():
    build("USB-AM90", "USB1",
          "USB 2.0 type-A male plug, right angle, through hole (LCSC C404965). "
          "Pad geometry derived from the fabricated sd - net rev 1.5 board.",
          "usb type-a plug right-angle tht")
    build("SD-006M", "CARD1",
          "Full-size SD card socket, push-push, 11 contacts + 2 shell tabs "
          "(LCSC C125615). Pad geometry derived from the fabricated sd - net "
          "rev 1.5 board.",
          "sd card socket push-push")
    build("LED-12-215SYGC", "LED1",
          "Everlight 12-215SYGC/S530-E2/TR8 yellow-green chip LED, 2.0 x 1.0 mm "
          "body (LCSC C131283). Pad geometry derived from the fabricated sd - "
          "net rev 1.5 board. Pad 1 is the cathode. Do NOT substitute a stock "
          "0603 land: the terminals sit 0.60-1.00 mm out from the centre, which "
          "a 1.6 mm land does not reach properly.",
          "led chip yellow-green",
          silk=cathode_silk)

    tbl = ('(fp_lib_table\n  (version 7)\n'
           '  (lib (name "sd-net")(type "KiCad")'
           '(uri "${KIPRJMOD}/sd-net.pretty")(options "")'
           '(descr "sd - net project footprints"))\n)\n')
    open(os.path.join(HERE, "hardware", "fp-lib-table"), "w").write(tbl)


if __name__ == "__main__":
    main()
