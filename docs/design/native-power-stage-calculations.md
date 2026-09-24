# Native Rev.B power design calculations — design inputs, NOT measured results

Supply range 9–15 V regulated SELV. Fuse + SS34 series diode + TPS259474L
circuit-breaker protect VIN_PROT. This is not a 48/67V motor-bus power input.
The selected current-trip is approximately 1.51 A, not a guaranteed continuous
output current. AON is deliberately limited to 15 mA.

## Positive conversion

AP63201WU-7: internally compensated 500 kHz forced PWM, pins FB1 EN2 VIN3 GND4
SW5 BST6. EN from eFuse INPUT_OK. Three independent stages:

| Rail | R upper / lower | Nominal | L | Board load budget |
|---|---|---:|---:|---:|
| 6V2_PRE | 67.3k / 10k | 6.184 V | 10 uH | 0.50 A |
| 3V3_D | 31.2k / 10k | 3.296 V | 6.8 uH | 0.30 A |
| 1V8_D | 12.4k / 10k | 1.792 V | 4.7 uH | 0.30 A |

Vout=0.8*(1+Ru/Rl). All dividers 0.1%; reference tolerance must also be included.
Each output has 2x22uF/16V X7R in 1210; actual part/DC-bias data must show at
least 20uF combined at operating voltage/temperature. Each bootstrap is100nF.
Inductors require Isat>=3A and DCR<100mOhm; exact manufacturer MPN remains BOM
qualification, not a fabricated claim of an already purchased part.

At VIN=15V, f=450kHz (conservative design assumption), L=80% nominal,
DeltaI=Vout*(Vin-Vout)/(Vin*L*f): approximately1.01A,1.05A,0.93A respectively.
Nominal budget peak currents are0.50+1.01/2=1.005A,0.30+1.05/2=.825A,
0.30+.93/2=.765A. These calculations do not prove startup/current-limit or
transient stability, and exact switching-frequency bound must be reviewed.

LT3045 MSE pin map includes all three IN pins and both OUT pins; EP13=GND.
SET49.9k ->4.990V and52k ->5.200V at100uA. Current limit499ohm ->~300mA.
PG divider150k/10k ->4.80V;158k/10k ->5.04V. OUTS Kelvin to output capacitor.
At0.20A and0.12A loads, LDO dissipation is approximately0.239W and0.118W.
These use nominal rails and exclude quiescent current. PCB thermal validation
and effective output capacitance are still required.

## Negative conversion

LT8330ES6#TRMPBF uses a real two-inductor inverting/Cuk topology:
VIN->L301->SW_NEG->C410->NEG_X->L302->negative OUT. Diode D301 anode=NEG_X,
cathode=GND. Independent10uH inductors (not unspecified coupled pinouts);
1uF/50V transfer capacitor must tolerate VIN+|Vout| and ripple current.
FBX=-0.8V, divider1M/147k gives about-6.242V. Feedforward4.7pF follows the
vendor topology. Negative continuous design budget is0.12A. This is not the
1A switch-current specification misrepresented as1A output capability.

For VIN8–15V, abs(Vout)=6.242V, diode0.5V, f>=1.8MHz design assumption,
L>=8uH, duty=(6.242+.5)/(VIN+6.242+.5), the approximate combined-switch peak
current at0.12A output is below0.6A (efficiency and ripple must be rechecked
with the actual inductor and PCB). Vsw ideal<22V at15V input; ringing and
surge remain unqualified. LT8330's 60V switch rating is not input immunity.

LT3094 MSE EP13=IN (-6V2_PRE), NOT GND. EN tied IN, unused VIOC open.
SET52k ->-5.2V, ILIM15k ->250mA. PG158k/10k ->about-5.04V. Two22uF output
capacitors must retain at least10uF effective combined. Dissipation at0.12A
is approximately(6.242-5.2)*.12=0.125W plus quiescent current.

ADR4525BRZ SO8:VIN2 GND4 VOUT6; pin8 DNC,1/3/5/7 NIC. Source from+5V0_DAC;
VREF_2V5 feeds four DAC external reference inputs. Disable each DAC's internal
reference as required by the verified register/startup sequence; do not assume
multiple enabled internal voltage sources can be paralleled.

## DAC load and rail margin

AD3542R Rev.C specifies digital dynamic DVDD up to40mA/device at its test mode,
AVDD up to28.5mA/device; output-stage currents are load dependent and some
published quiescent figures are typical, not guaranteed maxima. Four-DAC logic
is allocated0.30A total, +5V0 allocates0.20A, PVDD/PVSS each0.12A. No50ohm
terminated output-drive capability is claimed. Additional ADC/PHY loads must
be budgeted before adding them, not silently consume reserved power.

With +/-1% SET current and0.1% SET resistance, the nominal +/-5.2V rails each
reach about5.257V; summed span~10.514V stays below the10.6V recommended DAC
span in the static calculation. Startup overshoot and regulator accuracy over
temperature must still be measured; a nominal calculation is not a rail clamp.

## Primary sources
- AP63200/1/3/5 DS41326 Rev3-2:https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf
- LT3045 RevD:https://www.analog.com/media/en/technical-documentation/data-sheets/lt3045.pdf
- LT3094 RevB:https://www.analog.com/media/en/technical-documentation/data-sheets/lt3094.pdf
- LT8330 RevD:https://www.analog.com/media/en/technical-documentation/data-sheets/lt8330.pdf
- ADR45xx RevG:https://www.analog.com/media/en/technical-documentation/data-sheets/ADR4520_4525_4530_4533_4540_4550.pdf
- AD3542R RevC:https://www.analog.com/media/en/technical-documentation/data-sheets/ad3542r.pdf

All native schematics remain NON-RELEASE until exact components, protection,
layout, transient/thermal, power-off backfeed and physical DUT safety pass review.
