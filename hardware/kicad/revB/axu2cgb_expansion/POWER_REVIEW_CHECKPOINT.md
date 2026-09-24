# Native power schematic checkpoint

Input, positive rails, negative rail/reference, rail supervisors, latched re-arm
and host-referenced power-status circuits are physically represented.
LOW HIL_ARM immediately holds DAC_RESET_N LOW. Power fault clears the latch;
a fresh ARM edge after rail qualification is required.

Q401/Q402 replace the incomplete open-drain status interface. Status pull-up
energy comes from HOST HIL_ARM, not an expansion supply. Powered-off expansion
cannot report healthy merely because its output is floating. Transient and
partial-power behavior still require bench measurement.

OUT11/OUT12 of each LDO remain connected. One power_out and one passive duplicate
pad model the same internal output, not independent regulators shorted together.
Footprints are locally registered instead of suppressing ERC warnings.
Unassigned regulator/DAC land patterns and exact L/C MPNs remain review items.
The 47uF input ceramic uses a large2220 review footprint, not an implausible0805;
effective DC-bias capacitance must still be substantiated.

Complete HIL watchdog, AO disconnect and DUT gate inhibit are NOT implemented by
this power checkpoint. HIL_WDI terminates at TP401 only. ADC/PHY are deferred.
No board startup, surge, thermal, ripple or FOC hardware PASS is claimed.
