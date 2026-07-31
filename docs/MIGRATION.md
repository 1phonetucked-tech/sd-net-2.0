# EasyEDA Pro → KiCad 10 migration (rev 1.5 → 2.0)

## Correction on the route

EasyEDA Pro has **no native KiCad export**. It only *imports* KiCad. The community
converters you'll find (`easyeda2kicad.py`, Wokwi's converter, `easyeda2kicad6`) target the
**EasyEDA Standard** JSON format — they do not handle EasyEDA **Pro** project files, and
`easyeda2kicad.py` in particular is a *component* library converter, not a project converter.

The route that actually works Pro → KiCad is **via Altium**:

```
EasyEDA Pro  ──Export→Altium Designer──►  .SchDoc + .PcbDoc  ──KiCad Altium importer──►  KiCad 10
```

KiCad has built-in Altium importers for both schematic and PCB. EasyEDA Pro writes Altium
ASCII 5.0, which is the dialect the importer handles best.

## Step 1 — export from EasyEDA Pro

In the sd - net project:

1. **File → Export → Altium Designer** (also reachable as top menu **Export → Altium Designer**).
2. Export **both** the schematic and the PCB. You get a zip containing `.SchDoc` and `.PcbDoc`.
3. Drop the zip in `fab/v1.5-easyeda/altium-export/` and tell me — I'll take it from there.

Also grab, while you're in there:

- **File → Export → Netlist** (any format) — a second netlist confirms the rail split later.
- The **BOM** with LCSC part numbers, if it has more detail than the 2026-06-19 xlsx.

## Step 2 — import into KiCad (I'll drive this)

1. `File → Import Non-KiCad Project → Altium Project`, or import `.PcbDoc` / `.SchDoc`
   individually into a fresh project at `hardware/sd-net.kicad_pro`.
2. Expect these to need hand-repair after import — this is normal, not a failed conversion:
   - **Copper pours don't survive** the EasyEDA export. Re-draw and re-fill all zones.
   - **Text size/position drifts.** Silkscreen especially.
   - **Symbols/footprints land in an import-specific library.** They need re-pointing at
     proper KiCad libs, or promoting into a project-local `sd-net.pretty` / `.kicad_sym`.
   - **Net names** come across mangled (`$1N2351` style). Rename to `+5V`, `+3V3`, `VCARD`, `GND`.
3. Run `Update PCB from Schematic` with **re-link footprints by reference designator** ticked.

## Step 3 — apply the rail fix

Do this in the **schematic**, not the PCB. Per `../CLAUDE.md`:

- Break the wire tying `U1.8` (PMOS) to `U1.9`/`U1.13`.
- Run a dedicated net `U1.8` → `CARD1.4`, name it `VCARD`.
- Reassign the three 10 µF / 100 nF pairs one per rail (5 V, 3 V3, VCARD).
- Move R1/LED to the 3 V3 rail.
- Tie `USB1.MH1`/`MH2` and `CARD1.12`/`13` to GND (direct, or 1 MΩ ∥ 1 nF if you'd rather
  keep chassis and signal ground split).
- **Verify against the GL823K datasheet typical-application circuit before routing.**

## Step 4 — verify the migration didn't lose anything

Once both exist I'll diff rev 1.5 against rev 2.0 mechanically:

- Board outline and connector positions from the old Gerbers vs the new `.kicad_pcb` — the
  USB-A plug tongue dimensions and SD socket position are the parts that *must* not move.
- Netlist diff: every rev 1.5 net should map to a rev 2.0 net, with exactly the intended
  three-way split showing as the difference.
- BOM diff: component count should be identical (zero new parts).

## Worth deciding during the rebuild

- **Layer count.** Rev 1.5 is 4-layer. For USB 2.0 high-speed (480 Mbps) the D+/D− pair
  wants ~90 Ω differential, which 4-layer makes easy and controlled. On a board this small a
  2-layer stackup can work and is cheaper — but given these are being handed out, keeping
  4-layer for signal integrity is the safer call. Worth a quote both ways.
- **Silkscreen.** Place `branding/oshwa_mark/oshw_gear_black.svg` at ≈13 mm wide, plus the
  OSHWA UID **US002797**, revision, and the CERN-OHL-S-2.0 notice.
