# GL823K power topology, what the datasheet actually says

Read from `datasheets/GL823K_rev1.05.pdf` (Genesys Logic, Rev 1.05, 15 pp) on 2026-07-31.

## First: there is no "Typical Application Circuit"

`RESUME_NOTES.md` said to verify the fix against the datasheet's typical-application figure
before respinning. **That figure does not exist.** The Rev 1.05 datasheet is 15 pages, overview, features, SSOP-16 pinout, pin description, block diagram, electrical
characteristics, package dimensions, ordering info. There is no reference schematic and no
recommended decoupling values anywhere in it.

So that verification gate can't be satisfied as written. What the datasheet *does* give is
enough to settle the topology question on its own, see below, but final cap values are an
engineering judgement, not something we can cite.

## The finding that changes the fix

**The GL823K has exactly one external supply: 5 V.**

> §5.2 Operating Conditions, Supply Voltage **+4.75 V to +5.25 V**
> §5.3 DC Characteristics, V5, "5V power source", min 4.75 / max 5.25 V

There is **no 3.3 V entry anywhere** in the operating conditions or DC characteristics. And:

> §4.6 Regulator, "5V to 3.3V **Band Gap Regulator** for stable voltage supply for USB PHY,
> PMOS" / "3.3V to 1.8V, For core logic and internal memory"
>
> §4.7 PMOS, "On-Chip power MOSFETs for memory card power"
>
> §1 Overview, "Inside the chip, it integrates 5V to 3.3V regulator, 3.3V to 1.8V regulator
> and power MOSFETs"

Therefore **VDD (pin 9) and VDDA (pin 13) are outputs of the internal regulator, not supply
inputs.** The pin table calls them "Digital 3.3V power source" and "USB2.0 PHY 3.3V power
source", that phrasing reads as *inputs* at a glance, which is almost certainly how rev 1.5
went wrong. They are rails the chip generates and brings out to be decoupled.

Pin table (§3.2) for reference:

| Pin | Name | Datasheet description |
|---|---|---|
| 10 | 5V | VBUS 5V input, **the only real supply input** |
| 9 | VDD | Digital 3.3V power source, *regulator output* |
| 13 | VDDA | USB2.0 PHY 3.3V power source, *regulator output* |
| 8 | PMOS | Card power 200 mA, *switched output* |
| 1, 14 | VSS | Power ground |
| 12 | LED | Access LED (output) |

## What this means for rev 2.0

The rev 1.5 defect is **worse than "the card-power switch is defeated"**, net `$1N2351`
ties together *three separate internal output nodes* (VDD, VDDA, PMOS) and hangs all six
decoupling caps plus R1 off the resulting single node. Two on-chip regulator taps and a
switched card-power MOSFET are shorted to each other. The diagnosis stands and is now
stronger than the netlist alone showed.

The revised topology, this supersedes the "three rails, one 10 µF + 100 nF pair each" table
in `RESUME_NOTES.md`, which treated all three as equivalent supply rails:

| Node | Pin(s) | Direction | Treatment | Caps |
|---|---|---|---|---|
| **+5V** | `USB1.1` → `U1.10` | **input** | Bulk + HF to GND, close to pin 10 | C1 10 µF, C4 100 nF |
| **VDD** | `U1.9` | regulator **output** | HF at the pin, plus bulk | C2 10 µF, C5 100 nF |
| **VDDA** | `U1.13` | regulator **output** | PHY rail, keep tight and short | C6 100 nF, C8 100 nF |
| **VCARD** | `U1.8` → `CARD1.4` | switched **output** | At the *socket*, not the chip | C3 10 µF, C7 100 nF |

**C7 and C8 are new in rev 2.0** (100 nF 0603, LCSC C14663, same part as C4/C5/C6). Rev 1.5's
six caps stretch to three rails, not four: without them VCARD gets bulk but no high-frequency
decoupling, and VDDA gets neither a second cap nor any bulk. Two extra 0603s cost about a cent
each on a board that's being respun regardless. BOM goes 11 → 13 placements.

