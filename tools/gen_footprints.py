#!/usr/bin/env python3
"""Derive KiCad footprints for SD-006M and USB-AM90 from the rev 1.5 board.

KiCad has no stock footprint for either part. Rather than draw them by hand
against a datasheet, take the pad geometry straight out of the Altium ASCII
export of the board that was actually fabricated — those pads are known to
match the physical parts, because boards were built with them.

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


def pad_sexp(p):
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


def build(name, ref, descr, tags):
    rot, pads = extract(ref)
    body, (x0, y0, x1, y1) = courtyard(pads)
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
          + "".join(pad_sexp(p) for p in pads)
          + "\t(embedded_fonts no)\n)\n")
    os.makedirs(PRETTY, exist_ok=True)
    open(os.path.join(PRETTY, name + ".kicad_mod"), "w").write(fp)
    print(f"{name}: {len(pads)} pads, rev1.5 rotation {rot:g}, "
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

    tbl = ('(fp_lib_table\n  (version 7)\n'
           '  (lib (name "sd-net")(type "KiCad")'
           '(uri "${KIPRJMOD}/sd-net.pretty")(options "")'
           '(descr "sd - net project footprints"))\n)\n')
    open(os.path.join(HERE, "hardware", "fp-lib-table"), "w").write(tbl)


if __name__ == "__main__":
    main()
