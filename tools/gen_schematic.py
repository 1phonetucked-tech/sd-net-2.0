#!/usr/bin/env python3
"""Bootstrap the rev 2.0 KiCad schematic from the recovered rev 1.5 netlist.

One-time generator. It emits `hardware/sd-net.kicad_sym` (project-local symbols
for the three parts KiCad has no stock symbol for) and `hardware/sd-net.kicad_sch`
wired to the corrected rev 2.0 netlist.

The point of generating rather than importing is that the fix is then correct *by
construction*: the four power nodes are separate nets here because they're
declared separate, not because someone remembered to cut a wire. See
`docs/POWER-DESIGN.md`.

Once this has run and ERC is clean, edit the schematic in KiCad — do not re-run
this and clobber hand edits.

    ./tools/gen_schematic.py
"""

import os
import re
import uuid

SHARED = "/Applications/KiCad/KiCad.app/Contents/SharedSupport"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(HERE, "hardware")

VERSION = 20251024      # .kicad_sym format
SCH_VERSION = 20260306  # .kicad_sch format -- different numbering from the lib
GEN_VER = "10.0"


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------- symbols ----

def pin(number, name, ptype, x, y, angle, length=5.08):
    return f"""\t\t\t(pin {ptype} line
\t\t\t\t(at {x} {y} {angle})
\t\t\t\t(length {length})
\t\t\t\t(name "{name}"
\t\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t\t)
\t\t\t\t(number "{number}"
\t\t\t\t\t(effects (font (size 1.27 1.27)))
\t\t\t\t)
\t\t\t)
"""


def prop(name, value, x, y, hide=False, show_name=False):
    h = "\n\t\t\t(hide yes)" if hide else ""
    return f"""\t\t(property "{name}" "{value}"
\t\t\t(at {x} {y} 0)
\t\t\t(show_name {"yes" if show_name else "no"}){h}
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
"""


def make_symbol(name, desc, ref, footprint, pins, half_w, top, bot, datasheet=""):
    """pins: list of (number, pinname, type, side, y)."""
    body = f"""\t\t(symbol "{name}_0_1"
\t\t\t(rectangle
\t\t\t\t(start {-half_w} {top})
\t\t\t\t(end {half_w} {bot})
\t\t\t\t(stroke (width 0.254) (type default))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t)
"""
    px = []
    for number, pname, ptype, side, y in pins:
        if side == "L":
            px.append(pin(number, pname, ptype, -(half_w + 5.08), y, 0))
        else:
            px.append(pin(number, pname, ptype, half_w + 5.08, y, 180))
    unit = f'\t\t(symbol "{name}_1_1"\n' + "".join(px) + "\t\t)\n"

    return (
        f'\t(symbol "{name}"\n'
        "\t\t(pin_names (offset 1.016))\n"
        "\t\t(exclude_from_sim no)\n"
        "\t\t(in_bom yes)\n"
        "\t\t(on_board yes)\n"
        + prop("Reference", ref, -half_w, top + 2.54)
        + prop("Value", name, -half_w, bot - 2.54)
        + prop("Footprint", footprint, 0, 0, hide=True)
        + prop("Datasheet", datasheet, 0, 0, hide=True)
        + prop("Description", desc, 0, 0, hide=True)
        + body
        + unit
        + "\t)\n"
    )


