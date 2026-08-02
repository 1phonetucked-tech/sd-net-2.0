#!/usr/bin/env python3
"""Build the rev 2.0 fabrication package.

Produces everything PCBWay needs to quote and build the board, in the shape
they expect it: **Gerbers and drill files zipped together**, with the BOM and
pick-and-place alongside as loose CSVs.

    ./tools/gen_fab.py                      # -> fab/v2.0-kicad/
    ./tools/gen_fab.py EXTRA_DIR ...        # also copy the package to EXTRA_DIR

Gerber conventions chosen deliberately:
  * Protel extensions (.GTL/.GBL/...) rather than .gbr. Every fab reads both;
    Protel is what PCBWay's own documentation shows.
  * X2 attributes left ON. They carry net and pad function metadata, which is
    what lets a fab's DFM tooling tell a via from a pad.
  * Soldermask subtracted from silkscreen, so legend never prints onto bare
    copper.
  * Absolute origin for both Gerbers and drill, so the two always agree.
  * PTH and NPTH in separate files -- this board has NPTH that matters (the
    connector locating pegs), and merging them invites a fab to plate holes
    that must not be plated.
"""

import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, "hardware", "sd-net.kicad_pcb")
SCH = os.path.join(HERE, "hardware", "sd-net.kicad_sch")
OUT = os.path.join(HERE, "fab", "v2.0-kicad")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

LAYERS = ("F.Cu,In1.Cu,In2.Cu,B.Cu,"
          "F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts")

BOM_FIELDS = "Reference,Value,Footprint,MPN,Manufacturer,LCSC,${QUANTITY}"
BOM_LABELS = "Designator,Value,Footprint,MPN,Manufacturer,LCSC Part #,Quantity"


README = """# sd - net 2.0, fabrication package

Open-source USB SD card reader. **OSHWA UID US002797**, CERN-OHL-S-2.0.
Repository: https://github.com/1phonetucked-tech/sd-net

| | |
|---|---|
| Board size | **116.12 × 64.98 mm**, shaped outline, not a rectangle |
| Layers | 4 |
| Thickness | 1.6 mm |
| Copper | 1 oz (35 µm) outer and inner |
| Surface finish | **ENIG** |
| Soldermask | **black** |
| Silkscreen | **white** |
| Min track / clearance | 0.20 mm / 0.20 mm |
| Min via | 0.60 mm pad, 0.30 mm drill |
| Placements | **13**, across 7 line items |

## Files

| File | |
|---|---|
| `sd-net-2.0-gerber.zip` | Gerbers + Excellon drill, flat, Protel extensions |
| `sd-net-2.0-bom.csv` | BOM with MPN, manufacturer and LCSC part numbers |
| `sd-net-2.0-cpl.csv` | Pick-and-place |
| `sd-net-2.0-assembly.pdf` | Assembly drawing, legend, part outlines, designators |
| `sd-net-2.0-placement-reference.png` | Render of the finished board |
| `sd-net-2.0-schematic.pdf` | Schematic, for reference |

## Please note when quoting

**1, The outline is not rectangular.** An isosceles triangle with a 13.54 mm
radius arc across the apex and 4.85 mm fillets on the bottom two corners.
Please confirm any profiling or CNC routing charge is included.

**2, One through-hole part.** `USB1` is an AM90 right-angle USB-A **male
plug**, 6 joints, and it is not part of standard SMT assembly. Please quote the
hand-soldering separately. Everything else is SMT.

**3, Two plated slots.** `USB1` MH1/MH2 are **0.90 × 2.25 mm plated slots**,
not round holes. They take the plug's shell tabs and carry the mechanical load,
so please do not substitute round drills.

**4, Four holes must NOT be plated.** `sd-net-NPTH.drl` holds 2 × Ø1.00 mm
(USB plug locating pegs) and 2 × Ø1.60 mm (SD socket pegs). Plating them will
prevent both connectors from seating.

**5, Impedance, as a courtesy check.** `USB_DP` / `USB_DM` on F.Cu are
intended as a 90 Ω differential pair: 0.30 mm wide, 0.346 mm gap, referenced to
In1.Cu, solved against your standard 4-layer 1.6 mm stackup (7628 prepreg,
0.1855 mm after lamination, Dk 4.74). The pair is only ~10 mm long, so this is
not critical, but if your stackup wants a different width or gap, please say
and we will adjust. Note the pair threads a 1.475 mm corridor with 0.265 mm
either side, so widening it needs a layout change on our end.

**6, Please check the CPL rotations against your convention.** The
pick-and-place is KiCad's native output: millimetres, Y negative, rotations in
KiCad's frame. Orientation is the single largest risk on this board, `U1` is
an SSOP-16 where pin 1 must be right, and `LED1` is polarised. If your tooling
expects a different rotation origin, please tell us rather than assuming.

## Two requests

**Five boards first, not the full run.** This revision has never been
fabricated. We would rather find problems on five.

**A photo of the first assembled board before the rest are run.** Compare it
against `sd-net-2.0-placement-reference.png`. Assembly orientation is the
largest remaining risk in this design, and a photo catches it for free.

## About the project

Boards are **given away, not sold**, this is an open-hardware project under
CERN-OHL-S-2.0 with OSHWA certification UID **US002797**. Happy to credit
PCBWay wherever the project is published.
"""


