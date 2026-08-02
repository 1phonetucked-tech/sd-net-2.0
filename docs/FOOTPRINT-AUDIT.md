# Footprint audit against manufacturer land patterns

Audited 2026-08-02. `tools/gen_footprints.py` built `SD-006M`, `USB-AM90` and
the LED land from rev 1.5's fabricated pad geometry, on the reasoning that pads
boards were built with must match the physical parts. Rev 1.5 never enumerated,
so that reasoning was never actually tested — a mechanical error would have been
invisible behind the power defect.

This is the test. Every land pattern is compared against the manufacturer's own
recommended footprint drawing.

## Method

Both connector datasheets give a "recommended PCB layout" view. Printed
dimensions were read directly; positions were also measured independently by
rasterising the drawing at 300–900 dpi, locating the pad and hole centroids in
pixels, and scaling by a known printed dimension. The two agree throughout,
which is what makes the numbers below trustworthy to about ±0.05 mm.

Scale checks used: SD-006M `#4→#9 = 10.00` (24.325 px/mm at 300 dpi), verified
against `hole spacing 24.20` and `GROUND2 above GROUND1 = 1.20`. USB-AM90
`pin1→pin4 = 7.00` (87.5 px/mm at 700 dpi), verified against `peg spacing 4.50`
and `tab spacing 11.70`.

## SD-006M — SOFNG, LCSC C125615

Datasheet page 2, "CIRCUIT BOARD SIZE (Vertical view)".

| Dimension | Datasheet | Rev 1.5 / rev 2.0 | Δ |
|---|---|---|---|
| **Contact row → peg holes** | **24.60** | **24.05** | **−0.55** ⚠ |
| Peg hole spacing | 24.20 | 24.200 | ✓ |
| GROUND1 → peg holes (Y) | 2.10 | 2.101 | ✓ |
| GROUND2 above GROUND1 | 1.20 | 1.201 | ✓ |
| #4 → #9 | 10.00 | 10.000 | ✓ |
| #3 → #9 | 8.30 | 8.298 | ✓ |
| #2 → #9 / #1 → #9 | 5.00 / 2.50 | 4.999 / 2.499 | ✓ |
| #5 → #9 / #6 → #9 | 12.50 / 15.00 | 12.499 / 14.999 | ✓ |
| #7 → #6 (the irregular gap) | 2.43 | 2.431 | ✓ |
| #8 → #7 | 1.70 | 1.699 | ✓ |
| WP → #8 | 3.25 | 3.350 | −0.10 |
| CD → #9 | 6.43 | 6.650 | −0.22 |
| Contact pad | 1.20 × 2.00 | 1.1989 × 2.1996 | pad 0.20 longer |
| Ground tab pad | 1.70 × 2.00 | 1.999 × 2.3012 | pad 0.30 larger |
| Peg hole Ø | 1.50 | 1.60 | looser, fine |

**The contact-row error is confirmed three ways:** the printed `24.6` dimension;
the drawn geometry (598 px ÷ 24.325 px/mm = 24.58); and the fabricated rev 1.5
data itself, where the CPL puts CARD1's contacts at Y 43.635 and
`Drill_NPTH_Through.DRL` puts the pegs at Y 67.686 — 24.051 apart.

The pegs locate the socket, so the tails landed ~0.55 mm off the pads: about
78 % overlap on a 2.0 mm tail. Marginal rather than fatal, which is why nothing
caught it.

CD and WP are the only two contacts whose X is wrong, and they are the only two
this design leaves unconnected — someone transcribed the drawing by hand and got
sloppy on the pads nobody uses. Harmless here.

Pads larger than the datasheet (contacts +0.20, ground tabs +0.30) are left
alone. More fillet is not a defect, and DRC clearance still passes.

**Status: FIXED.** The contact row moved to y = −11.524, CD and WP to their
datasheet X, and pad 12 out to 14.582. `CARD1`'s own origin did not move, so the
mechanical fit `REV1.5-BASELINE.md` locks down is untouched.

Three knock-on changes were needed behind it:

* **Seven SD-bus tracks.** The pads move 0.549 mm *toward* U1, which is the easy
  direction — every contact drops straight down to a fan-out line at y 73.8, so
  each track start simply followed its pad. No re-topology.
* **The VCARD via at (86.5, 73.8) → (86.5, 74.05).** Pad 3 (GND) came down onto
  it: 0.052 mm copper clearance against a 0.2 mm rule. Pushed 0.25 mm clear.
* **C7 from (88.0, 75.1) → (88.0, 75.6).** The taller footprint's courtyard
  reached C7's. Rather than loosen the courtyard, C7 moved — it also restores
  the gap between C7's **VCARD** pad and CARD1's **GND** contact pad, which the
  row move had cut from 0.912 mm to 0.363 mm. Now 0.863 mm. A short there would
  tie VCARD to ground, which is the rev 1.5 failure all over again, so it was
  worth the 0.5 mm.

