# ServoHIL

**基于 Zynq UltraScale+ MPSoC 的单 SoC 实时伺服 Hardware-in-the-Loop 平台。**

ServoHIL 面向伺服驱动器、机器人关节模组与电机控制器的实时 HIL 验证。
当前活动硬件为 **Rev.B + ALINX AXU2CGB / ZU2CG**：ZU2CG 同时运行 Plant 与实时 I/O，
自研扩展板负责模拟量、PWM、编码器、RS-485、电源和独立硬件监督，不再增加第二颗 FPGA。

> **当前工程状态**
>
> - Schematic / source-level Layout entry：**已闭合**
> - PCB Layout：**允许开始**
> - Fabrication：**未放行**
> - Product / release qualification：**未放行**
>
> 机器契约：`layout_allowed=true`、`fabrication_allowed=false`、`release_allowed=false`。

---

## 1. Rev.B HIL 板架构

```text
                         ┌─────────────────────────────────────────────┐
                         │          ALINX AXU2CGB / ZU2CG            │
                         │                                             │
 Host / Test Software ──►│  PS/Linux        PL Real-Time Fabric       │
                         │                  ┌───────────────────────┐  │
                         │                  │ PMSM / mechanics Plant│  │
                         │                  │ stimulus / capture    │  │
                         │                  │ protocol engines      │  │
                         │                  │ health / lease logic  │  │
                         │                  └───────────┬───────────┘  │
                         └──────────────────────────────┼──────────────┘
                                                        │
                              J12 / 1.8 V                │ J15 / 3.3 V
                DAC + ADC high-speed digital             │ PWM / encoder / RS485 /
                                                        │ AUX / safety handshake
                                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         ServoHIL Rev.B Expansion Board                        │
│                                                                               │
│  9–15 V SELV                                                                 │
│      │                                                                        │
│      ▼                                                                        │
│  Fuse / reverse / TVS / TPS259474L eFuse                                     │
│      │                                                                        │
│      ├──► AP63201 ─► 6V2_PRE ─► LT3045 ─► +5V0_DAC                          │
│      │                         └► LT3045 ─► +5V2_PVDD                         │
│      ├──► AP63201 ─► 3V3_D                                                   │
│      ├──► AP63201 ─► 1V8_D                                                   │
│      └──► LT8330 ─► -6V2_PRE ─► LT3094 ─► -5V2_PVSS                         │
│                                  ADR4525 ─► VREF_2V5                          │
│                                                                               │
│  Analog Output                                                               │
│  ZU2CG ─► 4 × AD3542R ─► 8 × AO ─► 2 × ADG5412F ─► J5 ─► DUT              │
│                                                                               │
│  Analog Input                                                                │
│  DUT ─► J801 ─► protection + RC ─► AD7606C-16 ─► 8-lane serial ─► ZU2CG   │
│                                                                               │
│  Digital / Encoder                                                           │
│  DUT PWM ─► protection/buffer ───────────────────────────────────► ZU2CG     │
│  SSI/BiSS ⇄ THVD1450 PHY ⇄───────────────────────────────────────► ZU2CG     │
│  RS-485  ⇄ THVD1450 PHY ⇄───────────────────────────────────────► ZU2CG     │
│                                                                               │
│  Independent Supervision                                                     │
│  rail monitors + progress-qualified heartbeat + TPS3430 watchdog             │
│                  │                                                            │
│                  ├──► DAC reset / AO disconnect                              │
│                  ├──► HIL_FAULT_N / re-arm                                   │
│                  └──► AQY212GS floating DUT permit                           │
└───────────────────────────────────────────────────────────────────────────────┘
```

Rev.B 的核心目标不是做一块通用 DAQ，而是把
**`Plant → deterministic I/O → DUT → measurement → Plant`**
闭环所需的实时模拟/数字接口收敛到一块 ZU2CG 扩展板上，并对失效状态采用
fail-closed 的硬件边界。

---

## 2. 主要 I/O 能力

| 功能 | Rev.B 实现 | 备注 |
|---|---|---|
| Analog Output | 8 路，4 × AD3542RBCPZ16 | 16-bit DAC；经 ADG5412F 实现物理高阻断开 |
| Analog Input | 8 路，AD7606C-16BSTZ | 低能量实验室 ±10 V 前端候选；8-lane serial |
| PWM Capture | 6 路 | 3.3 V logic，SN74LVC541A 缓冲 |
| Encoder | 2 端口 SSI/BiSS-C | 每端口 CLK/DATA 两个差分对，THVD1450 |
| RS-485 | 1 路 | THVD1450，120 Ω 跳线终端 |
| AUX GPIO | 6 路 | 3.3 V logic |
| Management | I²C | 3.3 V |
| HIL handshake | HIL_ARM / HIL_WDI / HIL_FAULT_N | 与独立硬件 watchdog/supervision 配合 |
| DUT permit | 1 路 floating NO contact | AQY212GS；实验室非安全许可触点 |

