# ADP5054 power-stage freeze gate

This gate prevents routing a PCB around guessed switching components.

## Required inputs
- final FPGA part/package/speed grade;
- Vivado/XPE current estimates for VCCINT, VCCAUX and each VCCO bank;
- Local-FPGA utilization including 200 MHz timestamp fabric;
- DAC static/dynamic current budget;
- worst-case ambient/enclosure thermal target;
- allowed ripple and load-step deviation.

## Freeze checklist
- [ ] choose switching frequency per channel;
- [ ] choose inductor value and saturation-current margin;
- [ ] choose ceramic/bulk capacitance with DC-bias derating;
- [ ] verify compensation/stability using vendor design flow;
- [ ] verify min on/off time across 9-15 V input;
- [ ] verify startup sequencing and monotonic rise;
- [ ] verify load-step response;
- [ ] calculate loss and junction temperature;
- [ ] record final values in schematic and BOM;
- [ ] mark gate PASS before PCB placement.