# GL823K — SSOP-16. Pin types encode the finding in docs/POWER-DESIGN.md:
# VDD/VDDA/PMOS are regulator OUTPUTS (power_out), 5V is the only input.
GL823K_PINS = [
    ("10", "5V",   "power_in",       "L",  12.7),
    ("9",  "VDD",  "power_out",      "L",  10.16),
    ("13", "VDDA", "power_out",      "L",  7.62),
    ("8",  "PMOS", "power_out",      "L",  5.08),
    ("1",  "VSS",  "power_in",       "L", -12.7),
    ("14", "VSS",  "power_in",       "L", -15.24),
    ("15", "DP",   "bidirectional",  "R",  12.7),
    ("16", "DM",   "bidirectional",  "R",  10.16),
    ("4",  "CLK",  "output",         "R",  5.08),
    ("5",  "CMD",  "bidirectional",  "R",  2.54),
    ("3",  "D0",   "bidirectional",  "R",  0),
    ("2",  "D1",   "bidirectional",  "R", -2.54),
    ("7",  "D2",   "bidirectional",  "R", -5.08),
    ("6",  "D3",   "bidirectional",  "R", -7.62),
    ("12", "LED",  "open_collector", "R", -12.7),
    ("11", "GPIO", "input",          "R", -15.24),
]

# SD-006M full-size SD socket (LCSC C125615). Pad names match the physical part
# as exported from EasyEDA, including the CD/WP/shell pads.
SD_PINS = [
    ("1",  "DAT3_CD", "bidirectional", "L",  15.24),
    ("2",  "CMD",     "bidirectional", "L",  12.7),
    ("3",  "VSS1",    "power_in",      "L",  10.16),
    ("4",  "VDD",     "power_in",      "L",  7.62),
    ("5",  "CLK",     "input",         "L",  5.08),
    ("6",  "VSS2",    "power_in",      "L",  2.54),
    ("7",  "DAT0",    "bidirectional", "L",  0),
    ("8",  "DAT1",    "bidirectional", "L", -2.54),
    ("9",  "DAT2",    "bidirectional", "L", -5.08),
    ("CD", "CARD_DET","passive",       "L", -7.62),
    ("WP", "WP",      "passive",       "L", -10.16),
    ("12", "SHELL1",  "passive",       "L", -12.7),
    ("13", "SHELL2",  "passive",       "L", -15.24),
]

# AM90 right-angle USB-A male plug (LCSC C404965).
USB_PINS = [
    ("1",   "VBUS", "power_out",     "L",  6.35),
    ("2",   "D-",   "bidirectional", "L",  3.81),
    ("3",   "D+",   "bidirectional", "L",  1.27),
    ("4",   "GND",  "power_in",      "L", -1.27),
    ("MH1", "MH1",  "passive",       "L", -3.81),
    ("MH2", "MH2",  "passive",       "L", -6.35),
]

CUSTOM = [
    ("GL823K", "USB 2.0 SD/MSPRO card reader controller, SSOP-16", "U",
     "Package_SO:SSOP-16_3.9x4.9mm_P0.635mm", GL823K_PINS, 12.7, 17.78, -19.05,
     "https://w.electrodragon.com/w/images/c/cb/GL823K.pdf"),
    ("SD-006M", "Full-size SD card socket, push-push, 13 pad", "CARD",
     "sd-net:SD-006M", SD_PINS, 12.7, 19.05, -19.05, ""),
    ("USB-AM90", "USB 2.0 type-A male plug, right angle, through hole", "USB",
     "sd-net:USB-AM90", USB_PINS, 12.7, 10.16, -10.16, ""),
]


def write_symbol_lib():
    body = "".join(make_symbol(*c) for c in CUSTOM)
    out = (
        "(kicad_symbol_lib\n"
        f"\t(version {VERSION})\n"
        '\t(generator "sd-net gen_schematic.py")\n'
        f'\t(generator_version "{GEN_VER}")\n'
        + body
        + ")\n"
    )
    open(os.path.join(HW, "sd-net.kicad_sym"), "w").write(out)
    return {name: dict((p[0], (p[3], p[4])) for p in pins)
            for name, _, _, _, pins, *_ in CUSTOM}


# ------------------------------------------------------- stock symbol grab ---