当前扩展板**没有**板载 EtherCAT/CAN 控制器或 PHY；工业总线主站/协议验证属于其他
host/平台工作流，不应把 AUX 引脚描述成已实现 EtherCAT/CAN。

---

## 3. AXU2CGB / ZU2CG 接口

Rev.B 直接使用 AXU2CGB 的 J12/J15 扩展接口。

### J12 — 1.8 V GPIO domain

主要承载高速 ADC/DAC 数字接口：

- DAC：`SCLK`、`LDAC_N`、4 × `CS_N`、8 × `SDIO`、4 × `ALERT_N`
- ADC：8 × `DOUT`、`SCLK`、`CS_N`、`SDI`、`CONVST`、`BUSY`、`RESET`

### J15 — 3.3 V GPIO domain

主要承载外部数字/PHY 与硬件监督：

- 6 × PWM
- 2 × SSI/BiSS encoder ports
- 6 × AUX GPIO
- RS-485 TX/RX/DE
- I²C
- `HIL_ARM` / `HIL_WDI` / `HIL_FAULT_N`

完整逻辑映射见：

- `hardware/carriers/axu2cgb/physical_pinout.csv`
- `hardware/carriers/axu2cgb/assignments.csv`
- `hardware/revB/io_contract.json`

官方 ALINX DXF 已绑定：

- AXU2CGB outline：**100 × 85 mm**
- 4 个主安装孔及孔径
- J12/J15 2×20 / 2.54 mm pin grid
- J12/J15 几何中心
- 两个连接器的 pin-1 方向

仍未冻结：**AXU2CGB host connector MPN、mating connector MPN、mated stack height 和
carrier height keepout**。因此在这些机械事实闭合前，不使用通用 2×20 footprint
伪造可制造的 mating PCB。

---

## 4. 电源与模拟架构

Rev.B 接受 **9–15 V regulated SELV**，不是电机 48/67 V DC bus 输入。

### 输入保护

```text
J101
  │
  ▼
F101 2 A
  │
SS34 reverse-polarity protection
  │
SMBJ16A TVS
  │
TPS259474L eFuse
  │
VIN_PROT
```

关键设计计算：

- eFuse current limit：约 **1.51 A**
- UV：约 **7.95 V**
- OV：约 **15.91 V**

### 正电源

三路 AP63201：

| Rail | Nominal |
|---|---:|
| `6V2_PRE` | 6.184 V |
| `3V3_D` | 3.296 V |
| `1V8_D` | 1.792 V |

`6V2_PRE` 再经两路 LT3045 生成：

- `+5V0_DAC`
- `+5V2_PVDD`

### 负电源与参考

- LT8330 Cuk/inverting preregulator：约 `-6.24 V`
- LT3094：`-5V2_PVSS`
- ADR4525：`VREF_2V5`

当前 EDV 仍保留 DAC supply-span/headroom corner 问题；Layout 可以继续，
但 rail tolerance、DAC stability、MLCC derating、磁性损耗和实板 thermal
仍属于 fabrication/release gate。

详细计算：

- `docs/design/native-power-stage-calculations.md`
- `docs/design/native-power-supervision.md`
- `sim/power/README.md`

---

## 5. 硬件监督与失效语义

Rev.B 的 safety/interlock 设计原则是：

**软件/RTL 停止正常推进时，硬件必须能够独立撤销输出许可。**

主要链路包括：

- TPS3808 rail supervisors
- negative-rail comparator
- explicit arm / re-arm latch
- progress-qualified `HIL_WDI`
- TPS3430 window watchdog
- DAC hardware reset
- 2 × ADG5412F AO disconnect
- AQY212GS floating normally-open DUT permit

`health_heartbeat.sv` 不使用无条件 free-running heartbeat。
只有 Plant/I/O 完成序号持续推进并且 host lease 有效时才继续输出 WDI；
progress timeout、lease expiry、序号异常或显式 fault 都会撤销健康状态。

### 安全边界

以下语义必须保持明确：

- **AO disconnect = high impedance，不等于 guaranteed 0 V。**
- **J701 floating DUT permit 不是 STO。**
- J501/J701 为两线 contact 语义，跨线短路可能等效于“触点闭合”，因此
  **不是 cable-short fail-safe 或 redundant functional-safety channel**。
- Rev.B 当前定位为工程/实验室 HIL，不声明 IEC 功能安全认证。

---

## 6. 当前 Rev.B 工程状态

### 已完成

