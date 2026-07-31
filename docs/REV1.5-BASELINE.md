# Rev 1.5 measured baseline

Extracted from the fabricated Gerbers, BOM and pick-and-place on 2026-07-31. These are the
numbers rev 2.0 gets checked against — anything here that changes during the KiCad migration
changed by accident unless we decided otherwise.

Regenerate with:

```
python3 tools/gerber_bbox.py fab/v1.5-easyeda/gerber-extracted/*.G* 
python3 tools/xlsx2csv.py "fab/v1.5-easyeda/BOM_sd - net 1.5_sd - net 1.5_2026-06-19.xlsx"
```

## Bill of materials — 11 placements, 7 line items

| Ref | Part | Package | LCSC |
|---|---|---|---|
| C1, C2, C3 | 10 µF | C0805 | C15850 (Samsung CL21A106KAYNNNE) |
| C4, C5, C6 | 100 nF | C0603 | C14663 (Yageo CC0603KRX7R9BB104) |
| CARD1 | SD-006M SD socket, 13-pin | SD-SMD_SD-006M | C125615 (Sofng) |
| LED1 | 12-215SYGC/S530-E2 green | LED-SMD | C131283 (Everlight) |
| R1 | 220 Ω | R0603 | C22962 (Uni-Royal) |
| U1 | **GL823K-HCY04** | **SSOP-16** (4.9 × 3.9, 0.64 pitch) | C284879 (Genesys) |
| USB1 | **AM90 USB-A male, right-angle** | **USB-AM-TH** (through-hole) | C404965 (Shou Han) |

Rev 2.0 must land on this same 11-placement, 7-line BOM — the rail fix adds no parts.

**U1 is SSOP-16, not QFN.** 0.64 mm pitch with visible leads: hand-solderable with a fine tip
and flux, and very reworkable. Good news for debugging rev 2.0 by hand before committing to a
production run.

## ⚠️ USB1 is through-hole — this affects the assembly quote

`SMD: No` in the pick-and-place. Through-hole parts are **not** part of standard economic
SMT assembly at most fabs — they're hand-soldered and billed separately per joint, and some
low-cost assembly tiers refuse THT outright. Six joints on USB1, so it's not expensive, but
it must be raised explicitly when quoting, and it's a point in PCBWay's favor (they handle
mixed THT/SMT assembly more willingly than the cheapest JLCPCB tiers).

Worth asking during rev 2.0: is there an SMD right-angle USB-A male equivalent? Going
all-SMD would make the board assembly-house-trivial and cheaper at every quantity. Not a
blocker — just the single highest-leverage DFM change available.

## Mechanical envelope

**Overall: 113.85 × 74.56 mm**, board outline X 9.80–123.66, Y 6.25–80.81 mm.

It is not a rectangle. The outline is a **symmetric shaped board** — flat bottom edge, sides
angling up and inward, capped by a **13.54 mm-radius arc** centered at (68.30, 72.00),
with small corner fillets at the bottom two corners. Symmetric about **X ≈ 68.3 mm**.

A **12.40 × 15.40 mm rectangular tab** protrudes below the bottom edge at X 61.62–74.02,
Y 6.25–21.65 — centered on the same 68.3 mm axis as USB1.

### Placement coordinates (mm, from pick-and-place)

| Ref | Mid X | Mid Y | Rot | Layer |
|---|---|---|---|---|
| CARD1 | 68.199 | 54.610 | 180 | Top |
| U1 | 68.326 | 34.290 | 180 | Top |
| USB1 | 67.818 | 25.146 | 0 | Top |
| C1 | 73.914 | 38.227 | 0 | Top |
| C2 | 74.041 | 34.925 | 0 | Top |
| C3 | 74.041 | 31.369 | 0 | Top |
| C4 | 62.992 | 37.592 | 0 | Top |
| C5 | 62.865 | 34.544 | 0 | Top |
| C6 | 62.865 | 31.496 | 0 | Top |
| R1 | 37.719 | 25.400 | 0 | Top |
| LED1 | 17.653 | 25.273 | 0 | Top |

Everything functional sits on the centerline: SD socket at top, controller below it, USB plug
at the bottom, with the 100 nF caps to the left of U1 and the 10 µF to the right. R1 and LED1
run out to the lower left — the LED is a long way from the controller, ~50 mm of trace.

**Must not move in rev 2.0:** USB1 and CARD1 positions and the outline tab — those are
mechanical fits. Everything else is free to re-place, and the decoupling caps *should* move:
each pair belongs as close as possible to the pin of the rail it now serves.

## Stackup

4 layers — `GTL` / `G1` / `G2` / `GBL`. Copper layers span X 8.55–124.79, Y 20.88–85.19
(top/bottom, including pads and silk-adjacent copper); inner layers X 9.96–123.48,
Y 20.78–80.64.

Drills: PTH 0.305 mm (vias), 1.000 mm, 2.600 mm; NPTH 1.000 mm and 1.600 mm.

Keep 4 layers in rev 2.0 — USB 2.0 high-speed D+/D− wants a controlled ~90 Ω differential
pair over a solid reference plane. On boards you're handing out, there's no reason to gamble
on a 2-layer stackup to save a few dollars.