# A symbol looks slightly different inside a .kicad_sym library than it does
# embedded in a .kicad_sch lib_symbols cache: the library form carries
# show_name/do_not_autoplace/in_pos_files/... and puts (hide yes) as a sibling of
# (effects), while the schematic form omits those and nests (hide yes) *inside*
# (effects). Copying a library symbol verbatim into a schematic makes the whole
# file unloadable, with no error beyond "Failed to load schematic" -- hence this
# transform rather than string surgery.

SEXP_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')
LIB_ONLY_FIELDS = {
    "show_name", "do_not_autoplace", "in_pos_files",
    "duplicate_pin_numbers_are_jumpers",
}


def sexp_parse(text):
    toks = SEXP_TOKEN.findall(text)

    def build(i):
        out = []
        while i < len(toks):
            t = toks[i]
            if t == "(":
                sub, i = build(i + 1)
                out.append(sub)
            elif t == ")":
                return out, i + 1
            else:
                out.append(t)
                i += 1
        return out, i

    return build(0)[0][0]


def sexp_dump(node, indent=0):
    if isinstance(node, str):
        return node
    if all(isinstance(c, str) for c in node):
        return "(" + " ".join(node) + ")"
    # Keep leading atoms on the head line: (property "Reference" "U" ...)
    k = 1
    while k < len(node) and isinstance(node[k], str):
        k += 1
    pad = "\t" * (indent + 1)
    body = "\n".join(pad + sexp_dump(c, indent + 1) for c in node[k:])
    return "(" + " ".join(node[:k]) + f"\n{body}\n" + "\t" * indent + ")"


def to_schematic_form(node):
    """Rewrite a library-style symbol into the form a .kicad_sch accepts."""
    if isinstance(node, str):
        return node
    kids = [to_schematic_form(c) for c in node[1:]
            if not (isinstance(c, list) and c and c[0] in LIB_ONLY_FIELDS)]
    name = node[0]
    if name == "property":
        hides = [c for c in kids if isinstance(c, list) and c[0] == "hide"]
        for h in hides:
            kids.remove(h)
        if hides:
            eff = next((c for c in kids
                        if isinstance(c, list) and c[0] == "effects"), None)
            if eff is None:
                eff = ["effects"]
                kids.append(eff)
            eff.append(["hide", "yes"])
    return [name] + kids


def grab(libfile, symname):
    """Pull one symbol block out of a stock .kicad_sym, renamed to Lib:Name."""
    path = os.path.join(SHARED, "symbols", libfile + ".kicad_sym")
    s = open(path).read()
    start = s.find(f'\t(symbol "{symname}"\n')
    if start < 0:
        raise SystemExit(f"symbol {symname} not found in {libfile}")
    end = s.find('\n\t(symbol "', start + 5)
    blk = s[start:end if end > 0 else s.rfind(")")]
    # Only the *outer* symbol takes the "Lib:Name" form. The child unit symbols
    # keep their bare "Name_0_1" / "Name_1_1" names -- qualifying those makes the
    # schematic unloadable.
    blk = blk.replace(f'(symbol "{symname}"', f'(symbol "{libfile}:{symname}"', 1)
    return blk.rstrip("\n") + "\n"


def stock_pin_positions(blk):
    """Map pin number -> (x, y) from a symbol block."""
    out = {}
    for m in re.finditer(
        r"\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)"
        r"(?:.|\n)*?\(number \"([^\"]+)\"", blk
    ):
        x, y, ang, num = float(m.group(1)), float(m.group(2)), int(m.group(3)), m.group(4)
        out[num] = (x, y, ang)
    return out


# ------------------------------------------------------------- schematic -----

