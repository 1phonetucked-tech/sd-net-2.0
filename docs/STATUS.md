# Status and open items

Rev 2.0 has not been fabricated. Everything below distinguishes what has been
verified from what has not.

## Verified

: DRC 0 violations, 0 unconnected, with `missing_courtyard` and
  `track_not_centered_on_via` enabled
: Netlist checked against intent by `tools/verify_netlist.py`, 15 nets
: Supply topology confirmed on hardware at 3.38 V, see `POWER-DESIGN.md`
: All three land patterns measured against the manufacturers' drawings, see
  `LAND-PATTERNS.md`
: No external crystal required, the controller has an on-chip clock source
: Fabrication package regenerates byte-identical apart from embedded timestamps

## Not verified

**Nothing in this design has run.** No board has been fabricated. DRC and
netlist checks confirm the design matches its intent; they say nothing about
whether the intent is correct.

## Open items

### Assembly orientation

The largest remaining risk. `U1` is an SSOP-16 where pin 1 must be correct, and
`LED1` is polarised. The pick-and-place file uses KiCad's native convention:
millimetres, Y negative, rotations in KiCad's frame.

Ask the assembler to confirm the rotation convention rather than assume it, and
to send a photograph of the first assembled board for comparison against
`fab/v2.0-kicad/sd-net-2.0-placement-reference.png`.

### Mechanical

The board is 116.12 × 64.98 mm hanging off a single USB-A plug, roughly 75 mm of
overhang once inserted. A knock puts leverage on both the plug's solder joints
and the host port.

The shell tabs now sit in correctly sized plated slots rather than oversized
round holes, which is what carries that load. The lever arm is unchanged.

### Differential pair impedance

`USB_DP` and `USB_DM` are intended as a 90 R differential pair: 0.30 mm wide,
0.346 mm gap on F.Cu, referenced to In1.Cu, solved with IPC-2141 against a
standard 4-layer 1.6 mm stackup, 7628 prepreg at 0.1855 mm after lamination,
Dk 4.74.

This is a first-order closed-form approximation rather than a 2D field solve.
It is also not critical: the routed pair measures 10.11 mm and 9.50 mm, roughly
63 ps of flight time against USB 2.0's 500 ps rise time, below the point at
which a trace behaves as a transmission line. Intra-pair skew is about 4 ps.

Worth asking a fab to check against their production stackup, but not a gate. If
a different width or gap is required, note the pair threads a 1.475 mm corridor
with 0.265 mm either side, so widening it needs C6 to move.

### SD socket overhang

The socket body overhangs the board edge by up to 1.14 mm at its two front
corners. Within the tolerance of the modelled body position, so it needs
checking against a physical part rather than correcting blind.

## First article checks

1. Plug into a host and confirm the device enumerates.
2. Insert a card and confirm it mounts.
3. Measure `VCARD` at `CARD1` pin 4. It must come up under the controller's
   control rather than sitting hard-tied to the 3.3 V rail. This is the single
   most informative measurement on the board.
4. Confirm the LED lights on power and flickers during transfer. It indicates
   power and access, not card presence.

## Order quantity

Order five, not thirty. Every open item above is cheap to discover on five
boards and expensive to discover on thirty.
