# Before ordering boards

Rev 2.0 is finished and verified as far as software can verify it: DRC clean,
0 unconnected, netlist checked against intent, mechanics identical to rev 1.5.

None of that is the same as knowing it works. Rev 1.5 also passed every check
its tools could run, and it never enumerated. What follows is everything that is
still assumption rather than fact, and what it would cost to close each one.

## Order a small batch first

**Five boards, not thirty.** Prove one enumerates before committing to the
giveaway run.

Every open item below is cheap to discover on five boards and expensive to
discover on thirty. It is also a better sponsorship pitch — approaching PCBWay
with a board you can demonstrate is a different conversation from asking them to
fund a hypothesis.

## Open item 1 — VDD/VDDA was reasoned, never measured

`docs/POWER-DESIGN.md` argues that VDD (pin 9) and VDDA (pin 13) are outputs of
the GL823K's internal regulator, and that decoupling them separately without an
external link is correct whether or not they share an internal node. The
reasoning holds, and the datasheet supports it: §5.2/§5.3 list 5 V as the only
supply, §4.6 describes the on-chip 5 V→3.3 V band-gap regulator.

**It was never confirmed on hardware.** No second-source schematic was
obtainable — every route was blocked, see the dead-end table in
`POWER-DESIGN.md`.

**The test, on a rev 1.5 board, costs nothing:**

1. Plug a rev 1.5 board into USB.
2. Measure `U1` pin 9 against `U1` pin 14 (VSS).

| Reading | Meaning |
|---|---|
| ~3.3 V | The internal regulator is running. VDD/VDDA are outputs. Design is right. |
| 0 V | The reading behind the whole rev 2.0 power topology is wrong. **Stop and reassess.** |

Rev 1.5 shorts pins 8, 9 and 13 together, so this measures the combined node —
which is exactly what makes the test easy.

## Open item 2 — the 90 Ω pair is calculated, not field-solved

The USB differential pair is 0.30 mm wide with a 0.346 mm gap, solved with
IPC-2141 microstrip against PCBWay's published standard 4-layer 1.6 mm stackup
(7628 prepreg, 0.1855 mm after lamination, Dk 4.74). That is a first-order
closed-form approximation, not a 2D field solve.

The first attempt at this pair was **105.9 Ω** — badly off 90 — and nothing in
the design flow caught it. It only surfaced because the geometry was checked
against real dielectric numbers.

**Ask PCBWay's impedance team to verify against their production stackup.** It
is already flagged in the fab package README. If they want a different width or
gap, note the pair threads a 1.475 mm corridor between C6's pad and U1's pads
with only 0.265 mm either side — **C6 has to move before the pair can widen.**

## Open item 3 — the footprints came from a board that never worked

`SD-006M` and `USB-AM90` were derived from rev 1.5's fabricated pad geometry
(`tools/gen_footprints.py`), round-trip verified to 0.057 µm. That guarantees
they match rev 1.5 exactly. It does **not** guarantee rev 1.5 was right — a
footprint error would have been masked by the power defect that stopped anything
from working.

Partial reassurance: the netlist audit in `REV1.5-BASELINE.md` confirms all nine
SD contacts map to the correct GL823K pins, and both USB data lines are on the
right pins. So the *pinout* is right. What is unverified is the *physical* pad
geometry — whether the socket and plug actually seat.

Note that the NPTH mounting holes for both connectors were **missing** from the
first cut of these footprints and had to be recovered from the drill file. That
is the class of error that hides here.

## Open item 4 — nothing in this design has ever run

Rev 1.5 never enumerated. Rev 2.0 fixes the one defect that was found, and that
defect is confirmed three independent ways. But "we fixed the bug we found" is
not "there are no other bugs", and no part of this design has been proven in
hardware.

## Open item 5 — mechanical: 114 mm cantilevered off a USB plug

The board is **113.85 × 60.29 mm** hanging off a single USB-A plug — roughly
75 mm of overhang once inserted. A knock puts real leverage on both the AM90's
solder joints and the host's USB port.

This is inherited from rev 1.5, not introduced by any rev 2.0 change, and it has
never been examined. It matters more than usual here because these boards are
being handed to other people and going into their laptops.

The AM90's two 2.6 mm through-hole mounting posts are what carry that load,
which is the main argument for keeping it over any surface-mount alternative.

## Bring-up, once boards arrive

1. Plug into a Mac. Check **System Information → USB** for the device.
2. Insert a card. Confirm it mounts.
3. **Measure `VCARD` at `CARD1` pin 4.** It should come up under the GL823K's
   control, not sit hard-tied to the 3.3 V rail. That is precisely the test
   rev 1.5 failed, and the single most informative measurement on the board.
4. Confirm the LED lights on power and flickers during transfer — it indicates
   power and access, not card presence.
