#!/usr/bin/env python3
"""Build the rev 2.0 fabrication package.

produces everything PCBWay needs to quote and build the board, in the shape
they expect it: **Gerbers and drill files zipped together**, with the BOM and
pick-and-place alongside as loose CSVs.

    ./tools/gen_fab.py                      # -> fab/v2.0-kicad/
    ./tools/gen_fab.py EXTRA_DIR ...        # also copy the package to EXTRA_DIR
    ./tools/gen_fab.py --pcbway             # -> fab/v2.0-pcbway/ only

`--pcbway` builds the vendor variant and touches nothing else, so the canonical
package can sit untouched while an order is in audit. See
`fab/v2.0-pcbway/README.md` for why that folder exists.

Gerber conventions chosen deliberately:
  * protel extensions (.GTL/.GBL/...) rather than .gbr. Every fab reads both;
    Protel is what PCBWay's own documentation shows.
  * x2 attributes left ON. They carry net and pad function metadata, which is
    what lets a fab's DFM tooling tell a via from a pad. The PCBWay variant
    turns them off, see build_pcbway().
  * soldermask subtracted from silkscreen, so legend never prints onto bare
    copper.
  * absolute origin for both Gerbers and drill, so the two always agree.
  * PTH and NPTH in separate files > board has NPTH that matters (the
    connector locating pegs), and merging them invites a fab to plate holes
    that must not be plated.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, "hardware", "sd-net.kicad_pcb")
SCH = os.path.join(HERE, "hardware", "sd-net.kicad_sch")
OUT = os.path.join(HERE, "fab", "v2.0-kicad")
PCBWAY_OUT = os.path.join(HERE, "fab", "v2.0-pcbway")
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

# Gerber X2 attribute commands. Stripping these leaves plain RS-274X: the
# image data is untouched and the same metadata survives as G04 comments.
X2_CMD = re.compile(r"^%T[FAOD]")

LAYERS = ("F.Cu,In1.Cu,In2.Cu,B.Cu,"
          "F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts")

BOM_FIELDS = "Reference,Value,Footprint,MPN,Manufacturer,LCSC,${QUANTITY}"
BOM_LABELS = "Designator,Value,Footprint,MPN,Manufacturer,LCSC Part #,Quantity"


README = """# sd - net 2.0, fabrication package

open-source USB SD card reader. CERN-OHL-S-2.0.
Repository: https://github.com/1phonetucked-tech/sd-net-2.0

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

**2, One through-hole part, and we do want it populated.** `USB1` is an AM90
right-angle USB-A **male plug**, 6 joints. It falls outside standard SMT
assembly, so please add the hand-soldering as a line item and quote it, rather
than shipping the plug loose. Every board should arrive with `USB1` fitted.
Everything else is SMT.

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
CERN-OHL-S-2.0. Happy to credit PCBWay wherever the project is published.
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


PCBWAY_README = """# sd - net 2.0, PCBWay variant

Vendor-specific build of the same board. **Nothing here is a different design.**
Every layer is byte-for-byte identical to `fab/v2.0-kicad/` once Gerber
attribute and comment lines are stripped, and the drill coordinates are the
same to the micron.

Anyone fabricating this board elsewhere should use **`fab/v2.0-kicad/`**, which
is the canonical package. This folder exists because PCBWay asked for two
specific things during the 2026-08 file audit.

## What is different, and why

**1, Gerbers are plain RS-274X, not X2.** PCBWay asked for RS-274X on
2026-08-05. Exported with `--no-x2`, which removes the `%TF` / `%TA` / `%TO` /
`%TD` extended commands. `--no-netlist` is deliberately **not** used: it is not
needed for RS-274X compliance and it would delete the net names. They survive
as ordinary `G04` comments, so netlist-based DFM still works.

**2, The `.gbrjob` file is omitted.** It is part of the X2 family and its
presence invites the same question the RS-274X conversion was meant to settle.

**3, The two `USB1` slots ship in alternative encodings.** They are the only
non-round feature on the board, and the only part of the package queried during
the audit. `sd-net-2.0-drill-alternates.zip` holds the same two slots written
two other ways, so a CAM system can take whichever slot convention it prefers.

## Files

| File | |
|---|---|
| `sd-net-2.0-gerber-rs274x.zip` | Gerbers + Excellon drill, RS-274X, no `.gbrjob` |
| `sd-net-2.0-drill-alternates.zip` | Slot alternatives, see below |

Inside `sd-net-2.0-drill-alternates.zip`:

| File | |
|---|---|
| `sd-net-PTH-M15M16.drl` | Plated drill with the slots as M15/M16 routed slots instead of `G85`. Identical to `sd-net-PTH.drl` in every other respect |
| `sd-net-PTH-drl.gbr` | Drill data plotted as a Gerber layer, so every hole is visible in an ordinary viewer |
| `sd-net-NPTH-drl.gbr` | The same, non-plated |

**Only one plated drill file may be loaded**, either `sd-net-PTH.drl` from the
main zip or `sd-net-PTH-M15M16.drl` from the alternates. Both describe the same
two slots, so loading both would double them.

The two `.gbr` files are for viewing and cross-checking only. They are not a
fabrication layer and must not be used as one.

## The slots

All three encodings describe one geometry: a 0.90 mm tool travelling 1.350 mm
along Y, giving a **0.90 x 2.25 mm plated slot**, long axis vertical.

| | Centre | Extent along Y |
|---|---|---|
| MH1 | X 94.155, Y -95.855 | -94.730 → -96.980 |
| MH2 | X 82.445, Y -95.855 | -94.730 → -96.980 |

Copper is an obround 1.70 x 3.05 mm flashed at the same two centres on all four
layers, mask opened to match, both on GND.

## Hole inventory

| File | Tool | Size | Count | |
|---|---|---|---|---|
| PTH | T1 | Ø0.300 mm | 20 | vias |
| PTH | T3 | Ø1.001 mm | 4 | `USB1` signal pins |
| PTH | T2 | 0.90 x 2.25 mm slot | 2 | `USB1` shell tabs |
| NPTH | T1 | Ø1.000 mm | 2 | `USB1` locating pegs |
| NPTH | T2 | Ø1.600 mm | 2 | SD socket pegs |

26 plated including the two slots, 4 non-plated, 30 total. **The four NPTH must
stay unplated** or neither connector will seat.

## Regenerating

    ./tools/gen_fab.py --pcbway

Builds this folder and touches nothing else. The quoting notes, BOM, CPL and
assembly drawing are not duplicated here: they live in `fab/v2.0-kicad/` and
are not vendor-specific.
"""


