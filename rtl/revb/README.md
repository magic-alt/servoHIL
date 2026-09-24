# Rev.B runtime health producer

`health_heartbeat.sv` is a synthesizable one-clock-domain core. It is not a board
bitstream, a Plant implementation, an AXI register file or a CDC bridge.

At **100 MHz**, default WDI falling edges are **5 ms** apart; each half-period is
2.5 ms. PLANT/IO deadlines are 100 us and host lease is 10 ms. These are explicit
engineering defaults, not proof that a particular Plant satisfies its deadlines.
Clock changes require re-deriving all parameters; never retain a 100 MHz parameter
set while using another clock. Cycle limits are integers >=2.

## Accepted transaction contract

All data/control inputs must be stable in `clk` domain. Assert reset asynchronously
if required and deassert synchronously upstream. A PS/AXI producer must transfer
sequence and valid atomically, with a proper CDC handshake if clocks differ.

`plant_valid/plant_seq` acknowledge a completed Plant step. `io_valid/io_seq`
acknowledge the completed required I/O set for a step, not merely a FIFO write,
DMA submission, DAC command request or timer interrupt. `lease_valid/lease_seq`
acknowledge a genuinely renewed host/session lease. An always-incrementing PL
counter is not an acceptable implementation of any of these sources.

The first sequence establishes the baseline. Subsequent accepted progress must
be exactly +1 modulo 2^32. An identical value is ignored and does not extend the
deadline; a jump/backward sequence faults. If a faster producer coalesces work,
place a reviewed per-accepted-transaction sequence adapter upstream; this core
does not treat arbitrary jumps as proof of progress.

A fault latches WDI at its present level and immediately withdraws `hil_arm` on
the detecting clock. There is no synthetic final falling edge. Later activity
cannot clear the fault. To start/recover, pulse `session_start` with ARM low and
runtime_fault absent; all three sources must then establish fresh progress. A
session-start during healthy tracking faults rather than refreshing deadlines.

`healthy` means *runtime sources fresh*, **not board RAILS_OK**. WDI runs while
disarmed so the external TPS3430/two-edge/TPS3808 chain can qualify. HIL_FAULT_N
is not a pre-arm heartbeat qualifier: the existing board asserts fault while
unarmed, and feeding that back would deadlock startup. `arm_request` must remain
low until the commissioning controller has allowed the hardware qualification
sequence; then issue a fresh rising edge. A premature attempt can be rejected by
the board ARM latch and requires explicit disarm/retry, not automatic toggling.
A future board integration must validate that sequence and monitor the actual
DUT permit/feedback. No RAILS_OK GPIO or host-health integration is invented here.

The core sees ARM low in a healthy session before permitting a rising edge.
ARM high through reset/recovery never arms. Dropping ARM disarms without stopping
an otherwise healthy heartbeat. The external safety chain remains authoritative;
this single-clock RTL is not redundant and does not establish STO/SIL/PL.

## Latched reason mask

| Bit | Meaning |
|---|---|
| 0 | Explicit runtime fault |
| 1 / 2 / 3 | Plant / I/O / lease deadline |
| 4 / 5 / 6 | Plant / I/O / lease sequence discontinuity |
| 7 | Invalid session start (live session, ARM high or runtime fault) |

Deadlines count clocks since the last accepted advance. Progress on the last
allowed clock refreshes the age; absent/duplicate input at that clock faults.
Faults take precedence over heartbeat toggles and ARM rises. Source counters and
latched failures cannot wrap to healthy after a long outage.

## Verification

`python -m unittest discover -s tests -p test_health_rtl.py -v` runs real Icarus
compilation and simulation. Small-cycle directed vectors cover missing/duplicate
progress, discontinuities, uint32 wrap, deadline boundaries, fault priority,
held-high ARM, deliberate recovery and healthy-disarmed feed. A second bench
runs default parameters for 11 ms at 100 MHz and checks the actual 5 ms falling
edge interval. Numerical simulation is not timing closure or hardware evidence.

Still required: reviewed PS/AXI/CDC session integration; actual Plant and I/O
completion producers; top-level/XDC binding; Vivado synthesis/STA/IO DRC; external
watchdog startup and fault injection; measured hardware disable/DUT reaction.
