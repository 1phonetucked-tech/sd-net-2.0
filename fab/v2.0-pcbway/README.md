# sd - net 2.0, PCBWay variant

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