Nothing external drives VDD or VDDA. Nothing ties them to 5 V. Nothing ties any of them to
PMOS.

## VDD/VDDA: resolved, do not tie them together

**Decision: decouple VDD and VDDA separately to GND, each close to its own pin, and run no
external connection between them.**

This holds regardless of whether they're internally the same node, so the question doesn't
need to be answered before routing:

- **If internally common** (one band-gap tap brought out twice for clean PHY decoupling, the likelier case), an external link is *redundant*. Omitting it costs nothing.
- **If internally separate** (independently filtered digital and PHY taps), an external link
  *defeats* that on-chip isolation, dumping 8051 and card-interface switching noise straight
  into the USB 2.0 PHY rail. That's the same class of error as rev 1.5.

Not tying them is safe under both readings. Tying them is only safe under one. So don't.

There is also nothing to debate about *sourcing* them: this board has no external 3.3 V
supply and the chip's only rated input is 5 V, so VDD and VDDA are internally generated
either way.

### ✅ Confirmed on hardware, 2026-08-02, **3.38 V**

The above was reasoning. It has now been measured.

A rev 1.5 board was powered from a 5 V phone charger (VBUS confirmed at 5.17 V, inside the
4.75-5.25 V of Table 5.2) and the shorted pin-8/9/13 node read **3.38 V** against ground.

Nothing external feeds that node. VBUS is the board's only supply and it lands on pin 10
alone. So the 3.38 V can only be produced inside the chip, **the on-chip 5 V→3.3 V band-gap
regulator of §4.6 is real, it runs, and it drives these pins.** 3.38 V is also within the
±3 % you would expect of a band-gap part, so it is regulating, not merely leaking.

**VDD and VDDA are outputs. Nothing external needs to supply 3.3 V.** The rev 2.0 topology, 5 V in, VDD and VDDA decoupled separately at their own pins, no external link, is correct,
and is no longer an assumption.

One limit worth stating: rev 1.5 shorts pins 8, 9 and 13 together, so this measures the
combined node. It proves the node is driven; it does not say which of the three pins sources
it. That distinction does not affect any decision here, the design question was only ever
whether an external 3.3 V rail is required, and it is not.

Measured with a DT-830-class meter. ⚠️ Its first readings were ~23 % high with an unstable
reference; the low-battery icon was lit. Every number above was taken after fitting a fresh
9 V and re-checking against a known cell and the charger. If you repeat this, sanity-check
the meter on a fresh AA (1.5-1.6 V) before trusting anything it says.

### Observed failure mode, 2026-08-02, it never reached the bus

Same bench session, same rev 1.5 board. This is what the prototypes actually do, which
until now was nowhere in this repo:

| Condition | Observed |
|---|---|
| 5 V charger, empty slot | pin-8/9/13 node **stable at 3.38 V** |
| 5 V charger, card inserted | node **sags and fluctuates** |
| Mac, empty slot | **does not enumerate** |
| Mac, card inserted | **does not enumerate** |
| While failing | node cycles **3.3 V → 2.5 V → back up, or lower** |

**Two corrections to the earlier account.**

*It is not a card-power failure.* The board never appears on the bus at all, with or without
a card. The short does defeat card power, but that is not what stopped the prototypes.

*3.3 → 2.5 → 3.3 is not a sag; it is a brownout/reset loop.* Power applies, the chip starts,
the load steps, the rail collapses, the chip resets, repeat. A host never sees a device
because the device never stays alive long enough to enumerate.

The tell is the difference between the two supplies. On a **charger** with an empty slot the
node is stable, nothing is asking the chip to do anything. On a **Mac** it oscillates,
because the host actually attempts enumeration: the PHY switches on, D+ pulls up, high-speed
signalling starts, and the current draw steps hard. That step is what the rail cannot take.

