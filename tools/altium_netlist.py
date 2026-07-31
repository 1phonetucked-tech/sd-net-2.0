#!/usr/bin/env python3
"""Extract a netlist from an Altium/Protel **ASCII** .PcbDoc.

EasyEDA Pro exports Altium ASCII 5.0, which KiCad's Altium importer rejects (it
wants the binary OLE compound format). The ASCII is plain pipe-delimited text
though, so we can read the connectivity out of it directly. This is the ground
truth for what rev 1.5 was actually fabricated as.

    ./tools/altium_netlist.py <file.pcbdoc>
"""

import sys
from collections import defaultdict


def records(path):
    """Yield (kind, {field: value}) for each |RECORD=... block."""
    data = open(path, encoding="latin-1").read()
    for chunk in data.split("|RECORD="):
        chunk = chunk.strip()
        if not chunk:
            continue
        fields = {}
        parts = chunk.split("|")
        kind = parts[0]
        for p in parts[1:]:
            if "=" in p:
                k, _, v = p.partition("=")
                fields.setdefault(k, v)
        yield kind, fields


def build(path):
    nets, comps, pads = {}, {}, []
    for kind, f in records(path):
        if kind == "Net":
            nets[int(f["ID"])] = f["NAME"]
        elif kind == "Component":
            comps[int(f["ID"])] = {
                "ref": f.get("SOURCEDESIGNATOR", "?"),
                "pattern": f.get("PATTERN", ""),
                "x": f.get("X", ""),
                "y": f.get("Y", ""),
                "rot": f.get("ROTATION", ""),
                "layer": f.get("LAYER", ""),
            }
        elif kind == "Pad":
            pads.append(f)

    netmap = defaultdict(list)
    for p in pads:
        net = int(p.get("NET", -1))
        if net < 0:
            continue
        comp = int(p.get("COMPONENT", -1))
        ref = comps.get(comp, {}).get("ref", "?") if comp >= 0 else "(free)"
        netmap[net].append(f"{ref}.{p.get('NAME','?')}")

    return nets, comps, netmap


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    nets, comps, netmap = build(sys.argv[1])

    print(f"# {len(comps)} components, {len(nets)} nets\n")
    print("## Components\n")
    for i in sorted(comps):
        c = comps[i]
        print(f"  {c['ref']:<7} {c['pattern']:<34} @ {c['x']},{c['y']} "
              f"rot={c['rot']} {c['layer']}")

    print("\n## Nets\n")
    for i in sorted(nets):
        members = sorted(netmap.get(i, []))
        flag = "  <-- " + str(len(members)) + " nodes" if len(members) > 4 else ""
        print(f"  [{i:>2}] {nets[i]:<12} {' '.join(members) or '(no pads)'}{flag}")

    orphan = set(netmap) - set(nets)
    if orphan:
        print(f"\n!! pads reference undefined net ids: {sorted(orphan)}")


if __name__ == "__main__":
    main()
