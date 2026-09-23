# ZU2CG SoM carrier binding (not selected)

This is an alternative to AXU2CGB, NOT another FPGA connected to it.

The common logical contract is `hardware/revB/io_contract.json`. A native physical
project/XDC cannot be generated while this profile is UNBOUND. To bind a module:

1. Select an exact vendor/module/hardware revision and archive its interface evidence.
2. Populate a separate `physical_pinout.csv` (connector,pin,board_signal,soc_ball,
   bank_group,voltage,kind,source), with no functional net names mixed in.
3. Populate `assignments.csv` (net,connector,pin) from the common contract.
4. Record the canonical CSV SHA256, vendor power/boot contract and FPGA device.
5. Set status to BOUND_CANDIDATE, not PASS. Run the same validator and native
   netlist/ERC checks. Binding does not close hardware validation gates.

The current generator accepts only physically matching common voltage domains.
A module with only 1.8V HP pins needs actual reviewed 3.3V translation/PHY changes;
the validator deliberately rejects voltage mismatch rather than silently aliasing
it. The fixed common I/O design is reusable; the carrier power, level conversion,
connector layout and exact balls are not vendor-independent.

A purchased module is responsible for SoC BGA, DDR, boot storage and internal
core supply. The carrier must supply only the vendor-required module input(s),
not a guessed copy of the removed local-FPGA power tree.