Both known defects feed it:

- **VBUS has no decoupling at all**, so the current step has to arrive down a USB cable with
  zero local reservoir at pin 10.
- **The short puts all six caps, ~30 µF, on the regulator's output.** Charging that through
  an internal regulator with current limiting, from an unsupported input, is a textbook
  hiccup oscillator.

⚠️ This is *consistent with* the two known defects, which is not the same as proving there is
no third fault. What it does establish is that the two things rev 2.0 changes are the two
things that would break this loop: VBUS gains 10 µF + 100 nF, and the regulator's output load
drops from ~30 µF to ~10.3 µF on a node that no longer carries the card or the PHY.

**Still worth one probe** if a rev 1.5 board is to hand: measure VBUS (`USB1` pin 1 to pin 4)
while it is looping on a Mac. If VBUS cycles too, the undecoupled input is the driver. If
VBUS holds 5 V while the 3.3 V node cycles; the cause is downstream, the regulator current
limiting into 30 µF, or a fault latch on the shorted PMOS pin.

### Second-source search, what was actually checked (2026-07-31)

No verified second-source schematic was obtained. Every accessible route was blocked:

| Source | Result |
|---|---|
| [OSHWLab GL823K-Cardreader](https://oshwlab.com/oshwlab/GL823K-Cardreader) | Schematic only renders inside the EasyEDA editor. The two PDFs attached to the project turned out to be the same Rev 1.05 datasheet we already have, and a JLC ISO-27001 certificate. |
| EasyEDA document API | 403 (CloudFront). |
| [EEWorld TF card reader ref design](https://en.eeworld.com.cn/Reference_Designs/detail/59148) | Page returns no content to a fetcher. |
| [Scribd SD-WFI-V2-0](https://www.scribd.com/document/813586126/SD-WFI-V2-0) | Paywalled. |
| [PCBWay OTG card reader + HUB](https://www.pcbway.com/project/shareproject/Mobile_phone_OTG_card_reader___HUB.html) | Page returns no content to a fetcher. |

⚠️ Search-engine summaries claimed a GL823K schematic with "C1 4.7 µF, C2 0.1 µF, C3 4.7 µF,
C4 2.2 µF" and "USB5V through an **AP2112-3.3V** regulator". **Treat that as unverified.**
Those summaries describe pages that could not be read directly, and the AP2112 detail almost
certainly belongs to the *SD-WiFi* board in that same result set, a design that pairs a
GL823K with a WiFi module, where the LDO powers the radio, not the card-reader chip. Do not
let it talk you into feeding VDD/VDDA from an external 3.3 V rail. Nothing in the datasheet
supports that, and it would fight the on-chip regulator.

### A definitive bench test, if you want certainty

Take a **loose, unsoldered GL823K** and measure resistance / diode drop between **pin 9 and
pin 13**. Near-zero ohms means one internal node; anything else means they're separate. This
cannot be done on a rev 1.5 board, the PCB shorts those pins together, which is the bug.

It's a nice-to-know, not a blocker: the recommended layout above is correct either way.

## Remaining notes

1. **Cap values.** 100 nF per power pin plus 10 µF bulk on VBUS is conventional and safe.
   Nothing in the datasheet mandates values, so the existing parts are fine.
2. **Card power budget.** PMOS is rated **200 mA**. Modern high-speed SD cards can exceed
   that transiently, the 10 µF at the socket matters for exactly this reason.
3. **R1 / LED1.** Pin 12 is an output that drives the access LED. Feed the anode through R1
   from **VDD**, cathode to pin 12. Do not feed it from `VCARD`.
4. **Placement.** Rev 1.5 put the 100 nF caps on one side of U1 and the 10 µF on the other,
   which made sense when they all shared one net. Now each cap belongs beside the specific
   pin it serves, VDDA's especially, since that's the USB PHY rail.
