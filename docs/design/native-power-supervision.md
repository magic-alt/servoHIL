# Native power supervision — not complete DUT safety

The power stage now uses real TPS3808G01 supervisors for1V8,3V3 and VREF,
LT3045/LT3094 PG signals, and an AON-powered TLV1701 negative-rail detector.
No interface connector is substituted for a power monitor.

TPS3808 DBV pins: RESET1 GND2 MR3 CT4 SENSE5 VDD6. CT open gives20ms nominal
release delay. Dividers32.8k/10k,67.3k/10k,49.9k/10k give thresholds1.7334V,
3.13065V,2.42595V. Outputs are open drain wired together at RAILS_OK.
Positive analog PG and independent negative sense are ANDed with INPUT_OK,
then applied to U401 MR, so analog faults also restart the release delay.

Negative detector: NEG_FOLD=.75*VREF+.25*PVSS. Compare against VREF/4.
At2.5V reference, nominal trip is near-5.0V, so missing PVSS forces fault even
if an unpowered regulator's PG output floats. The1M feedback adds hysteresis;
Schottky clamps limit startup negative/positive excursions at the comparator.
Divider/offset/leakage/hysteresis and partial-power behavior require bench review.
Reference loss is separately caught by U403; NEG_VALID alone is not a valid signal.

SN74LVC1G74 DCT latch: CLK1 D2 QN3 GND4 Q5 CLR6 PRE7 VCC8.
RAILS_OK low asynchronously clears Q. A new HIL_ARM rising edge AFTER power
qualification sets Q. Restored rails do not automatically re-arm a previously
high HIL_ARM. HIL_ARM has100k pulldown. SN74LVC1G11 output supplied from1V8_D
combines RAILS_OK,ARM_LATCH,INPUT_OK and drives DAC_RESET_N at1.8V, with10k
hardware default pulldown. Inputs tolerate the3.3V AON-domain control levels.

HIL_FAULT_N is an open-drain POWER diagnostic through SN74LVC1G07. Configure
and verify a HOST-side pull-up; no expansion-board pull-up should back-power
an unpowered host. It is not a combined certified STO/encoder/watchdog status.

HIL_WDI currently terminates at TP401 ONLY. This power-phase deliverable DOES
NOT implement missing-heartbeat detection, physical analog-output disconnect
or DUT gate-driver inhibition. TPS3431 was not inserted merely as a placeholder:
its programmable minimum interval is about63ms, not the microsecond HIL loop
loss limit. A separately specified watchdog/inhibit circuit remains required.
DAC RESET does not equal zero current or a safe analog voltage. Do not energize
DUT MOSFETs or claim physical current-loop qualification from this schematic.

Sources:
- https://www.ti.com/lit/ds/symlink/tps3808.pdf
- https://www.ti.com/lit/ds/symlink/tlv1701.pdf
- https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf
- https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf
- https://www.ti.com/lit/ds/symlink/sn74lvc1g07.pdf
- https://www.ti.com/lit/ds/symlink/tps3431.pdf
