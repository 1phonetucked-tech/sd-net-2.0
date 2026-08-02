#!/usr/bin/env python3
"""Report the coordinate bounding box of a Gerber file.

Used to pin down rev 1.5's mechanical envelope from the fabricated Gerbers, so
the KiCad rev 2.0 board can be checked against it. The USB-A connector and SD
socket positions are mechanical fits, they must not drift during the migration.

    ./tools/gerber_bbox.py <file.gbr> [...]
"""

import re
import sys

COORD = re.compile(r"([XY])(-?\d+)")
FS = re.compile(r"%FSLA?X(\d)(\d)Y(\d)(\d)\*%")


def parse(path):
    xi = xd = yi = yd = None
    units = "mm"
    xs, ys = [], []
    x = y = None

    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("G04"):  # comment
                continue
            m = FS.search(line)
            if m:
                xi, xd, yi, yd = (int(g) for g in m.groups())
                continue
            if "%MOIN*%" in line:
                units = "in"
            if xd is None:
                continue
            # Only D01/D02/D03 lines carry real geometry.
            if not re.search(r"D0[123]\*?$", line):
                continue
            for axis, raw in COORD.findall(line):
                digits = xd if axis == "X" else yd
                neg = raw.startswith("-")
                raw = raw.lstrip("-")
                val = int(raw) / (10**digits)
                if neg:
                    val = -val
                (xs if axis == "X" else ys).append(val)
                if axis == "X":
                    x = val
                else:
                    y = val

    if not xs or not ys:
        return None
    return {
        "units": units,
        "x": (min(xs), max(xs)),
        "y": (min(ys), max(ys)),
        "w": max(xs) - min(xs),
        "h": max(ys) - min(ys),
        "points": len(xs),
    }


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for path in sys.argv[1:]:
        r = parse(path)
        name = path.rsplit("/", 1)[-1]
        if r is None:
            print(f"{name}: no coordinates found")
            continue
        print(
            f"{name}: X {r['x'][0]:.3f}..{r['x'][1]:.3f}  "
            f"Y {r['y'][0]:.3f}..{r['y'][1]:.3f}  "
            f"= {r['w']:.3f} x {r['h']:.3f} {r['units']}  ({r['points']} pts)"
        )


if __name__ == "__main__":
    main()
