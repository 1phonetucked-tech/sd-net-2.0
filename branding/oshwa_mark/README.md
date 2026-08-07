# Open-source-hardware logo — silkscreen artwork

Prepared for **sd - net** (the plain gear needs no number).

Black (single silkscreen color) version of the classic open-source-hardware gear,
recolored from your `oshw-logo.svg` (OSHW teal `#0099B0` → pure black).

| File | Use |
|------|-----|
| `oshw_gear_13mm.svg` | **Import this** into KiCad — same artwork with real-world dimensions stamped on it (13.0 × 13.661 mm), so `File → Import → Graphics` sizes it correctly instead of guessing a DPI |
| `oshw_gear_black.svg` | Unsized original |
| `oshw_gear_black.png` | 1000 px raster fallback if the SVG import ever misbehaves |

**Target size: 13 mm wide, 10 mm absolute floor.** An earlier version of this file
said 8–12 mm, which was wrong: the artwork is not gear-only, it carries the
"open source hardware" wordmark underneath, and the wordmark is what sets the
minimum. At 13 mm total the wordmark's two lines are roughly 2.2 mm each. Go
much below 10 mm and the thin strokes drop under PCBWay's 0.15 mm silkscreen
minimum, where they print broken or vanish.

Place on a copper-free area — silkscreen over exposed copper gets clipped.
The plain gear logo is free to use on any design that meets the open-source-hardware
definition — no registration or UID required.