Verified afterwards: no non-GND copper runs anywhere under the socket body.

## USB-AM90 — Shou Han, LCSC C404965

Datasheet drawing A/0 dated 2018.07.10, bottom-right PCB layout view.

| Dimension | Datasheet | Rev 1.5 | Now | |
|---|---|---|---|---|
| Signal pin spacing | 2.50 / 2.00 / 2.50 | 2.502 / 1.999 / 2.499 | unchanged | ✓ |
| Signal hole Ø | 4−R0.50 → 1.00 | 1.0008 | unchanged | ✓ |
| Peg spacing | 4.50 | 4.500 | unchanged | ✓ |
| **Pin row → peg row** | **2.00** | **2.176** | **2.002** | fixed |
| **Shell tab opening** | **0.86 × 2.20 slot** | **Ø2.601 round** | **0.90 × 2.25 slot** | fixed |
| Shell tab spacing | 11.70 | 12.00 | 11.710 | fixed |

**The peg holes were an interference fit.** The peg is Ø0.85 +0.05/−0.02 in a
Ø1.00 hole — 0.05–0.075 mm of radial clearance. A 0.175 mm position error
exceeds it, so the pegs bind and the plug does not seat flat. Nothing routes to
NPTH, so correcting it cost no copper.

**The AM90 has no mounting posts.** Its shell ends in two flat 0.86 mm tabs that
belong in slots. Rev 1.5's Ø2.6 round holes gave those tabs almost no anchorage,
on a board that cantilevers ~75 mm out of a USB port. Slots are cut 0.04 mm over
the recommended 0.86 × 2.20 to leave room for hole plating.

**Status: FIXED.** Board pad geometry now matches
`hardware/sd-net.pretty/USB-AM90.kicad_mod` exactly.

## LED1 — Everlight 12-215SYGC/S530-E2/TR8, LCSC C131283

Not a rev 1.5 error — a rev 2.0 regression. The schematic kept the Everlight
MPN, but the PCB assigned it stock `LED_SMD:LED_0603_1608Metric`. The part is
~2.0 × 1.0 mm; rev 1.5's part-specific land has pads 0.899 × 0.800 at ±1.050,
which is a land for a 2.0 mm body, not a 1.6 mm one.

Fixed by generating `sd-net:LED-12-215SYGC` from the rev 1.5 export, with a
silkscreen cathode bar added (the stock footprint had polarity marking; the
generated ones do not, and an unmarked LED is an assembly coin-flip).

**Do not "simplify" this to a stock green 0603.** R1 is fed from **VDD**, so the
LED runs on 3.3 V and needs Vf ≤ ~2.4 V. The rev 1.5 part is a yellow-green
AlInGaP at 1.7–2.4 V — 5.5 mA through 220 Ω. The obvious LCSC 0603 green
(C72043) is an emerald InGaN with **Vf 3.3 V** and would barely light.

**Status: FIXED.**

## Everything else

`U1` uses stock `Package_SO:SSOP-16_3.9x4.9mm_P0.635mm`: pads 1.65 × 0.40 on
0.635 pitch with rows at ±2.625, against rev 1.5's 1.8136 × 0.3556 at ±2.6543.
Within 0.06 mm and IPC-correct. The caps and R1 all match their packages.

## Regenerating these footprints — the courtyard trap

`gen_footprints.py` derives each courtyard from the pad extents, so **any pad
move changes the courtyard too**. The board's footprint instances carry their
own copy of that rectangle, and editing pads without also updating the instance
`fp_rect` leaves the two out of sync — which KiCad reports as
`lib_footprint_mismatch`, the same warning CLAUDE.md discusses. It is a genuine
divergence, not the cosmetic one.

So after re-running the generator, sync three things in each board instance: pad
positions, **both** `fp_rect`s (F.CrtYd and F.Fab), and then re-fill zones.
`kicad-cli pcb drc --refill-zones --save-board` does the last part; stale zone
fill otherwise shows up as a pile of phantom clearance errors around whatever
moved.

Note also that saving through `kicad-cli` re-stamps pad rotation angles that
`a2b049a` had stripped from CARD1. That is harmless here — CARD1's pads are
rectangles at 180°, symmetric under it — but it is worth knowing that the
stripping done in that commit does not survive a save, and that **U1's 270°
angles are untouched by it** (verified byte-identical). U1 is the one where the
angles are load-bearing.

## What this does not prove

Land patterns matching the datasheet is not the same as parts seating. The
cheapest remaining check is physical, and rev 1.5 boards are the fixture: they
still carry the *uncorrected* geometry, so seating a real SD-006M on its pegs
and eyeballing where the tails fall confirms the 0.55 mm directly, and a real
AM90 confirms the pegs bound. Both are checks on the errors, not on the fixes —
the fixes themselves can only be confirmed on rev 2.0 hardware.
