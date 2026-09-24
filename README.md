# ServoHIL — Rev.B 单 SoC 实时 HIL 扩展板

**一颗 ZU2CG 同时承担 Plant 与实时 I/O；自研扩展板不增加第二颗 FPGA。**

ServoHIL Rev.B 面向伺服驱动器 / 关节模组的实时 Hardware-in-the-Loop 验证。当前工作重点已经从“继续扩充原理图页面”转入 **Electrical Design Verification + Hardware Safety Qualification**：先把电源、参考、输出断开和 DUT 硬件禁止链闭合，再推进 ADC / 数字 PHY 和 PCB Layout。

> **当前状态：工程可继续设计与验证，但尚未达到可生产、可打板或功能安全放行状态。**
>
> `hardware/revB/gates.json` 中 `layout_allowed=false` 保持不变。

## Rev.B 当前状态

| 项目 | 当前状态 | 说明 |
|---|---|---|
| 单 ZU2CG 架构 | ✅ 已确定 | Plant + 实时 I/O 统一在 ZU2CG；不增加第二 FPGA |
| 原生 KiCad 工程 | ✅ 13 页 | 可直接编辑，不依赖生成器重建 |
| 输入保护 / 正负电源 / 基准 | ✅ 已有实际器件 | 仍需继续关闭 EDV、启动、热与器件资格问题 |
| 电源监控 / ARM latch | ✅ 已实现 | 与新增 watchdog 资格链联动 |
| 独立 heartbeat watchdog | ✅ 已实现原生电路 | TPS3430 + 两级 heartbeat qualification + TPS3808 delayed release |
| AO hardware disconnect | ✅ 8 路已实现 | 2 × ADG5412F；DAC → DUT 无并行旁路 |
| DUT hardware permit | ✅ 板级电路已实现 | AQY212GS 常开许可触点；**不是认证 STO** |
| ADC 输入前端 | ⏳ 未完成 | 等电源 EDV / safety qualification 后推进 |
| 数字 PHY | ⏳ 未完成 | EtherCAT/CAN/encoder 等板级 PHY 尚未完整落地 |
| PCB Layout | ⛔ 未授权 | 必须先关闭 EDV、封装/BOM 和实物验证门禁 |
| 生产资格 | ⛔ 未达到 | 无实板量测、EMC/热/掉电/故障注入完整证据 |

### PR #21 当前硬件检查点

