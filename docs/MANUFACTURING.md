# Manufacturer selection

Priorities set 2026-07-31: **open-source sponsorship**, **quality + real support**,
**low cost per board** — in that order. Boards are **fab-assembled (PCBA)** and **handed out,
not sold**.

## Recommendation

**Lead with PCBWay, keep JLCPCB as the cost baseline, try Aisler as a long shot.**

### PCBWay — primary target
Best fit for all three priorities at once. They run an explicit
[sponsorship platform for open-source projects](https://www.pcbway.com/project/sponsor/) and
an [educational/OSHW program](https://www.pcbway.com/sponsor.html); sponsorship requests go to
**sponsor@pcbway.com** and they turn coupon codes around in ~24 h. Their support is
responsive and they give real DFM feedback — which matters here, because rev 1.5 shipped
with a fatal netlist bug that a fab review would not have caught but a careful engineer might.

They also host [shared projects](https://www.pcbway.com/project/shareproject/?tag=open+source):
publish sd - net there and PCBWay donates 10% of any order others place through your page back
to you. For a board meant to be handed out and replicated, that's a distribution channel and a
funding trickle in one.

**An OSHWA-certified design with a UID (US002797) is exactly the profile these programs
exist for.** That certification is the strongest card you're holding — lead with it.

### JLCPCB — cost baseline
Still the price floor for small PCBA runs, and you're already in their ecosystem via EasyEDA
(same parent company), so the rev 1.5 BOM/CPL are already in their format. Use them to price
the run so you know what a PCBWay sponsorship is actually worth. Downside: support is thin
and DFM feedback is minimal — you get what you upload.

### Aisler — long shot worth one email
[Sponsors open hardware projects](https://community.aisler.net/t/sponsoring-for-open-hardware-projects/3786)
with PCBs and stencils; contact their DevRel with a project summary. They run €500/yr for
community hubs and €1000 store credit for student teams. Quality and support are excellent.
Catch: they're EU-based, so shipping and customs to the US cut into the value, and their
assembly offering is narrower than PCBWay's.

### Ruled out for this project
- **OSH Park** — beautiful boards, US-based, but no assembly service and expensive per unit.
  Wrong shape for a PCBA giveaway run.
- **MacroFab / Advanced Circuits** — US assembly, but priced for production volume, and no
  open-source sponsorship angle.

## Action plan

1. **Finish rev 2.0 first.** Do not approach anyone with rev 1.5 — it doesn't work. A
   sponsorship pitch backed by a board you can demo is a different conversation than one
   backed by a board that never enumerated.
2. **Get a JLCPCB quote** for the rev 2.0 BOM/CPL at your target quantity. That's your number.
3. **Email sponsor@pcbway.com** with: OSHWA UID US002797, the GitHub repo link, what the board
   is, how many you want, and that they're being given away — not sold. Attach a render or
   photo. Ask specifically about their open-source sponsorship, not a student discount.
4. **Publish to PCBWay shared projects** regardless of whether sponsorship lands.
5. **One email to Aisler DevRel** in parallel. Costs nothing.

## Quantity note

Decide the giveaway quantity before quoting — PCBA setup cost (stencil, feeder setup)
dominates at low volume, so 30 boards often costs barely more than 10. Get quotes at 10 / 30 /
50 and pick the knee of the curve.

## Sources

- [PCBWay sponsorship platform](https://www.pcbway.com/project/sponsor/)
- [PCBWay educational / hacker sponsorship](https://www.pcbway.com/sponsor.html)
- [PCBWay shared open-source projects](https://www.pcbway.com/project/shareproject/?tag=open+source)
- [Aisler — sponsoring for open hardware projects](https://community.aisler.net/t/sponsoring-for-open-hardware-projects/3786)
- [Aisler — Exclusive Endorsement](https://aisler.net/en/exclusive_endorsement)