# Rev 2.0 netlist. Four separate power nodes -- see docs/POWER-DESIGN.md.
#   +5V   VBUS input          : 10uF C1 + 100nF C4
#   VDD   regulator output    : 10uF C2 + 100nF C5, feeds the LED via R1
#   VDDA  PHY reg output      : 100nF C6, kept on its own net (never tied to VDD)
#   VCARD switched card power : 10uF C3, at the socket
NETS = {
    "+5V":      [("USB1", "1"), ("U1", "10"), ("C1", "1"), ("C4", "1")],
    "VDD":      [("U1", "9"), ("C2", "1"), ("C5", "1"), ("R1", "1")],
    "VDDA":     [("U1", "13"), ("C6", "1")],
    "VCARD":    [("U1", "8"), ("CARD1", "4"), ("C3", "1")],
    "GND":      [("U1", "1"), ("U1", "14"), ("USB1", "4"),
                 ("CARD1", "3"), ("CARD1", "6"),
                 ("CARD1", "12"), ("CARD1", "13"),
                 ("USB1", "MH1"), ("USB1", "MH2"),
                 ("C1", "2"), ("C2", "2"), ("C3", "2"),
                 ("C4", "2"), ("C5", "2"), ("C6", "2")],
    "SD_CMD":   [("CARD1", "2"), ("U1", "5")],
    "SD_CLK":   [("CARD1", "5"), ("U1", "4")],
    "SD_DAT0":  [("CARD1", "7"), ("U1", "3")],
    "SD_DAT1":  [("CARD1", "8"), ("U1", "2")],
    "SD_DAT2":  [("CARD1", "9"), ("U1", "7")],
    "SD_DAT3":  [("CARD1", "1"), ("U1", "6")],
    "USB_DP":   [("U1", "15"), ("USB1", "3")],
    "USB_DM":   [("U1", "16"), ("USB1", "2")],
    "LED_A":    [("R1", "2"), ("LED1", "2")],
    "LED_K":    [("LED1", "1"), ("U1", "12")],
}

# ref -> (lib_id, value, footprint, x, y)
PARTS = {
    "U1":    ("sd-net:GL823K",   "GL823K-HCY04", "Package_SO:SSOP-16_3.9x4.9mm_P0.635mm", 146.05, 100.33),
    "CARD1": ("sd-net:SD-006M",  "SD-006M",      "sd-net:SD-006M",                        215.90, 100.33),
    "USB1":  ("sd-net:USB-AM90", "AM90",         "sd-net:USB-AM90",                        68.58, 100.33),
    "C1":    ("Device:C",        "10uF",         "Capacitor_SMD:C_0805_2012Metric",        68.58, 148.59),
    "C4":    ("Device:C",        "100nF",        "Capacitor_SMD:C_0603_1608Metric",        88.90, 148.59),
    "C2":    ("Device:C",        "10uF",         "Capacitor_SMD:C_0805_2012Metric",       109.22, 148.59),
    "C5":    ("Device:C",        "100nF",        "Capacitor_SMD:C_0603_1608Metric",       129.54, 148.59),
    "C6":    ("Device:C",        "100nF",        "Capacitor_SMD:C_0603_1608Metric",       149.86, 148.59),
    "C3":    ("Device:C",        "10uF",         "Capacitor_SMD:C_0805_2012Metric",       170.18, 148.59),
    "R1":    ("Device:R",        "220",          "Resistor_SMD:R_0603_1608Metric",         68.58, 173.99),
    "LED1":  ("Device:LED",      "12-215SYGC",   "LED_SMD:LED_0603_1608Metric",            96.52, 173.99),
}

# Pins that are deliberately left floating. Marking them no-connect is the
# difference between "we decided this" and "we forgot this" -- rev 1.5 gave no
# way to tell them apart.
#   U1.11  GPIO       - acceptable per datasheet section 3.2
#   CARD1.CD/WP       - card-detect and write-protect are optional
NC_PINS = [("U1", "11"), ("CARD1", "CD"), ("CARD1", "WP")]

# GND is fed only by power_input pins (the USB shell and both VSS pairs), so ERC
# needs a flag telling it the net really is driven.
PWR_FLAGS = [("GND", 60.96, 190.5)]