[PR #21 — independent watchdog, AO disconnect and DUT hardware permit](https://github.com/magic-alt/servoHIL/pull/21) 已把此前缺失的三类安全相关电路落到原生 KiCad：

- **13 个原生 schematic pages**
- 原有 **216 个器件连接关系保持冻结**
- 新增 **47 个物理器件**
- 新增 **168 个独立 pin assertions**
- 仅允许 **J5.1..8** 按预定方案从 DAC 直连改为经 AO disconnect 输出
- KiCad **10.0.6** 实际导出 / ERC 检查
- 当前已验证硬件检查点 `57b7747`：**144 / 144 tests PASS，0 skipped**
- 13 页原理图：**0 ERC violations**
- native pin contract、旧网络冻结、AO bypass 检查、permit contact isolation：PASS

这些自动检查只证明**源码连接关系和验证流程满足当前契约**，不代表真实硬件在电气、模拟性能、故障反应或功能安全层面已经通过。

## 直接打开当前原理图

当前硬件源文件直接保存在 Git 中：

```text
hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro
```

相关入口：

- [Rev.B 原生 KiCad 工程](hardware/kicad/revB/axu2cgb_expansion/)
- [PR #21 safety-chain 设计、证据与实测计划](docs/review/revb-safety/README.md)
- [Electrical Design Verification](docs/review/revb-edv/README.md)
- [EDV 仿真与复现说明](sim/power/README.md)
- [历史 11 页 schematic PDF（不是当前 13 页版本）](docs/review/revb-readability/schematic-review.pdf)
- [历史原理图连线整理记录](docs/review/revb-readability/README.md)

### 当前 13 页

1. 载板接口
2. 输入保护
3. 正电源
4. 负电源 / 参考
5. 电源监控
6. 状态输出
7. 外设边界
8. DAC 0–3
9. DAC 4–7
10. 模拟输出 / AO disconnect
11. 独立 heartbeat watchdog / interlock
12. DUT hardware permit
13. 顶层索引

## Hardware Safety Chain

### 1. Independent heartbeat watchdog

`50_watchdog_interlock.kicad_sch` 使用独立器件构成硬件许可链：

```text
HIL_WDI
  ↓
TPS3430 window watchdog
  ↓
heartbeat edge qualification
  ↓
TPS3808 delayed release
  ↓
RAILS_OK
  ↓
existing ARM latch
  ↓
SAFE_ENABLE
```

设计要求：

- TPS3430 使用 falling-edge heartbeat interval；
- nominal heartbeat interval = **5 ms**，当前 contract = **4…6 ms**；
- heartbeat 丢失、过快、过慢、AON/interlock/rail fault 都会使能链失效；
- fault recovery **不能自动重新启动 DUT**；
- 恢复资格后仍需要新的 `HIL_ARM` 上升沿；
- watchdog 不提供 firmware-controlled bypass。

软件 / RTL 后续必须保证 heartbeat 代表**真实 Plant / I/O deadline + 有效 host/session lease**。无条件 free-running FPGA timer 不能作为最终健康证明。

### 2. Eight-channel AO disconnect

`06_analog_outputs.kicad_sch` 使用 **2 × ADG5412F** 提供 8 路硬件断开：

```text
DAC AOx → ADG5412F → DUT_AOx → J5
                    ↑
               SAFE_ENABLE
```

关键规则：

- protected **S terminal 面向 DUT**
- **D terminal 面向 DAC**
- 所有 8 路 AO 都必须经过 disconnect switch
- 不允许 DAC → DUT 的并行直通路径
- switch enable 具有默认硬件下拉
- FF 输出目前只作为本地诊断测试点

**AO OFF = high impedance，不等于 DUT 的安全零电压。**

实际 DUT adapter 必须定义断开后的 neutral bias / safe state，并与独立 permit contact 配合使用。

### 3. DUT hardware permit

`60_dut_permit.kicad_sch` 使用 AQY212GS PhotoMOS 提供**常开、浮地的许可触点**：

```text
SAFE_ENABLE
  ↓
NPN / LED drive
  ↓
AQY212GS normally-open contact
  ↓
DUT permit input
```

当前建议接口仅作为低能量 SELV permit：

- ≤ 24 V
- ≤ 10 mA
- contact side 不连接 ServoHIL board GND / supply

它**不是电机动力切断器，不是冗余 STO，也没有功能安全认证**。实际 DUT 必须保证 open contact、线缆断开和规定范围内 leakage 都解释为 inhibited。

## Electrical Design Verification

当前 Rev.B 不应直接进入 PCB Layout。

已有 EDV 工作包括：

- native-value driven calculations
- 25-condition ngspice regression matrix
- worst-case / startup / load-transient 检查框架
- LTspice vendor-model preparation
- magnetic component screening
- MLCC candidate / derating evidence
- thermal / headroom / regulation checks
- evidence manifest / source digest / failure artifact integrity

但仍有真实设计阻塞项：

- DAC 全条件供电跨度 / 输出 headroom
- 负电源边界
- Ćuk CCM 模型适用性
- regulator vendor closed-loop model
- startup / light-load / transient
- thermal margin
- MLCC DC-bias / temperature / aging evidence
- magnetics L(I,T) / AC-core loss
- 新增 safety chain 的 AON current / thermal budget
- partial-power / backfeed
- 实板 shutdown / fault-injection evidence

因此：

```text
simulation execution PASS != electrical qualification PASS
ERC PASS != fabrication release
logic regression PASS != functional safety certification
```

`analysis.py --strict-design` 当前仍应返回 **2**。

## 原生工程验证

需要 Python 3.11+、KiCad CLI；ngspice 用于实际数值回归。

```sh
mkdir -p build/native

python tools/check_native_readability.py

kicad-cli sch export netlist \
  --format kicadxml \
  -o build/native/netlist.xml \
  hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch

python tools/check_native_readability.py \
  --normalize build/native/netlist.xml \
  --output build/native/canonical.xml

python tools/verify_native_all.py \
  build/native/canonical.xml \
  --stage supervision

python tools/check_revb_netlist.py \
  build/native/canonical.xml \
  hardware/kicad/revB/axu2cgb_expansion/expected_connections.json

python tools/check_native_safety.py \
  build/native/canonical.xml

kicad-cli sch erc \
  --format json \
  --exit-code-violations \
  -o build/native/erc.json \
  hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch

python tools/check_revb_erc.py build/native/erc.json
```

Linux / macOS：

```sh
NATIVE_NETLIST=build/native/canonical.xml \
python -m unittest discover -s tests -v
```

PowerShell：

```powershell
$env:NATIVE_NETLIST = 'build/native/canonical.xml'
python -m unittest discover -s tests -v
```

### Native-source policy

`.kicad_sch` / `.kicad_sym` / `.kicad_pro`、项目库表及本地 footprint library 是活动设计源，可直接人工编辑。

规则：

- 页内优先连续导线；
- 标准供电使用 power symbols；
- **只有真实跨页网络使用 global label**；
- 页内反馈 / 配置网络优先 local label；
- 不用同名 global/local label 混合方式掩盖零散连线；
- ordinary CI 只能读取、导出、检查原生工程，不能自动重画并覆盖 source；
- 一次性迁移 / authoring helper 只保留在 Git 历史，不属于当前活动工作流。

原始 KiCad XML 保留 sheet path；`canonical.xml` 仅作为既有断言的检查副本。归一化过程遇到不同页面的同名本地网络不会静默合并。

Safety gate 另外验证：

- 冻结已有 216 个器件及其 pin partition；
- 只允许 J5.1..8 的明确输出路径变更；
- 独立检查 47 个新增器件 / 168 个 pins；
- 检查八路 AO 无旁路；
- 检查 permit contact 两侧保持 board-independent floating network。

## 两种 ZU2CG 载板形式

| 形式 | 当前状态 |
|---|---|
| 原版 AXU2CGB + expansion board | J12/J15 接口已建立当前活动 Rev.B 工程 |
| 市售 ZU2CG SoM + carrier | 共用逻辑 I/O contract；具体厂商 / 型号 / revision 仍 UNBOUND |

两种形式是**替代关系**，不是两颗 FPGA 同时使用。

SoM 未绑定时：

- 不生成声称可制造的物理 schematic / XDC；
- 不把 HP-only 1.8 V bank 声称成 3.3 V compatible；
- 电源、启动、connector、bank voltage 和 level shifting 必须重新审查。

载板事实与逻辑分配：

```text
hardware/carriers/axu2cgb/physical_pinout.csv
hardware/carriers/axu2cgb/assignments.csv
hardware/carriers/zu2cg_som/profile.json
hardware/revB/io_contract.json
```

## 下一阶段

当前推荐顺序：

```text
Rev.B power EDV closure
        ↓
Safety-chain component / package / AON budget qualification
        ↓
Low-energy DUT adapter + watchdog / AO / permit physical acceptance
        ↓
ADC analog front-end
        ↓
Digital PHY
        ↓
Full native ERC / netlist / BOM / package review
        ↓
PCB Layout
        ↓
Prototype bring-up
        ↓
FOC HIL closed-loop acceptance
```

在开始 Layout 之前至少需要关闭：

1. ±5 V / DAC headroom 和 regulator operating margin；
2. worst-case startup / load transient / thermal；
3. MLCC / magnetics / package / footprint / lifecycle；
4. watchdog / ARM / partial-power / recovery 实测；
5. AO disconnect 的 RON、settling、charge injection、off leakage 和 fault behaviour；
6. 实际 DUT adapter 的 neutral state、permit leakage、cable removal 与 shutdown budget；
7. 新增 AON 负载与失效场景；
8. ADC / digital PHY 原理图和相应验证门禁。

## 历史资料

`tools/revb.py generate` 仍服务于 interface contract / carrier compatibility 等工具回归，输出到独立 `build/`。它生成的早期 review schematic **不是当前活动硬件源**，不能覆盖 native project。

`archive/revA/snapshot/` 保存历史双 FPGA Rev.A，不参加当前 Rev.B 构建。PR #18 对归档原理图做过可读性 / 连线修复；repository guard 冻结的是该已经审查、已经合并的 archive snapshot，而不是修复前的旧文件。

旧 FGG484 / HIL-Link 相关 release gates 为 **SUPERSEDED**，不是 PASS。

`hil_lab` 中的 AN9767 / AN706、AX7010 FPGA-Lite、Raspberry Pi IgH 等属于其他验证平台，不在 ServoHIL Rev.B PCB 本体范围。

## Release boundary

当前自动化可以证明：

- source structure 一致；
- native connectivity 满足显式 contract；
- 已知误接 mutation 能被 gate 捕获；
- ERC / regression pipeline 可复现；
- EDV 仿真与 evidence integrity 可运行。

当前自动化**不能证明**：

- 实际器件在所有 PVT 条件都满足要求；
- assembled board 不存在 backfeed / transient / thermal / EMC 问题；
- DUT 在任一单点故障下都安全；
- permit contact 达到 STO / SIL / PL 等功能安全要求；
- 当前设计已经适合 PCB fabrication。

因此在所有 release blockers 明确关闭之前：

> **Rev.B = engineering development / verification hardware, not production-qualified hardware.**
