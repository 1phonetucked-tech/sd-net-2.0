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
4. **One email to Aisler DevRel** in parallel. Costs nothing.

The canonical public home is the **GitHub repo** — that's the decided distribution channel.
PCBWay's shared-projects gallery is worth attaching to the sponsorship pitch (it's what their
program expects to see), but it isn't a second place the project lives.

## Quantity

**Target ~30 units.** PCBA setup cost (stencil, feeder setup) dominates at low volume, so 30
often costs barely more than 10 in total. Still quote 10 / 30 / 50 to confirm where the knee
actually falls for this BOM.

## Quote these two things explicitly

Both come from `REV1.5-BASELINE.md` and both move the price:

1. **13 placements, one of them through-hole.** USB1 is an AM90 right-angle USB-A male plug.
   THT is not part of standard economic SMT assembly — it's hand-soldered and billed per
   joint, and the cheapest JLCPCB tiers may decline it. Six joints, so it's small money, but
   ask up front. PCBWay handles mixed THT/SMT more willingly, which is a point in their
   favor here.
2. **The board is a shaped outline, 116.12 × 64.98 mm** — an isosceles triangle with a
   13.54 mm-radius arc across the apex and 4.85 mm fillets on the bottom two corners, not a
   rectangle. Some fabs charge for non-rectangular routing or CNC profiling beyond a simple
   outline. Confirm it's included.

   Those are the **rev 2.0** numbers, measured from `Edge.Cuts` including the arc bulges.
   `REV1.5-BASELINE.md` quotes 113.85 × 74.56 for rev 1.5: that is a vertex-only width, and
   the height includes the 12.40 × 15.40 mm tab which is the AM90's plastic housing leaking
   into the outline layer, not board material. Rev 2.0 has no such tab.

## Sources

- [PCBWay sponsorship platform](https://www.pcbway.com/project/sponsor/)
- [PCBWay educational / hacker sponsorship](https://www.pcbway.com/sponsor.html)
- [PCBWay shared open-source projects](https://www.pcbway.com/project/shareproject/?tag=open+source)
- [Aisler — sponsoring for open hardware projects](https://community.aisler.net/t/sponsoring-for-open-hardware-projects/3786)
- [Aisler — Exclusive Endorsement](https://aisler.net/en/exclusive_endorsement)
