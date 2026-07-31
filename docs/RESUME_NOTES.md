# SD - NET 1.5 — review notes & next steps

_Saved 2026-07-13. Pick up from here._

Project: **sd - net**, open-source full-size USB SD card reader (EasyEDA Pro, GL823K
controller). OSHWA-certified **UID US002797** (creator 1PhoneTucked, CERN-OHL-S-2.0).
Prior prototypes didn't work; this session confirmed why.

---

## 1. Logo — DONE, ready to place

Files are in `oshwa_mark/`:
- **`oshw_gear_black.svg`** ← import this (plain open-source-hardware gear, black, **no UID number**)
- `oshw_gear_black.png` ← raster fallback
- `README.md` ← details

Made from your `oshw-logo.svg`, recolored teal `#0099B0` → pure black for clean single-color
silkscreen import.

### How to add it in EasyEDA Pro
1. Open the **PCB** (not schematic) of sd - net.
2. **Place → Image** (or the image icon on the PCB toolbar / Edit → Import → Image).
3. Choose `oshwa_mark/oshw_gear_black.svg`.
4. Layer → **Top Silkscreen** (or Bottom Silkscreen for the back).
5. Size → **width ≈ 13 mm** (height auto-fills to ~14 mm). This is the recommended size —
   the "open source hardware" wordmark is the limiter; 10 mm is the floor, 12–15 mm is comfy.
6. Place it on a copper-free area, then run **Design → Check DRC**.

_Optional:_ if you want it smaller (6–8 mm), ask for a **gear-only version without the
wordmark** — the gear stays crisp small, the text doesn't.

---

## 2. PCB — the "VCC" bug is CONFIRMED (fix before reordering)

Confirmed from your own `Netlist_Schematic1_2026-07-13.tel` and the Gerber flying-probe data.

**The problem — one net does too much.** Net `$1N2351` shorts together:
`C1.1 C2.1 C3.1 C4.1 C5.1 C6.1  CARD1.4(card VDD)  R1.1  U1.8(PMOS)  U1.9(VDD)  U1.13(VDDA)`

On the GL823K:
- **Pin 8 (PMOS)** = the chip's dedicated, current-limited **card-power output** ("Card power 200mA").
  It should feed **only** the SD card's VDD — its own net.
- **Pin 9 (VDD)** = digital 3.3V supply, **Pin 13 (VDDA)** = USB-PHY 3.3V supply → these two form the chip 3.3V rail.
- **Pin 10 (5V)** = USB VBUS input. Currently net `$1N2347` = only `U1.10 USB1.1` → **no decoupling cap on 5V**.

Shorting the PMOS output to the 3.3V rail defeats the on-chip card-power switch → cards
likely never enumerate. **Prime suspect for the dead prototypes.**

### The fix — ZERO new parts (you already have exactly the right caps)
You have 3× 10µF (C1/C2/C3) + 3× 100nF (C4/C5/C6) = three 10µF+100nF pairs. Split the one
overloaded net into the **three rails that should exist** and give each a pair:

| Rail | Pins | Caps |
|------|------|------|
| **5V / VBUS input** | USB1.1 → U1.10 | one 10µF + one 100nF |
| **3.3V chip rail** | U1.9 (VDD) + U1.13 (VDDA) | one 10µF + one 100nF |
| **Card power (new net)** | U1.8 (PMOS) → CARD1.4 (card VDD) | one 10µF + one 100nF |

- Keep R1 (LED) fed from the **3.3V chip rail**, not the PMOS/card net.
- In EasyEDA Pro: edit the **schematic** — break the wire tying PMOS to VDD/VDDA, run a
  dedicated wire PMOS(pin8)→card VDD(pin4), re-assign the caps, then update the PCB & re-route.

> ⚠️ **Verify before respinning:** confirm the exact topology & cap values against the
> **GL823K datasheet "Typical Application Circuit"** (Rev 1.05, LCSC part C284879). The
> diagnosis is netlist-proven; the datasheet figure is the authority on final values.

### Secondary (nice-to-have, not blockers)
- **Floating shields:** USB1 MH1/MH2 and the SD socket shell tabs (CARD1 pins 12/13) aren't
  connected anywhere — normally tied to GND (directly, or via 1MΩ ∥ 1nF). Card-detect (CD)
  and write-protect (WP) are also unconnected — fine, they're optional.
- **GPIO (U1 pin 11):** floating — low priority, typically acceptable per datasheet.

---

## Next time — pick up with:
1. (If wanted) gear-only logo variant for a smaller placement.
2. Implement the 3-rail cap fix in the EasyEDA schematic, cross-checked against the GL823K
   datasheet typical-application circuit.
3. Re-run DRC, regenerate Gerbers, reorder.
