# GL823K power topology — what the datasheet actually says

Read from `datasheets/GL823K_rev1.05.pdf` (Genesys Logic, Rev 1.05, 15 pp) on 2026-07-31.

## First: there is no "Typical Application Circuit"

`RESUME_NOTES.md` said to verify the fix against the datasheet's typical-application figure
before respinning. **That figure does not exist.** The Rev 1.05 datasheet is 15 pages —
overview, features, SSOP-16 pinout, pin description, block diagram, electrical
characteristics, package dimensions, ordering info. There is no reference schematic and no
recommended decoupling values anywhere in it.

So that verification gate can't be satisfied as written. What the datasheet *does* give is
enough to settle the topology question on its own — see below — but final cap values are an
engineering judgement, not something we can cite.

## The finding that changes the fix

**The GL823K has exactly one external supply: 5 V.**

> §5.2 Operating Conditions — Supply Voltage **+4.75 V to +5.25 V**
> §5.3 DC Characteristics — V5, "5V power source", min 4.75 / max 5.25 V

There is **no 3.3 V entry anywhere** in the operating conditions or DC characteristics. And:

> §4.6 Regulator — "5V to 3.3V **Band Gap Regulator** for stable voltage supply for USB PHY,
> PMOS" / "3.3V to 1.8V — For core logic and internal memory"
>
> §4.7 PMOS — "On-Chip power MOSFETs for memory card power"
>
> §1 Overview — "Inside the chip, it integrates 5V to 3.3V regulator, 3.3V to 1.8V regulator
> and power MOSFETs"

Therefore **VDD (pin 9) and VDDA (pin 13) are outputs of the internal regulator, not supply
inputs.** The pin table calls them "Digital 3.3V power source" and "USB2.0 PHY 3.3V power
source" — that phrasing reads as *inputs* at a glance, which is almost certainly how rev 1.5
went wrong. They are rails the chip generates and brings out to be decoupled.

Pin table (§3.2) for reference:

| Pin | Name | Datasheet description |
|---|---|---|
| 10 | 5V | VBUS 5V input — **the only real supply input** |
| 9 | VDD | Digital 3.3V power source — *regulator output* |
| 13 | VDDA | USB2.0 PHY 3.3V power source — *regulator output* |
| 8 | PMOS | Card power 200 mA — *switched output* |
| 1, 14 | VSS | Power ground |
| 12 | LED | Access LED (output) |

## What this means for rev 2.0

The rev 1.5 defect is **worse than "the card-power switch is defeated"** — net `$1N2351`
ties together *three separate internal output nodes* (VDD, VDDA, PMOS) and hangs all six
decoupling caps plus R1 off the resulting single node. Two on-chip regulator taps and a
switched card-power MOSFET are shorted to each other. The diagnosis stands and is now
stronger than the netlist alone showed.

The revised topology — this supersedes the "three rails, one 10 µF + 100 nF pair each" table
in `RESUME_NOTES.md`, which treated all three as equivalent supply rails:

| Node | Pin(s) | Direction | Treatment |
|---|---|---|---|
| **5 V / VBUS** | `USB1.1` → `U1.10` | **input** | Bulk 10 µF + 100 nF to GND, close to pin 10 |
| **VDD** | `U1.9` | regulator **output** | 100 nF to GND at the pin, + bulk 10 µF |
| **VDDA** | `U1.13` | regulator **output** | 100 nF to GND at the pin — PHY rail, keep this one tight and short |
| **VCARD** | `U1.8` → `CARD1.4` | switched **output** | 10 µF + 100 nF at the *socket*, not at the chip |

Nothing external drives VDD or VDDA. Nothing ties them to 5 V. Nothing ties any of them to
PMOS.

## Open questions to resolve before routing

1. **Are VDD and VDDA the same internal node?** The datasheet doesn't say. They're described
   as separate 3.3 V "sources" (digital vs USB PHY) fed by one band-gap regulator, so they
   are plausibly the same tap brought out twice for clean PHY decoupling. Common practice in
   that case is to decouple each separately and optionally link them through a ferrite bead.
   **Do not tie them with a plain wire until this is settled** — that's a variant of the
   rev 1.5 mistake.
2. **Cap values.** 100 nF per power pin and 10 µF bulk on VBUS is conventional and safe.
   Nothing in the datasheet mandates values, so we're free to keep the existing parts.
3. **Card power budget.** PMOS is rated **200 mA**. Modern high-speed SD cards can exceed
   that transiently — the 10 µF at the socket matters for exactly this reason.
4. **R1 / LED1.** Pin 12 is an output that drives the access LED. Feed the anode through R1
   from **VDD**, cathode to pin 12. Do not feed it from `VCARD`.

Since there's no vendor reference schematic, the best available cross-check is a
**second-source GL823K product schematic** — several exist publicly for commercial readers
using this exact chip. Worth pulling one before the rev 2.0 layout is finalized, purely to
confirm the VDD/VDDA question.
