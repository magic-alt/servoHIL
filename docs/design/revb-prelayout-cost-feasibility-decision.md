# Rev.B Pre-Layout Cost / Feasibility Decision

> **Decision date:** 2026-09-29  
> **Scope:** personal single-axis servo / joint-module HIL before PCB Layout freeze  
> **Decision status:** **HOLD_FULL_8AO_LAYOUT — validate reduced-cost architecture first**  
> **Machine gates unchanged:** `layout_allowed=true`, `fabrication_allowed=false`, `release_allowed=false`.

This decision does not invalidate the current Rev.B schematic. The present 8-AO
AD3542R architecture remains the **full-performance reference configuration**.
However, it is no longer the recommended default population for a personal
prototype.

## 1. Why this review exists

The current costed BOM is approximately:

- one fully populated board: **CNY 4,085**
- four AD3542RBCPZ16 devices: **CNY 2,318 / board**
- AD7606C-16: **CNY 456 / board**
- two ADG5412F: **CNY 202 / board**

The four AD3542R devices alone are roughly 57% of the board component budget.
For a personal project, committing PCB Layout around mandatory eight-channel,
16-bit, 100-ns analog output before proving that all eight channels need that
latency/resolution is poor capital efficiency.

## 2. AD3542R is not technically wrong

ADI explicitly lists hardware-in-the-loop as an AD3542R application. The device
provides:

- dual channel;
- 12-bit or 16-bit variants;
- 16 MUPS fast-mode update capability;
- 100 ns large-signal settling to 0.1%;
- selectable 0–2.5 V, 0–5 V, 0–10 V, -5–+5 V and -2.5–+7.5 V ranges;
- 1.2/1.8 V compatible serial I/O.

Source:
https://www.analog.com/en/products/ad3542r.html

The current AD3542RBCPZ16 small-quantity DigiKey price is about USD 86.38 each.
The AD3542RBCPZ12-RL7 12-bit variant is about USD 45.10 each and uses the same
28-lead 4 mm x 4 mm LFCSP package family.

Sources:
https://www.digikey.com/en/products/detail/analog-devices-inc/AD3542RBCPZ16/16580691
https://www.digikey.com/en/products/detail/analog-devices-inc/AD3542RBCPZ12-RL7/16651465

The cost problem is therefore **channel count and specification level**, not an
obvious bad component choice.

## 3. Is there a direct non-ADI replacement?

There is no inexpensive, obvious pin-compatible non-ADI replacement matching the
full combination of:

- dual channel;
- 16-bit precision;
- direct bipolar output;
- approximately 100 ns settling;
- low-latency SPI;
- 1.8 V logic;
- compact package.

Functional alternatives exist, but each trades something.

### TI DAC80504 / DAC80508

DAC80504 provides four 16-bit buffered channels, 5 us settling, 0–5 V output,
1.7–5.5 V SPI and an internal reference.

Source:
https://www.ti.com/product/DAC80504

Current small-quantity DAC80504 pricing is about USD 28.76 for four channels.

This is attractive if Rev.B is narrowed to **actual DUT sensor-level unipolar
signals** rather than generic ±5 V outputs. It does not satisfy the current
1 us PWM-to-AO target.

### TI DAC81404 / DAC61404

DAC81404 is a four-channel 16-bit buffered high-voltage DAC. It directly supports
±5 V / ±10 V / ±20 V, has 1.7 V compatible SPI and an integrated reference.
Typical settling is on the order of several microseconds; for a 10 V span the
datasheet is approximately 8 us to ±2 LSB.

Sources:
https://www.ti.com/product/DAC81404
https://www.digikey.com/en/products/detail/texas-instruments/DAC81404RHBT/13562978

This is a strong functional non-ADI alternative when 8–10 us analog latency is
acceptable, but its high-voltage analog supply requirements imply a power-tree
redesign.

DAC61404 is the pin-compatible 12-bit family member.

Source:
https://www.ti.com/product/DAC61404

### TI DAC82001 / DAC8830

These are 16-bit single-channel approximately 1 us precision DACs. DAC82001 is
about USD 16.88 each at small quantity.

Sources:
https://www.ti.com/product/DAC82001
https://www.digikey.com/en/products/detail/texas-instruments/DAC82001DRXR/17394927