- 15 页原生 KiCad schematic topology
- 439 个 on-board physical instances
- 431 populated + 8 DNP
- native on-board blank footprint：**0**
- U20–U23 AD3542R exact CP-28-15 land pattern
- J101 / SW101 / J5 / J501 / J701 board-side exact part/footprint binding
- C105 TDK exact land pattern
- AD7606C-16 schematic + RTL initialization / eight-DOUT capture path
- PWM / SSI-BiSS / RS-485 / AUX electrical boundaries
- input/output connector protection topology
- progress-qualified heartbeat / watchdog integration framework
- source-bound electrical calculations and ngspice regression
- AXU2CGB official DXF mechanical baseline
- Rev.B complete costed BOM
- Layout-entry machine contract

### 当前 gate

| Gate | State |
|---|---|
| Schematic source closure | ✅ closed |
| Layout entry | ✅ `READY_FOR_PCB_LAYOUT` |
| PCB Layout | 🟡 active / next engineering phase |
| Fabrication | ❌ blocked |
| Product release | ❌ blocked |

机器状态源：

`hardware/revB/gates.json`

当前明确：

```text
layout_allowed      = true
fabrication_allowed = false
release_allowed     = false
```

---

## 7. PCB Layout 基线

Rev.B 目标为 **6-layer PCB**：

| Layer | Role |
|---|---|
| L1 | components + signals |
| L2 | continuous GND reference |
| L3 | power distribution + slow signals |
| L4 | signals |
| L5 | continuous GND reference |
| L6 | components + signals |

设计原则：

- 不硬切 AGND/DGND；使用连续 reference planes + functional zoning
- switcher hot loop 与 ADC/DAC/reference 空间隔离
- 高速/精密信号不得跨 reference-plane void
- 每次高速换层附近设置 GND stitching via
- ESD/TVS 紧邻 connector，回流路径最短
- ADC/DAC digital bus 保持短、少 stub、少 layer transition
- 120 Ω differential 目前是目标阻抗，不在厂商 stackup 前冻结 width/gap

Layout 顺序：

```text
mechanical reference / board outline / connector keepout
    ↓
stackup + design rules
    ↓
power + precision analog placement
    ↓
ground / return-path review
    ↓
routing
    ↓
PCB DRC
```

详细 contract：

- `hardware/revB/pcb_layout_contract.json`
- `hardware/revB/pcb_design_rules.json`
- `docs/review/revb-layout/README.md`

---

## 8. 完整 BOM 与当前成本

Rev.B costed BOM 由原生 KiCad 反向审计，不再依赖手工简化表。

`bom/revb-costed.csv`：

- **439** 个 on-board physical refs
- **431** populated
- **8** DNP
- **139** grouped procurement lines

2026-09-29 engineering planning snapshot：

| Build | Component cost |
|---|---:|
| 1 × fully populated Rev.B | **约 ¥4,085.41** |
| 5 × fully populated Rev.B | **约 ¥17,153.21** |
| 5-board average | **约 ¥3,430.64 / board** |

以上不含：

- bare PCB
- stencil
- SMT/THT assembly
- freight / VAT / duties
- AXU2CGB
- J12/J15 mating connector stack
- rework / yield reserve

4 × AD3542R 是主要成本来源；与 AD7606C-16 合计约占单板元器件预算的
**68%** 左右，因此首板更适合采用“多做裸板、少量全贴”的 staged population。

采购状态区分：

- `EXACT_QUOTE`
- `EXACT_MPN_NO_LIVE_QUOTE`
- `CANDIDATE_QUOTE`
- `ORDERABLE_MPN_MISMATCH`
- `BUDGET_GENERIC`
- `DNP`

当前 U501 仍显式标记采购异常：
schematic 为 `TPS3430DRCR`，当前 active orderable candidate 为
`TPS3430WDRCR`；fabrication 前必须完成 variant/package/timing 审查并统一 schematic/BOM，
不能静默替换。

详细成本与采购策略：

- `bom/revb-costed.csv`
- `bom/revb-cost-summary.json`
- `bom/revb-pricing-sources.csv`
- `docs/design/revb-procurement-and-cost.md`

---

## 9. 设计文档入口

第一次接手 Rev.B，建议按以下顺序阅读：

1. **本 README** — 系统架构、工程状态和路线图
2. **`docs/design/revb-hardware-design-guide.md`** — 单一完整硬件设计说明书
3. **`hardware/carriers/axu2cgb/assignments.csv`** — ZU2CG ↔ Rev.B 信号映射
4. **`hardware/revB/io_contract.json`** — I/O 电气与逻辑契约
5. **`hardware/revB/pcb_layout_contract.json`** — PCB Layout 边界
6. **`docs/review/revb-layout/README.md`** — Layout placement/routing 规则
7. **`docs/review/revb-peripherals/README.md`** — ADC / PHY
8. **`docs/review/revb-safety/README.md`** — watchdog / interlock / DUT permit
9. **`sim/power/README.md`** — EDV / ngspice
10. **`docs/design/revb-procurement-and-cost.md`** — BOM / cost / sourcing