def _strip_x2(src, dst):
    """Copy a Gerber, dropping X2 attribute commands. Image data untouched."""
    with open(src) as f:
        kept = [ln for ln in f if not X2_CMD.match(ln)]
    with open(dst, "w") as f:
        f.writelines(kept)


def build_pcbway():
    """Vendor variant: RS-274X Gerbers, plus the slots in other encodings.

    Deliberately independent of build(). It never writes into fab/v2.0-kicad/,
    so this can be regenerated while an order is in audit without churning the
    package the fab is already holding.
    """
    os.makedirs(PCBWAY_OUT, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        main_dir = os.path.join(tmp, "main")
        alt_dir = os.path.join(tmp, "alt")
        os.makedirs(main_dir)
        os.makedirs(alt_dir)

        # RS-274X set. --no-netlist is deliberately absent: not required for
        # RS-274X, and it would throw away the net names that DFM relies on.
        run("pcb", "export", "gerbers", "--layers", LAYERS,
            "--subtract-soldermask", "--precision", "6", "--no-x2",
            "-o", main_dir + "/", PCB)
        run("pcb", "export", "drill", "--format", "excellon",
            "--drill-origin", "absolute", "--excellon-separate-th",
            "--excellon-zeros-format", "decimal", "--generate-map",
            "--map-format", "pdf", "-o", main_dir + "/", PCB)

        # The job file is X2 family; shipping it reopens the question the
        # RS-274X conversion exists to close.
        job = os.path.join(main_dir, "sd-net-job.gbrjob")
        if os.path.exists(job):
            os.remove(job)

        main_zip = os.path.join(PCBWAY_OUT, "sd-net-2.0-gerber-rs274x.zip")
        with zipfile.ZipFile(main_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(os.listdir(main_dir)):
                z.write(os.path.join(main_dir, f), f)

        # Slot alternatives. KiCad's flag names read backwards here: the
        # default "alternate" is G85, and "route" is what emits M15/M16.
        route_dir = os.path.join(tmp, "route")
        os.makedirs(route_dir)
        run("pcb", "export", "drill", "--format", "excellon",
            "--drill-origin", "absolute", "--excellon-separate-th",
            "--excellon-zeros-format", "decimal",
            "--excellon-oval-format", "route", "-o", route_dir + "/", PCB)
        # Renamed so it can never be mistaken for the file already reviewed.
        shutil.copy2(os.path.join(route_dir, "sd-net-PTH.drl"),
                     os.path.join(alt_dir, "sd-net-PTH-M15M16.drl"))

        # Drill plotted as Gerber, so the slots are visible in any viewer.
        gbr_dir = os.path.join(tmp, "gbr")
        os.makedirs(gbr_dir)
        run("pcb", "export", "drill", "--format", "gerber",
            "--drill-origin", "absolute", "-o", gbr_dir + "/", PCB)
        for name in ("sd-net-PTH-drl.gbr", "sd-net-NPTH-drl.gbr"):
            src = os.path.join(gbr_dir, name)
            if os.path.exists(src):
                _strip_x2(src, os.path.join(alt_dir, name))

        alt_zip = os.path.join(PCBWAY_OUT, "sd-net-2.0-drill-alternates.zip")
        with zipfile.ZipFile(alt_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(os.listdir(alt_dir)):
                z.write(os.path.join(alt_dir, f), f)

        n_main = len(zipfile.ZipFile(main_zip).namelist())
        n_alt = len(zipfile.ZipFile(alt_zip).namelist())

    open(os.path.join(PCBWAY_OUT, "README.md"), "w").write(PCBWAY_README)

    print(f"rs274x       : {n_main} files -> "
          f"{os.path.relpath(main_zip, HERE)}")
    print(f"alternates   : {n_alt} files -> "
          f"{os.path.relpath(alt_zip, HERE)}")


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


def listing(path):
    print(f"\npackage: {os.path.relpath(path, HERE)}/")
    for f in sorted(os.listdir(path)):
        p = os.path.join(path, f)
        if os.path.isfile(p):
            print(f"   {f:34s} {os.path.getsize(p)/1024:7.1f} KB")


def main():
    args = sys.argv[1:]

    # --pcbway builds the vendor variant alone, leaving fab/v2.0-kicad/ as it
    # is. That matters while an order is in audit: regenerating the canonical
    # package would restamp every timestamp for no change in the data.
    if "--pcbway" in args:
        build_pcbway()
        listing(PCBWAY_OUT)
        return

    os.makedirs(OUT, exist_ok=True)
    build()
    for extra in args:
        copy_to(extra)
    listing(OUT)


if __name__ == "__main__":
    main()