Four channels are substantially cheaper than the present four AD3542R devices,
but the parts are single-channel/unbuffered and require external output stages,
additional synchronization and likely digital-level adaptation. This increases
design risk and component count.

### TI DAC5672 / AD9767 class

TI DAC5672 is a dual 14-bit 275 MSPS current-output DAC and is documented by TI
as pin-compatible with AD9767. This proves that high-speed DAC alternatives are
not exclusive to ADI, but these parts use parallel digital interfaces and
current-output analog stages rather than the present AD3542R SPI / direct-voltage
architecture.

Source:
https://www.ti.com/product/DAC5672

AD9767 itself is a dual 14-bit 125 MSPS current-output device with roughly 35 ns
settling.

Source:
https://www.analog.com/en/products/ad9767.html

This class is more appropriate for a separate high-speed DAC module than as a
drop-in Rev.B replacement.

## 4. Requirement review: how many fast analog channels are really needed?

For a single-axis FOC HIL, the time-critical analog outputs are normally a subset
of:

- phase-current sensor A;
- phase-current sensor B;
- optional phase-current sensor C;
- DC-bus voltage or another fast protection/sensor channel.

Rotor position/speed should remain on the digital encoder path. Temperature,
torque, auxiliary sensors and configuration voltages generally do not require
100 ns settling.

Therefore **four fast AO channels are a better default architecture than eight**
unless a concrete DUT contract proves that >4 simultaneous sub-microsecond analog
signals are required.

The repository currently calls the provider `ad3542r_8ao_candidate`; the eight
channels have not been justified by a machine-readable minimum DUT signal set.

## 5. Cost options

Using the current Rev.B CNY planning model and current small-quantity public
prices:

| Option | Analog architecture | Estimated component BOM | Reduction vs current | Main trade-off |
|---|---|---:|---:|---|
| Full | 4 x AD3542R-16, 8 fast AO, AD7606C populated | ~CNY 4,085 | baseline | maximum capability / maximum cost |
| Same architecture, 12-bit | 4 x AD3542R-12 | ~CNY 2,977 | ~27% | lower DAC resolution, same eight channels |
| **Recommended Base-A** | **2 x AD3542R-12 = 4 fast AO; one ADG5412F; ADC retained** | **~CNY 2,270** | **~44%** | four fast AO instead of eight |
| **Recommended Base-B** | **Base-A plus AD7606C DNP for first prototype** | **~CNY 1,815** | **~56%** | no onboard 8-AI acquisition in initial build |
| Mid-speed redesign | 1 x DAC80504 + output/protection stage, 4 AO | ~CNY 1.9k–2.2k engineering estimate | ~46–54% | 5 us DAC, unipolar unless external level shift |
| Bipolar mid-speed redesign | 1 x DAC81404 + protection, 4 AO | ~CNY 2.0k class engineering estimate | ~50% | ~8 us at 10-V span; power-tree redesign |
| 1-us TI redesign | 4 x DAC82001 + buffers/protection | ~CNY 2.1k–2.4k engineering estimate | ~40–50% | more analog parts and synchronization complexity |

The redesign estimates are architecture budgets, not release BOM quotes.

## 6. Recommended implementation decision

### Decision A — do not freeze the current 8-AO full-population Layout

Keep the existing full schematic as the capability ceiling, but change the
prototype objective from “eight channels fully populated” to
**“four critical fast AO channels, optional expansion to eight.”**

Recommended PCB population strategy:

- U20/U21: populated by default;
- U22/U23: DNP by default, footprints/routing retained for later expansion;
- U601: populated for AO0..3;
- U602: DNP by default;
- AD7606C-16: optional first-spin DNP unless a defined closed-loop requirement
  needs onboard AI;
- keep the full connector/mechanical expansion path so the same PCB can later be
  upgraded without a new board spin.

### Decision B — default DAC grade should be selected by a resolution test

Start with AD3542R-12 only if its output quantization is demonstrably below the
DUT's relevant input-referred error/noise budget.

For reference:

- 12 bit over 10 V span: approximately 2.44 mV/LSB;
- 12 bit over 5 V span: approximately 1.22 mV/LSB;
- 16 bit over 10 V span: approximately 0.153 mV/LSB.

