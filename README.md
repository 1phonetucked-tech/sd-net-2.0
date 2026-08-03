# sd - net 2.0

full-size USB SD card reader > USB-A plug for end user connect > 13 placements across 7 line items in between.

[![CERN-OHL-S-2.0](https://img.shields.io/badge/license-CERN--OHL--S--2.0-green)](LICENSE)  
hardware, everything in `hardware/` and `fab/` > CERN-OHL-S-2.0 > distribute a variant and its design files must be shared under the same terms  
documentation, everything in `docs/` > CC-BY-SA-4.0 > credit the source, share adaptations alike  
software, the generators in `tools/` > GPL-3.0 > see `tools/LICENSE`

| | |
|---|---|
| controller | Genesys Logic GL823K, SSOP-16, LCSC C284879 |
| board | 116.12 × 64.98 mm, 4 layers, 1.6 mm, ENIG |
| finish | black soldermask, white legend |
| placements | 13, of which 12 SMT and 1 through-hole |
| interface | USB 2.0 high speed, SD 4-bit mode |

boards are exclusively given away > not sold.

## specifications

**supply**  
1 external rail. GL823K's only rated input is 5 V from VBUS (multimeter tested). VDD and VDDA are outputs of an on-chip band-gap regulator and carry decoupling only > never an external feed. card power is a separate switched net driven from the controller's current-limited output, with its bulk capacitance at the socket so card inrush never reaches the USB PHY rail. **four nets > eight capacitors > no external regulator**  
review `docs/POWER-DESIGN.md`

**land patterns**  
KiCad ships no footprint matching any of the three parts on this board > SD-006M (SD slot) > AM90 (USB) > Everlight 12-215SYGC/S530-E2/TR8 (LED). i opted out of pulling them from easyeda2kicad and generated them from the manufacturers' recommended land patterns instead > dimension by dimension > 3D models the same way. every value is recorded in `docs/LAND-PATTERNS.md` > the USB plug's shell tabs sit in correctly sized plated slots rather than oversized round holes > those tabs are the only thing anchoring a board that cantilevers roughly 75 mm out of a host port

**outline**  
isosceles triangle > symmetric about the axis the apex arc and all three connectors sit on > both sides 70.175 mm at 48.007 degrees, with the diagonals constructed as true tangents to the corner fillets

**no external clock**  
controller (GL823K-HCY04) has an on-chip clock source > 12 MHz crystal is not required.

**no card detect**  
by design. controller detects cards by polling the SD bus, which is why the socket's mechanical CD and WP are no connect

## currently

design is DRC clean.  
0 violations and 0 unconnected  
netlist is checked against intent > supply topology is confirmed on hardware at 3.38 V

**rev 2.0 has not been fabricated (yet)**  
`docs/STATUS.md` lists what is verified > what is not > and the checks to run on first articles.  
review before ordering

## layout

| Path | |
|---|---|
| `hardware/` | KiCad 10 project: schematic, PCB, footprints, 3D models |
| `fab/v2.0-kicad/` | Gerbers, drill, BOM, pick-and-place, assembly drawing |
| `docs/` | Power design, land patterns, status |
| `tools/` | Generators and checks |
| `branding/` | OSHW mark and the KiCad colour theme used for the schematic PDF |

## building

the package in `fab/v2.0-kicad/` uploads as-is. Its `README.md` states the
stackup, the plated slots, the non-plated holes and the impedance target for the
fab. To regenerate:

```sh
./tools/gen_fab.py                    # fabrication package
./tools/gen_footprints.py             # footprints
./tools/gen_3dmodels.py               # 3D models
./tools/verify_netlist.py             # netlist against intent
```

`gen_schematic.py` and `gen_pcb.py` built the original KiCad files > kept as a record only > running either overwrites the current board

**do not run `Tools → Update Footprints from Library` in the PCB editor. KiCad
stores pad angles absolutely & `U1` sits at 270 degrees > updating from the library strips those angles and shorts the part**  
*also explained in `docs/LAND-PATTERNS.md`*

## thanks

[PCBWay](https://www.pcbway.com/) is supporting the rev 2.0 run > five boards,
fabricated and assembled.

created by (1)PhoneTucked.
