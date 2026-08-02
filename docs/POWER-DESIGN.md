# Power design

The GL823K takes a single external supply. Everything else on the board is
generated inside the chip.

## Supply topology

Four nets, each with its own decoupling, and no external connection between
them.

: `+5V` : `USB1.1` to `U1.10`. The only external supply. C1 10 uF + C4 100 nF
: `VDD` : `U1.9`. Regulator output. Decouple only. C2 10 uF + C5 100 nF
: `VDDA` : `U1.13`. Regulator output feeding the USB PHY. Decouple only, keep
  the loop tight. C6 + C8 100 nF
: `VCARD` : `U1.8` to `CARD1.4`. Switched output. C3 10 uF + C7 100 nF, placed
  at the socket

## Why VDD and VDDA are not supplied externally

The datasheet lists exactly one supply. Table 5.2 gives an operating range of
+4.75 V to +5.25 V, and Table 5.3 lists one entry, `V5`. Neither VDD nor VDDA
appears anywhere in the electrical characteristics. Section 4.6 describes an
on-chip 5 V to 3.3 V band-gap regulator supplying the USB PHY and PMOS, and
section 4.7 describes on-chip power MOSFETs for memory card power.

VDD and VDDA are therefore outputs. Driving them from an external rail would
fight the internal regulator.

Confirmed on hardware, 2026-08-02. With only 5 V applied, VBUS measured at
5.17 V, the 3.3 V node reads 3.38 V, which is within the tolerance expected of a
band-gap reference. Nothing external supplies that node, so the regulator is
producing it.

The Rev 1.05 datasheet contains no typical application circuit and no
recommended decoupling values. The topology above follows from the electrical
tables; the capacitor values are engineering judgement.

## Why VDD and VDDA are not tied to each other

Decouple each separately at its own pin and run no external link between them.
This holds under either internal arrangement:

: If they are internally common, an external link is redundant and omitting it
  costs nothing
: If they are internally separate, an external link defeats that isolation and
  couples digital and card-interface switching noise into the USB 2.0 PHY rail

## Card power

`PMOS`, pin 8, is a switched current-limited output rated 200 mA. It is not a
supply rail and must drive the card only.

Bulk and high-frequency capacitance for the card sits at the socket rather than
at the controller, so card inrush is absorbed locally and does not reach VDD or
VDDA.

## Clock

No external crystal. The GL823K contains an on-chip clock source, so no 12 MHz
oscillator is required.

## LED

`R1`, 220 R, is fed from VDD, so the LED runs on 3.3 V and requires a forward
voltage at or below roughly 2.4 V. The specified part is a yellow-green AlInGaP
device at 1.7-2.4 V, giving about 5.5 mA. A pure green InGaN LED with a 3.3 V
forward voltage will not light on this rail.

The cathode returns to `U1.12`, an open-drain output. The LED indicates power
and bus activity, not card presence.

## Card detect

There is deliberately no card-detect connection. The datasheet feature list
advertises support for a non-SD-card-detect design; the controller detects cards
by polling the SD bus. Pin 11 is a general purpose I/O with an internal pull-up
and no documented card-presence function.

`CARD1.CD` and `CARD1.WP` are left unconnected with explicit no-connect markers.
`CARD1.1` is used as DAT3; that contact doubles as card detect only in SPI mode,
and this design uses 4-bit SD mode.

## Grounding

`USB1` shell tabs `MH1` and `MH2`, and SD socket shell tabs `CARD1.12` and
`CARD1.13`, are tied to GND.
