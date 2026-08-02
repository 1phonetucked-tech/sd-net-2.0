# sd - net 2.0

An open-source, full-size **USB SD card reader** on a single chip. USB-A plug on
one end, full-size SD socket on the other, and not much in between: the whole
board is 13 placements across 7 line items.

[![OSHWA certified](https://img.shields.io/badge/OSHWA-US002797-blue)](https://certification.oshwa.org/us002797.html)
[![License](https://img.shields.io/badge/license-CERN--OHL--S--2.0-green)](https://cern-ohl.web.cern.ch/)

| | |
|---|---|
| Controller | Genesys Logic **GL823K** (SSOP-16, LCSC C284879) |
| Board | 116.12 x 64.98 mm, 4 layers, 1.6 mm, ENIG, black mask, white legend |
| Placements | 13 (12 SMT, 1 through-hole) |
| Licence | CERN-OHL-S-2.0 |
| OSHWA UID | **US002797** |

Boards are **given away, not sold**.

## Status

**Rev 2.0 is complete and verified as far as software and a bench meter can take
it, but it has never been fabricated.** DRC is clean at 0 violations and 0
unconnected, the netlist checks against intent, and the power topology has been
confirmed on hardware. It has not yet been built.

Rev 1.5 was fabricated in June 2026 and **never worked**. That failure is now
fully diagnosed, reproduced on the bench, and fixed.

## What went wrong in rev 1.5, and what 2.0 does about it

Rev 1.5 shorted the GL823K's card-power switch output (pin 8) to its own 3.3 V
rail (pins 9 and 13), putting all six decoupling capacitors on one node, and
left the 5 V input with no decoupling at all.

Measured on the bench, the prototypes never reach the USB bus, with or without a
card in the slot. The 3.3 V rail cycles **3.3 V, down to 2.5 V, back up**: a
brownout and reset loop rather than a sag. The host attempts enumeration, the
PHY switches on, the current steps, and the rail collapses.

Rev 2.0 splits that single net into four, **+5V, VDD, VDDA and VCARD**, each
decoupled at its own pin, with card power restored to the chip's current-limited
switch. Full reasoning and measurements in
[`docs/POWER-DESIGN.md`](docs/POWER-DESIGN.md).

Four footprint errors were also found by measuring the land patterns against the
manufacturers' own drawings, and corrected. Among them an SD contact row 0.55 mm
out of position, and a USB plug whose locating pegs were an interference fit.
See [`docs/FOOTPRINT-AUDIT.md`](docs/FOOTPRINT-AUDIT.md).

## Repository layout

| Path | |
|---|---|
| `hardware/` | KiCad 10 project: schematic, PCB, footprints, 3D models |
| `fab/v2.0-kicad/` | Fabrication package: Gerbers, drill, BOM, pick-and-place |
| `fab/v1.5-easyeda/` | Frozen rev 1.5 outputs. Reference only, do not edit |
| `docs/` | Design notes, measurements, manufacturing decisions |
| `tools/` | Generators and checkers, all runnable standalone |
| `branding/` | OSHW mark and project artwork |

## Building it

The fabrication package in `fab/v2.0-kicad/` is ready to upload. Regenerate with:

```sh
./tools/gen_fab.py                    # -> fab/v2.0-kicad/
```

Other generators:

```sh
./tools/gen_footprints.py   # footprints, corrected against datasheets
./tools/gen_3dmodels.py     # 3D models KiCad has none of
./tools/verify_netlist.py   # netlist vs intent
```

## Read before spending money

**[`docs/BEFORE-ORDERING.md`](docs/BEFORE-ORDERING.md)** lists everything still
assumption rather than fact, and what each would cost to close. Nothing in this
design has run yet, and the largest remaining risk is assembly orientation
rather than anything in the design itself.

## Credits

Created by **1PhoneTucked**. Licensed CERN-OHL-S-2.0: if you make and distribute
a variant, the design files for it have to be shared under the same terms.