活动 KiCad 工程：

```text
hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro
```

原生 `.kicad_sch/.kicad_sym/.kicad_pro` 是设计源。
历史 review PDF、早期 XML 和 Rev.A snapshot 仅作为历史证据，不覆盖当前 native source。

---

## 10. Repository layout

```text
servoHIL/
├─ hardware/
│  ├─ kicad/revB/axu2cgb_expansion/   # active native Rev.B schematic / PCB source
│  ├─ revB/                            # machine-readable design/release contracts
│  └─ carriers/axu2cgb/               # carrier pinout / assignments / mechanics
├─ rtl/revb/                           # ADC / health / runtime integration RTL
├─ sim/
│  ├─ power/                           # analytical + ngspice EDV
│  └─ peripherals/                     # load / ADC frontend screening
├─ bom/                                # complete costed BOM + source ledger
├─ docs/design/                        # consolidated engineering design docs
├─ docs/review/                        # review checkpoints / evidence notes
├─ tests/                              # source / mutation / contract regressions
├─ tools/                              # repository / schematic / BOM / qualification checkers
└─ archive/revA/                       # superseded dual-FPGA historical design
```

---

## 11. 本地验证

推荐环境：

- Python 3.11+
- KiCad CLI
- ngspice
- Icarus Verilog

核心 source/contract 检查：

```sh
python tools/check_revb_schematic_closure.py
python tools/check_revb_prelayout_contract.py
python tools/check_revb_pcb_layout_contract.py
python tools/check_revb_costed_bom.py
python tools/revb_qualification.py
python -m unittest discover -s tests -v
```

原生 KiCad/ERC 路径：

```sh
mkdir -p build/native

kicad-cli sch export netlist \
  --format kicadxml \
  -o build/native/netlist.xml \
  hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch

python tools/check_native_readability.py \
  --normalize build/native/netlist.xml \
  --output build/native/canonical.xml

python tools/verify_native_all.py build/native/canonical.xml --stage supervision
python tools/check_revb_netlist.py \
  build/native/canonical.xml \
  hardware/kicad/revB/axu2cgb_expansion/expected_connections.json

python tools/check_native_safety.py build/native/canonical.xml

kicad-cli sch erc \
  --format json \
  --exit-code-violations \
  -o build/native/erc.json \
  hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch

python tools/check_revb_erc.py build/native/erc.json
```

CI 的 skipped 项只有在明确缺少对应 native tool/evidence 时才可接受；
**自动化通过不等于 electrical qualification 或 fabrication release。**

---

## 12. 下一阶段

原理图已经不再是主要工作面。当前工程优先级是：

1. **绑定 J12/J15 exact host/mating connector、stack height 与 height keepout**
2. 创建活动 `.kicad_pcb`
3. 冻结 board outline / mounting holes / connector placement / keepout
4. 绑定 PCB 厂 6-layer stackup 和真实 impedance geometry
5. power / precision-analog critical placement
6. grounding / return path review
7. routing
8. PCB DRC
9. fabrication qualification
10. 首板 bring-up + thermal / backfeed / fault injection / EMC
11. Vivado functional I/O DRC + STA/CDC
12. DUT adapter qualification
13. FOC physical closed-loop HIL acceptance

仍然阻塞 fabrication/release 的主要证据包括：

- exact J12/J15 connector stack
- MLCC DC-bias / temperature / aging / ESR / RMS
- XAL L(I,T) / AC / core / winding loss / saturation
- real DUT thresholds / leakage / cable-fault / shutdown time
- partial-power / backfeed
- mounted-board thermal
- low-energy fault-injection fixture
- Vivado raw I/O DRC + functional STA/CDC
- EMC / power-down / physical fault injection
- FOC closed-loop acceptance

---

## 13. Release philosophy

ServoHIL Rev.B 使用显式、fail-closed 的工程门禁：

- footprint 正确 ≠ electrical qualification
- ERC / DRC 通过 ≠ fabrication approval
- ngspice PASS ≠ mounted-board thermal PASS
- watchdog/interlock 电路存在 ≠ certified functional safety
- catalog rating ≠ real DUT compatibility
- prototype works ≠ release qualification

**只有与准确 source revision、实际硬件、实际 DUT 和原始测试 evidence 绑定的结果，
才允许关闭对应 release gate。**