The HIL DAC range should be matched to the real sensor range instead of always
using ±5 V. If the DUT current-sense range is only 0–3.3 V or 0–5 V, a narrower
range materially improves effective resolution and may eliminate the need for a
bipolar architecture.

### Decision C — benchmark real timing before selecting a slower TI DAC

Before any PCB Layout freeze, measure:

`DUT PWM edge -> FPGA capture -> Plant result ready -> DAC output settled -> DUT ADC sample`.

Use the actual target servo controller and the intended PWM/ADC trigger scheme.

Decision thresholds:

- **available analog-settling margin > 10 us**:
  DAC80504/DAC80508-class low-cost architecture becomes viable;
- **margin 2–10 us**:
  keep AD3542R or evaluate 1-us DAC82001-class architecture;
- **margin < 2 us**:
  retain AD3542R fast-precision architecture.

This timing measurement is more valuable than selecting the DAC from headline
sample rate alone.

## 7. Pre-PCB proof path

Before spending money on the custom analog board, prove the end-to-end HIL loop
with an already available high-speed DAC module where possible:

1. capture the DUT six PWM edges on ZU2CG;
2. execute the PMSM/plant step;
3. update two fast analog current channels;
4. feed the outputs into a low-energy DUT ADC fixture;
5. measure actual PWM-to-analog and analog-to-ADC timing;
6. close the current loop at the real 20 kHz operating point;
7. then add the third current / Vbus channel as required.

A 14-bit 125 MSPS AD9767-class module is sufficient to validate the real-time
latency architecture even though it is not the final Rev.B DAC topology.

The result of this experiment determines whether the custom board needs
AD3542R-class performance or only a 5–10 us precision DAC.

## 8. Feasibility / success assessment

| Architecture | Technical feasibility | First-spin risk | Personal-project value |
|---|---|---|---|
| 8ch AD3542R-16 current Rev.B | high | medium | low-medium because cost is dominated by unused capability |
| 4ch AD3542R-12/16 selectable | **high** | **low-medium** | **high** |
| 4ch DAC80504 sensor-level | medium-high if timing margin >10 us | medium | very high if DUT is 0–5 V/unipolar |
| 4ch DAC81404 bipolar | medium-high if timing margin >10 us | medium-high | medium-high |
| 4ch DAC82001 1-us custom output stage | medium | high | medium |
| PWM / sigma-delta analog generation | high for slow auxiliary outputs | low | high for slow signals, poor for current-feedback fidelity |
| external AD9767/DAC5672 module | high for proof-of-concept | low-medium | **very high before custom PCB** |

The present Rev.B is therefore likely to work eventually, but the probability of
a cost-effective first prototype is materially improved by reducing the mandatory
high-speed analog population before Layout.

## 9. Final decision

**Recommended Rev.B personal-project baseline:**

- 4 fast AO, not 8 mandatory;
- retain expansion footprints for 8 AO;
- prefer AD3542R-12 as the first cost-down candidate, upgrade to -16 only if
  resolution testing requires it;
- make AD7606C optional for the first closed-loop prototype;
- perform end-to-end timing validation with an external high-speed DAC before
  final PCB Layout;
- only redesign around DAC80504/DAC81404 if measured DUT sample timing proves
  5–10 us DAC settling is acceptable.

This preserves the high-value part of Rev.B — FPGA plant, PWM capture, encoder
emulation, watchdog/interlock and real analog current-loop injection — while
cutting the first prototype component budget by roughly **44–56%** without
throwing away the full-capability path.

## 10. Layout hold criterion

Do not freeze the DAC/power/precision-analog placement until all three answers
are recorded:

1. required number of **fast** AO channels for the actual DUT;
2. minimum required effective DAC resolution at the actual sensor voltage range;
3. measured PWM-to-DUT-ADC timing margin.

Once those are known, the project can choose between:

- `AD3542R_FAST_4AO`;
- `LOW_COST_5US_4AO`;
- or the existing `AD3542R_FULL_8AO`.

PCB mechanical work unrelated to the DAC/power region may continue, but
precision-analog placement/routing should remain unfrozen until this decision is
closed.
