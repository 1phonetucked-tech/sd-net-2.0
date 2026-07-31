#!/usr/bin/env python3
"""Dump an .xlsx to CSV using only the stdlib.

EasyEDA's BOM and pick-and-place exports are .xlsx, which git can't diff. This
converts them to CSV so the rev 1.5 baseline is reviewable and diffable against
whatever rev 2.0's KiCad exports produce.

    ./tools/xlsx2csv.py <file.xlsx> [output.csv]
"""

import csv
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def shared_strings(zf):
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(t.text or "" for t in si.iter(f"{NS}t"))
        for si in root.findall(f"{NS}si")
    ]


def cell_ref_to_index(ref):
    """'AB12' -> 27 (zero-based column)."""
    col = 0
    for ch in ref:
        if not ch.isalpha():
            break
        col = col * 26 + (ord(ch.upper()) - ord("A") + 1)
    return col - 1


def rows(zf, strings, sheet="xl/worksheets/sheet1.xml"):
    root = ET.fromstring(zf.read(sheet))
    for row in root.iter(f"{NS}row"):
        cells = {}
        for c in row.findall(f"{NS}c"):
            v = c.find(f"{NS}v")
            if v is None or v.text is None:
                # Inline strings show up as <is><t>...</t></is>
                is_el = c.find(f"{NS}is")
                if is_el is None:
                    continue
                val = "".join(t.text or "" for t in is_el.iter(f"{NS}t"))
            else:
                val = v.text
                if c.get("t") == "s":
                    val = strings[int(val)]
            ref = c.get("r") or ""
            cells[cell_ref_to_index(ref) if ref else len(cells)] = val
        if not cells:
            yield []
            continue
        yield [cells.get(i, "") for i in range(max(cells) + 1)]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    with zipfile.ZipFile(src) as zf:
        strings = shared_strings(zf)
        data = list(rows(zf, strings))

    out = open(sys.argv[2], "w", newline="") if len(sys.argv) > 2 else sys.stdout
    csv.writer(out).writerows(data)
    if out is not sys.stdout:
        out.close()


if __name__ == "__main__":
    main()