# LCSC part numbers, carried into the BOM.
LCSC = {
    "U1": "C284879", "CARD1": "C125615", "USB1": "C404965",
    "C1": "C15850", "C2": "C15850", "C3": "C15850",
    "C4": "C14663", "C5": "C14663", "C6": "C14663",
    "R1": "C22962", "LED1": "C131283",
}


# Where the reference/value text sits relative to the symbol origin. The big
# custom symbols have clear space above them; the two-pin Device symbols do not
# -- their pins carry net labels directly above and below, so their text goes to
# the right instead. Getting this wrong drops R1's and LED1's designators on top
# of the capacitor row.
LABEL_POS = {
    "sd-net:GL823K":   (0, -20.32, "center"),
    "sd-net:SD-006M":  (0, -21.59, "center"),
    "sd-net:USB-AM90": (0, -12.70, "center"),
    "Device:C":        (3.81, -1.27, "left"),
    "Device:R":        (3.81, -1.27, "left"),
    "Device:LED":      (3.81, -1.27, "left"),
    "power:PWR_FLAG":  (3.81, -1.27, "left"),
}


def sym_instance(ref, lib_id, value, footprint, x, y, uid_):
    lcsc = LCSC.get(ref, "")
    dx, dy, just = LABEL_POS.get(lib_id, (0, -20.32, "center"))
    j = "" if just == "center" else f" (justify {just})"
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(fields_autoplaced yes)
\t\t(uuid "{uid_}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x + dx} {y + dy} 0)
\t\t\t(effects (font (size 1.27 1.27)){j})
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {x + dx} {y + dy + 2.54} 0)
\t\t\t(effects (font (size 1.27 1.27)){j})
\t\t)
\t\t(property "Footprint" "{footprint}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "LCSC" "{lcsc}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(instances
\t\t\t(project "sd-net"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{ref}") (unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
"""


def wire(x1, y1, x2, y2):
    return f"""\t(wire
\t\t(pts (xy {x1} {y1}) (xy {x2} {y2}))
\t\t(stroke (width 0) (type default))
\t\t(uuid "{uid()}")
\t)
"""


def glabel(name, x, y, angle, justify):
    return f"""\t(global_label "{name}"
\t\t(shape bidirectional)
\t\t(at {x} {y} {angle})
\t\t(fields_autoplaced yes)
\t\t(effects (font (size 1.27 1.27)) (justify {justify}))
\t\t(uuid "{uid()}")
\t)
"""


ROOT_UUID = uid()


def main():
    os.makedirs(HW, exist_ok=True)
    custom_pins = write_symbol_lib()

    # Stock symbols we reuse, plus their pin geometry.
    stock_blocks, stock_pins = {}, {}
    for lib, name in [("Device", "C"), ("Device", "R"), ("Device", "LED"),
                      ("power", "PWR_FLAG")]:
        blk = grab(lib, name)
        stock_blocks[f"{lib}:{name}"] = blk
        stock_pins[f"{lib}:{name}"] = stock_pin_positions(blk)

    # Where does each (ref, pinnum) sit on the sheet, and which way does it face?
    def pin_xy(ref, num):
        lib_id, _, _, px, py = PARTS[ref]
        if lib_id.startswith("sd-net:"):
            sname = lib_id.split(":", 1)[1]
            side, ly = custom_pins[sname][num]
            half_w = dict((c[0], c[5]) for c in CUSTOM)[sname]
            lx = -(half_w + 5.08) if side == "L" else (half_w + 5.08)
            return px + lx, py - ly, side
        lx, ly, ang = stock_pins[lib_id][num]
        # Device:C / R / LED pins point up (90) and down (270).
        side = "U" if ang == 270 else "D"
        return px + lx, py - ly, side

    # Build lib_symbols section. Every block -- ours and KiCad's -- goes through
    # to_schematic_form(), because the library and schematic dialects differ.
    blocks = []
    custom_src = open(os.path.join(HW, "sd-net.kicad_sym")).read()
    for name, *_ in CUSTOM:
        blk_start = custom_src.find(f'\t(symbol "{name}"\n')
        blk_end = custom_src.find('\n\t(symbol "', blk_start + 5)
        blk = custom_src[blk_start:blk_end if blk_end > 0 else custom_src.rfind(")")]
        blk = blk.replace(f'(symbol "{name}"', f'(symbol "sd-net:{name}"', 1)
        blocks.append(blk)
    blocks.extend(stock_blocks.values())

    libsyms = "\t(lib_symbols\n"
    for blk in blocks:
        node = to_schematic_form(sexp_parse(blk))
        libsyms += "\t\t" + sexp_dump(node, 2) + "\n"
    libsyms += "\t)\n"

    parts = "".join(
        sym_instance(ref, lib_id, value, fp, x, y, uid())
        for ref, (lib_id, value, fp, x, y) in PARTS.items()
    )

    conns = ""
    STUB = 3.81
    for net, members in NETS.items():
        for ref, num in members:
            x, y, side = pin_xy(ref, num)
            if side == "L":
                conns += wire(x, y, x - STUB, y)
                conns += glabel(net, x - STUB, y, 180, "right")
            elif side == "R":
                conns += wire(x, y, x + STUB, y)
                conns += glabel(net, x + STUB, y, 0, "left")
            elif side == "U":
                conns += wire(x, y, x, y - STUB)
                conns += glabel(net, x, y - STUB, 90, "left")
            else:
                conns += wire(x, y, x, y + STUB)
                conns += glabel(net, x, y + STUB, 270, "left")

    # Deliberately floating pins get an explicit no-connect marker.
    for ref, num in NC_PINS:
        x, y, _ = pin_xy(ref, num)
        conns += f'\t(no_connect\n\t\t(at {x} {y})\n\t\t(uuid "{uid()}")\n\t)\n'

    # PWR_FLAG so ERC accepts nets fed only by power_input pins.
    for n, (net, fx, fy) in enumerate(PWR_FLAGS, 1):
        lx, ly, ang = stock_pins["power:PWR_FLAG"]["1"]
        px, py = fx + lx, fy - ly
        parts += sym_instance(f"#FLG0{n}", "power:PWR_FLAG", "PWR_FLAG",
                              "", fx, fy, uid())
        if ang == 270:
            conns += wire(px, py, px, py - STUB)
            conns += glabel(net, px, py - STUB, 90, "left")
        else:
            conns += wire(px, py, px, py + STUB)
            conns += glabel(net, px, py + STUB, 270, "left")

    sch = (
        "(kicad_sch\n"
        f"\t(version {SCH_VERSION})\n"
        '\t(generator "sd-net gen_schematic.py")\n'
        f'\t(generator_version "{GEN_VER}")\n'
        f'\t(uuid "{ROOT_UUID}")\n'
        '\t(paper "A3")\n'
        + libsyms
        + parts
        + conns
        + "\t(sheet_instances\n\t\t(path \"/\"\n\t\t\t(page \"1\")\n\t\t)\n\t)\n"
        ")\n"
    )
    open(os.path.join(HW, "sd-net.kicad_sch"), "w").write(sch)

    pro = """{
  "board": {"design_settings": {"defaults": {}}},
  "meta": {"filename": "sd-net.kicad_pro", "version": 3},
  "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
  "sheets": [["%s", "Root"]]
}
""" % ROOT_UUID
    open(os.path.join(HW, "sd-net.kicad_pro"), "w").write(pro)

    tbl = """(sym_lib_table
  (version 7)
  (lib (name "sd-net")(type "KiCad")(uri "${KIPRJMOD}/sd-net.kicad_sym")(options "")(descr "sd - net project symbols"))
)
"""
    open(os.path.join(HW, "sym-lib-table"), "w").write(tbl)

    print(f"wrote {len(PARTS)} parts, {len(NETS)} nets -> {HW}")


if __name__ == "__main__":
    main()