def run(*args):
    r = subprocess.run([CLI] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(args[:3])}\n{r.stdout}\n{r.stderr}")


def build():
    gerber_dir = os.path.join(OUT, "gerber")
    shutil.rmtree(gerber_dir, ignore_errors=True)
    os.makedirs(gerber_dir, exist_ok=True)

    run("pcb", "export", "gerbers", "--layers", LAYERS,
        "--subtract-soldermask", "--precision", "6", "-o", gerber_dir + "/", PCB)
    run("pcb", "export", "drill", "--format", "excellon",
        "--drill-origin", "absolute", "--excellon-separate-th",
        "--excellon-zeros-format", "decimal", "--generate-map",
        "--map-format", "pdf", "-o", gerber_dir + "/", PCB)

    # Zip exactly the Gerber + drill set, flat -- fabs expect no nesting.
    zip_path = os.path.join(OUT, "sd-net-2.0-gerber.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gerber_dir)):
            z.write(os.path.join(gerber_dir, f), f)
    n = len(zipfile.ZipFile(zip_path).namelist())

    run("pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "--side", "both", "-o", os.path.join(OUT, "sd-net-2.0-cpl.csv"), PCB)
    run("sch", "export", "bom", "--fields", BOM_FIELDS, "--labels", BOM_LABELS,
        "--group-by", "Value,MPN,Footprint", "--sort-field", "Reference",
        "-o", os.path.join(OUT, "sd-net-2.0-bom.csv"), SCH)

    sch_pdf = os.path.join(HERE, "docs", "sd-net-schematic.pdf")
    if os.path.exists(sch_pdf):
        shutil.copy2(sch_pdf, os.path.join(OUT, "sd-net-2.0-schematic.pdf"))

    # Assembly drawing: legend, fab outlines and board edge, with designators.
    run("pcb", "export", "pdf", "--mode-single",
        "--layers", "F.SilkS,F.Fab,Edge.Cuts", "--black-and-white",
        "-o", os.path.join(OUT, "sd-net-2.0-assembly.pdf"), PCB)

    # A picture of the finished board. Not a formal deliverable, but it is the
    # cheapest way for an assembly house to check orientation at a glance --
    # U1's pin 1, the LED, which way the connectors face. Needs the models
    # from gen_3dmodels.py; skipped silently if they are gone.
    run("pcb", "render", "--side", "top", "--perspective",
        "--use-board-stackup-colors", "--zoom", "0.8", "--quality", "high",
        "-w", "1600", "-h", "1100", "--background", "opaque",
        "-o", os.path.join(OUT, "sd-net-2.0-placement-reference.png"), PCB)

    open(os.path.join(OUT, "README.md"), "w").write(README)

    print(f"gerber+drill : {n} files -> {os.path.relpath(zip_path, HERE)}")
    return zip_path


def copy_to(dest):
    os.makedirs(dest, exist_ok=True)
    for name in sorted(os.listdir(OUT)):
        src = os.path.join(OUT, name)
        dst = os.path.join(dest, name)
        if os.path.isdir(src):
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print(f"copied package -> {dest}")


def main():
    os.makedirs(OUT, exist_ok=True)
    build()
    for extra in sys.argv[1:]:
        copy_to(extra)
    print(f"\npackage: {os.path.relpath(OUT, HERE)}/")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if os.path.isfile(p):
            print(f"   {f:34s} {os.path.getsize(p)/1024:7.1f} KB")


if __name__ == "__main__":
    main()
