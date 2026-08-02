<img src="branding/oshwa_mark/oshw_gear_black.png" width="76" align="right" alt="Open source hardware">

# sd - net 2.0

A full-size USB SD card reader on a single chip. USB-A plug at one end, full-size
SD socket at the other, 13 placements across 7 line items in between.

[![OSHWA US002797](https://img.shields.io/badge/OSHWA-US002797-blue)](https://certification.oshwa.org/us002797.html)
[![CERN-OHL-S-2.0](https://img.shields.io/badge/license-CERN--OHL--S--2.0-green)](LICENSE)

| | |
|---|---|
| Controller | Genesys Logic GL823K, SSOP-16, LCSC C284879 |
| Board | 116.12 × 64.98 mm, 4 layers, 1.6 mm, ENIG |
| Finish | black soldermask, white legend |
| Placements | 13, of which 12 SMT and 1 through-hole |
| Interface | USB 2.0 high speed, SD 4-bit mode |
| Licence | CERN-OHL-S-2.0 |

Boards are given away, not sold.

## Specification

**Supply.** One external rail. The GL823K's only rated input is 5 V from VBUS;
VDD and VDDA are outputs of an on-chip band-gap regulator and carry decoupling
only, never an external feed. Card power is a separate switched net driven from
the controller's current-limited output, with its bulk capacitance at the
socket so card inrush never reaches the USB PHY rail. Four nets, eight
capacitors, no external regulator. See `docs/POWER-DESIGN.md`.

**Land patterns.** KiCad ships no footprint for a full-size SD socket, a
board-mounted USB-A male plug, or a 2.0 × 1.0 mm chip LED, so all three are
generated from the manufacturers' recommended land patterns and recorded
dimension by dimension in `docs/LAND-PATTERNS.md`. The USB plug's shell tabs sit
in correctly sized plated slots, which is what anchors a board that cantilevers
out of a host port.

**Outline.** An isosceles triangle, symmetric about the axis the apex arc and
all three connectors sit on. Both sides 70.175 mm at 48.007 degrees, with the
diagonals constructed as true tangents to the corner fillets.

**No external clock.** The controller has an on-chip clock source, so no 12 MHz
crystal is required.

**No card detect.** By design. The controller detects cards by polling the SD
bus, which is why the socket's mechanical CD and WP contacts terminate nowhere.

## Status

The design is DRC clean at 0 violations and 0 unconnected, its netlist is
checked against intent, and the supply topology is confirmed on hardware at
3.38 V.

**It has not been fabricated.** `docs/STATUS.md` lists what is verified, what is
not, and the checks to run on first articles. Read it before ordering.

## Layout

| Path | |
|---|---|
| `hardware/` | KiCad 10 project: schematic, PCB, footprints, 3D models |
| `fab/v2.0-kicad/` | Gerbers, drill, BOM, pick-and-place, assembly drawing |
| `docs/` | Power design, land patterns, status, controller datasheet |
| `tools/` | Generators and checks |
| `branding/` | OSHW mark and the KiCad colour theme used for the schematic PDF |

## Building

The package in `fab/v2.0-kicad/` uploads as-is. Its `README.md` states the
stackup, the plated slots, the non-plated holes and the impedance target for the
fab. To regenerate:

```sh
./tools/gen_fab.py                    # fabrication package
./tools/gen_footprints.py             # footprints
./tools/gen_3dmodels.py               # 3D models
./tools/verify_netlist.py             # netlist against intent
```

`gen_pcb.py`, `gen_schematic.py` and `route.py` are one-time bootstrappers.
Running them overwrites the routed board.

Do not run `Tools → Update Footprints from Library` in the PCB editor. KiCad
stores pad angles absolutely, `U1` sits at 270 degrees, and updating from the
library strips those angles and shorts the part. `docs/LAND-PATTERNS.md`
explains it.

## Licence

CERN-OHL-S-2.0. Distribute a variant and its design files must be shared under
the same terms.

Created by 1PhoneTucked.
