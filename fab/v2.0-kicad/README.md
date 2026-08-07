# sd - net 2.0, fabrication package

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

They are in the drill file, not in the Gerber layers. `sd-net-PTH.drl` cuts them
as Excellon G85 routed slots on tool `T2C0.900`, each routing 1.350 mm along Y
from a centre of Y -95.855, at X 94.155 (MH1) and X 82.445 (MH2). The copper is
on all four layers: obround aperture 1.70 × 3.05 mm flashed at the same two
centres, mask opened to match, both on GND. They are the two oval pads either
side of the four round USB pins. `sd-net-PTH-drl_map.pdf` marks them as well. If
your CAM prefers M15/M16 routed slots or a separate rout layer, say so and we
will send a new drill file.

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
