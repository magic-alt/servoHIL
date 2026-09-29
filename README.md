# ServoHIL — Rev.B 单 SoC 实时 HIL 扩展板

**一颗 ZU2CG 同时承担 Plant 与实时 I/O，自研扩展板不增加第二颗 FPGA。**

ServoHIL 面向伺服驱动器和关节模组的实时 Hardware-in-the-Loop 验证。
当前原生 KiCad 已从接口占位推进到电源、DAC、安全链、ADC 与数字接口器件电路；
**仍是工程开发版；原理图与物理器件绑定已达到 PCB Layout entry，但尚未获得 fabrication、采购、生产或功能安全放行。**
`hardware/revB/gates.json` 当前明确为 `layout_allowed=true`、`fabrication_allowed=false`、`release_allowed=false`。

## 当前实现与资格状态

| 模块 | 已实现 | 尚未完成 / 不能据此声称 |
|---|---|---|
| 单 ZU2CG / 原生工程 | 15 页原生 KiCad，可直接编辑；U20~U23 exact AD3542R footprint、J101/SW101/J5/J501/J701 exact physical part/footprint 与 C105 TDK exact land pattern 均已绑定；载板分配保持 64 路信号 | Vivado target part 已绑定，但 I/O DRC raw evidence、functional active XDC/top/clocks、STA/CDC 仍未关闭 fabrication/release gate |
| 输入保护 / 正负电源 / 参考 | 实际器件、原生值驱动计算与 ngspice 矩阵；XAL50xx 与已分配 TDK MLCC 的精确厂家资料入口已登记 | 原厂曲线原始字节尚未 hash-import；XAL AC/core/winding loss、启动/短路饱和、MLCC DC-bias/温度/老化/RMS/ESR、实板热与反灌门禁仍未关闭 |
| 独立 watchdog / AO disconnect / DUT permit | PR #21 的窗口 watchdog、八路 ADG5412F、常开 PhotoMOS 许可触点；J501/J701 的原理图电气语义已绑定进机械计划 | 实际 DUT 的安全偏置、漏电流、断线与最大关断时间未验收；当前两线 J501/J701 对“跨触点短路”不能天然 fail-safe，必须由真实 DUT 线监测或接口重构处理；不是 STO |
| 有效进度心跳 RTL | PR #23 已把完成的 Plant/ADC 序号与主机租约续期接入 completion-only health wrapper；超时锁存、显式恢复/重新 ARM 保留 | AXI/CDC/顶层/XDC 与实板故障注入尚未验收 |
| ADC 输入前端 | AD7606C-16、8 路低能量输入；PR #23 已实现 CONFIG 0x02 八线模式写入/读回、BUSY 流程与 8×16-bit 完成采样序号 | 模拟精度、抗混叠、校准、CDC/板级时序和实测 1 MSPS 未验收 |
| 数字 PHY / 外部保护 | 六路 PWM、双 SSI/BiSS、RS-485、AUX/I2C；在对应接口页就地加入 AI/AO/逻辑/差分线 TVS | 保护拓扑不等于 IEC ESD/浪涌 PASS；不代表任意编码器或工业 24 V 输入兼容 |
| EtherCAT / CAN | 本扩展板没有独立引脚分配或对应板载实现 | 不借用 AUX 来假装已实现；新增接口需独立分配、控制器和 PHY 审查 |
| PCB Layout / 生产资格 | `hardware/revB/layout_entry_contract.json` = `READY_FOR_PCB_LAYOUT`，允许开始 placement/routing | **仅授权 Layout**；Gerber/fabrication/采购/生产仍禁止，直到厂商曲线、真实 DUT、反灌/thermal、fixture、Vivado 与后续实板门禁关闭 |

PR #22 完成原生 ADC/PHY 电路；PR #23 完成资格门禁、AD7606C-16 初始化/采样 RTL、completion-only health 集成和 Vivado 证据导入框架。PR #27 已用 ADI Rev.C、CP-28-15 package drawing 与官方 EVAL Gerber/IPC-356/BOM 关闭 U20~U23 四个 exact land-pattern blocker，使 source-level physical blocker 从 9 降为 5。
PR #28 建立了 fail-closed qualification contract；PR #29 增加了 AXU2CGB Vivado package-pin/IOSTANDARD DRC harness。当前 Layout-entry 收尾分支进一步关闭五个机械接口与 C105 exact land pattern，并把 Layout entry 与 fabrication/release qualification 分层，避免用“必须先有实板证据”反向阻塞 PCB Layout。PR #21 的 13 页 / 144 项测试仅保留为历史检查点。

## 打开工程与查阅证据

```text
hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro
```

原生文件直接保存在 Git，无需运行生成器。
[当前 ADC/PHY 接口、负载筛查和验收说明](docs/review/revb-peripherals/README.md)
与 [安全链说明](docs/review/revb-safety/README.md) 分别记录设计和资格边界。
[EDV 使用说明](sim/power/README.md) 及
[历史 EDV 阻塞分析](docs/review/revb-edv/README.md) 保留原始背景。

当前图纸包括顶层、载板接口、输入保护、正电源、负电源/参考、电源监控、
状态输出、PWM/辅助/RS-485、两页 DAC、AO disconnect、watchdog、DUT permit、
ADC 输入前端和双编码器 PHY。`70_adc_frontend`、`80_encoder_phy` 是新增页；
`03_peripheral_boundaries` 已替换 J3/J4 预留模块接口；连接器保护器件就地放在 `03/06/50/70/80` 对应接口页，避免把 page-local 网络升级为 global label。

当前源审计统计 **439 个 `in_bom=yes && on_board=yes` 物理器件**，并明确把购买的 AXU2CGB J12/J15 载板边界排除出扩展板 BOM/placement。新增连接器保护器件 37 个。`hardware/revB/schematic_open_items.json` 现在要求 **0 个** on-board 空 footprint；J101、SW101、C105、J5、J501、J701 已全部 source-bound，U20~U23 继续绑定 `Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R`，不得回退为通用 QFN。
实际 KiCad 网表、ERC、PDF 与回归结果以当前 PR 的 `native-schematic-readability` artifact 为准。

**当前 PDF 不在历史目录中。** 最新 `native-schematic-readability` artifact 包含
原理图 PDF、原生 source ZIP、XML、ERC、测试日志与确切 source commit。
[旧 11 页 PDF](docs/review/revb-readability/schematic-review.pdf) 只作历史参考。

## Layout entry 与 fabrication qualification 状态

当前 Layout Phase 1 已建立 `hardware/revB/pcb_layout_contract.json` 与 `hardware/revB/pcb_design_rules.json`：目标为 6 层板（L2/L5 连续 GND 参考面），先闭合机械基准/板框/keepout，再进入 power/precision-analog placement、return path、routing 与 PCB DRC。AXU2CGB 官方仓库已定位并固定到 commit `43effb3dacf1f9c7e76ac801d21f14a66f14d24e` 的 STEP/DXF/机械 PDF，见 `hardware/carriers/axu2cgb/mechanical_source.json`；在从该官方 CAD 提取并复核 J12/J15、安装孔与高度 keepout 精确坐标前，不用产品照片缩放结果冻结制造尺寸。

`hardware/revB/layout_entry_contract.json` 当前状态为 `READY_FOR_PCB_LAYOUT`；`hardware/revB/prelayout_qualification_contract.json` 则转为 `LAYOUT_ENTRY_COMPLETE_FABRICATION_QUALIFICATION_OPEN`。也就是说 source-level 设计已经允许进入 placement/routing，但 fabrication/release 仍 fail-closed。
机械、电气与实测工作分别由以下文件约束：

- `hardware/revB/mechanical_binding_plan.json`：J101=Phoenix 1757242、SW101=PTS645SM43SMTR92 LFS、J5=Phoenix 1844294、J501=Phoenix 1844210、J701=Molex 43045-0212 均已绑定 exact board-side part、mating family 与本地 footprint；线束工艺、机箱集成和真实 DUT 仍属于 fabrication/release evidence；
- `hardware/revB/component_evidence_sources.json`：Coilcraft XAL50xx 与 TDK exact-MPN characterization source 已定位，但原始 bytes/曲线尚未 SHA-256 归档并导入，因此只是 provenance discovery，不是 qualification PASS；
- `hardware/revB/dut_adapter_profile.json`：仍为 `UNBOUND`，AO neutral、permit 阈值/漏电、线缆故障和最大端到端 disable time 必须来自真实 DUT/adapter 实测；
- `hardware/revB/verification_plans/`：已给出 DUT adapter、partial-power/backfeed、board thermal、low-energy fixture 与 Vivado IO/STA 的可执行验证计划，checked-in result 全部保持 `NOT_RUN`；
- `hardware/revB/vivado_input_contract.json`：AXU2CGB target 已绑定到 `xczu2cg-sfvc784-1-e` / `XCZU2CG-1SFVC784E`；现有 `carrier.xdc.preview` 仍是 review preview，不能关闭 gate，仍需 reviewed top、active XDC、clocks/generated clocks、I/O delays/CDC timing policy 和原始 Vivado reports。

特别需要保留的故障语义：当前两线 J501 dry-contact 与 J701 floating permit，
“开路→inhibit”可以作为设计意图验证，但**跨两线短路会等效于闭合触点**。本版已明确选择 `ACCEPT_NON_SAFETY_RESIDUAL_RISK` 作为 Layout 方案，因此这两个接口只能用于实验室非安全 inhibit/permit，不能声称 STO、冗余安全输出或 cable-short fail-safe；fabrication/release 前仍必须在真实 DUT/fixture 上做故障注入与关断时间验证。

本地可直接运行：

```sh
python tools/check_revb_schematic_closure.py
python tools/check_revb_prelayout_contract.py
python tools/revb_qualification.py
```

contract checker 通过现在代表“source-level Layout entry 已闭合，且 fabrication/release 阻塞项和证据边界没有漂移”；不代表任何 physical gate 已 PASS。

## ADC 与数字接口范围

### ADC：原生电路已实现，采样系统未验收

U801 为 **AD7606C-16BSTZ**，不是供电条件不同的旧 AD7606。
AVCC 接 `+5V0_DAC`，VDRIVE 接 `1V8_D`；内部参考、两路独立 REGCAP、
REFCAP 去耦、软件模式和串行模式固定脚都已画入。
J801 提供 8 路单端输入及信号地，每路正/负腿 100 Ω、差分 1 nF。
这是低能量实验室输入候选，不是承受 24 V 或长线浪涌的工业 AI 端口。

八条 DOUT 接线不等于上电后自动进入八线采样。PR #23 的 `ad7606c16_controller.sv` 已按 fail-closed 顺序完成 CONFIG 0x02 八线模式写入/读回、CONVST/BUSY 等待、八条 DOUT 的 16-bit 捕获，并只在完整捕获后推进 `sample_seq`。这仍不是模拟精度、CDC、板级时序或实测 1 MSPS 的证据。

### 编码器、PWM 与 RS-485

双编码器各有时钟和数据两个差分对，使用 THVD1450，接收器持续开启。
每对 `DE = SAFE_ENABLE AND DIR`；DIR、发送数据和 DE 都有默认下拉。
`IO0/IO2` 固定为发送数据，`IO1/IO3` 固定为接收数据；通用载板契约中的
inout 不意味着可以在本板上任意交换发送与接收。
SSI/BiSS 主端发送时钟、接收数据；从端仿真角色相反。
当前 PHY **不提供 ABZ 三对或任意四线/三线 SPI 的通用兼容承诺**。

RS-485 同样经过安全许可门控；120 Ω 终端通过跳线接入，默认不装短接帽。
六路 PWM 使用 SN74LVC541A 缓冲及输入默认下拉；AUX/I2C 为 3.3 V 逻辑接口。
这些接口非隔离，不供应编码器电源，不直接接栅极功率、电机相线或 24 V PLC 信号。接口页内就地增加的 TVS 只关闭“原理图缺少接口保护拓扑”这一项；器件到连接器的实际布局、回流路径、部分供电 backfeed 和 IEC ESD/浪涌仍需实板资格。

## 有效系统进度心跳

`rtl/revb/health_heartbeat.sv` 不是无条件自由运行计数器。
只有已完成的 Plant/I/O 事务持续推进、主机租约有效，核心才持续输出 WDI。
重复序号不续期；跳号/逆序、进度超时、租约过期或显式故障锁存禁止。
默认 100 MHz 下下降沿间隔 5 ms，Plant/I/O 截止时间 100 µs，主机租约 10 ms。
这些是可配置工程默认值，不是实板能力保证。

故障后 WDI 保持当前电平，不额外补发下降沿；ARM 被撤销。
后续恢复流量不能自动重启，必须显式重建会话，并在健康状态观察到 ARM 低电平后
再次上升。未 ARM 时仍输出健康心跳，以允许外部硬件 watchdog 完成资格判定。
**不能用未 ARM 时本就有效的 HIL_FAULT_N 反向禁止心跳，否则会形成启动死锁。**

[RTL 接口与集成边界](rtl/revb/README.md) 说明同步事务、CDC、会话和 ARM 时序。PR #23 的 `runtime_health_integration.sv` 已只接受完成的 Plant、ADC sample 与 lease renewal 序号，不把 command/request 当作完成；尚未关闭的是这些完成事件到真实 AXI/CDC/top/XDC 的物理集成、Vivado STA/IO DRC 与板测。

## 电源 EDV 与新增负载

[外设筛查](sim/peripherals/screen.py) 从实际原生器件值读取 ADC RC 和终端电阻，
复用电源最差条件计算。不能用收发器空载静态电流代表带终端负载的驱动电流。
本轮保留完整旧预算，再增加新外设压力工况和明确标注的动态储备：

| 电源 | 原预算 | 新分析预算 |
|---|---:|---:|
| `3V3_D` | 0.30 A | 0.70 A |
| `1V8_D` | 0.30 A | 0.32 A |
| `6V2_PRE` | 0.50 A | 0.55 A |
| `+5V0_DAC` | 0.20 A | 0.25 A |

这不是额定电流认证或实际功耗量测。新的预算用于重跑原有 25 工况 ngspice 和
热/磁性筛查；AON 安全链预算、同时短路、动态损耗和真实板级热仍开放。
原 DAC 电源跨度/输出裕量、真实稳压器模型及输入保护能量问题仍未关闭。XAL50xx 与已分配 TDK MLCC 的精确原厂资料入口已经登记，但曲线原始文件尚未 hash-import；C105 / `input_protected` 已绑定 TDK C5750X7R1V476M230KC，项目本地 footprint 按 TDK PA/PB/PC 推荐范围中值实现，exact land-pattern/高度的 **Layout 子门禁已关闭**。但 >=22 uF effective@15.05 V、RMS/ESR、温度/老化与实板 thermal 尚无 hash-bound/physical evidence，因此这些仍阻塞 fabrication/release，而不再阻塞 placement/routing。

ADC 外部 RC 的简化计算也不等于完整抗混叠设计或 16 位精度证明。
100 Ω 正腿和 1 MΩ 简化输入负载会引入约 100 ppm 的未校准增益误差，
必须结合内部滤波、源阻抗、校准与实板精度预算处理。

`sim/power/analysis.py --strict-design` 与外设筛查的 strict 模式都应返回 **2**：
**自动化执行通过 ≠ 电气设计合格 ≠ 制造放行。**

## 本地验证

需要 Python 3.11+、KiCad CLI、ngspice 和 Icarus Verilog。下面为 shell 命令：

```sh
mkdir -p build/native
python tools/check_revb_schematic_closure.py
python tools/check_revb_prelayout_contract.py
python tools/revb_qualification.py
python tools/check_native_readability.py
kicad-cli sch export netlist --format kicadxml -o build/native/netlist.xml hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch
python tools/check_native_readability.py --normalize build/native/netlist.xml --output build/native/canonical.xml
python tools/verify_native_all.py build/native/canonical.xml --stage supervision
python tools/check_revb_netlist.py build/native/canonical.xml hardware/kicad/revB/axu2cgb_expansion/expected_connections.json
python tools/check_native_safety.py build/native/canonical.xml
kicad-cli sch erc --format json --exit-code-violations -o build/native/erc.json hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch
python tools/check_revb_erc.py build/native/erc.json
NATIVE_NETLIST=build/native/canonical.xml python -m unittest discover -s tests -v
python sim/peripherals/screen.py --output build/peripheral-screen.json
```

PowerShell 中运行测试前设 `$env:NATIVE_NETLIST='build/native/canonical.xml'`，
再运行 `python -m unittest discover -s tests -v`。
没有原生 XML、ngspice 或 Icarus 时出现的 skipped 不能称为全量验证通过。

## 原生源码与载板边界

原生 `.kicad_sch/.kicad_sym/.kicad_pro`、库表及本地封装是活动设计源。
页内优先连续导线与标准供电符号，global label 只表达真实跨页信号。
器件值必须保留可编辑属性，不用静态文本伪装。普通 CI 只读检查和导出；
一次性绘图脚本、临时写入工作流已从活动树移除，历史实现保留在 Git。

独立检查保留原有电源/DAC/安全连接，只允许明确的 J5 AO 改接和 J3/J4 移除。
历史 XML 基准未重写；新器件由独立 pin oracle 验证。
`expected_connections.json` 本身不是独立设计正确性证据。

原版 AXU2CGB + 扩展板是当前活动实现；市售 ZU2CG SoM + 载板仍为型号未绑定的
替代方案，不是再加一颗 SoC。SoM 的电压域、供电、启动和连接器必须单独绑定。
`hardware/carriers/axu2cgb/`、`hardware/carriers/zu2cg_som/profile.json`
与 `hardware/revB/io_contract.json` 分别记录物理事实、替代方案和逻辑分配。

`tools/revb.py generate` 只用于早期接口契约/载板工具回归，输出到独立 build 目录，
不能覆盖当前原生工程。`archive/revA/snapshot/` 是历史双 FPGA 方案，原有归档冻结
不变；其 FGG484/HIL-Link 门禁为 SUPERSEDED，不是 PASS。
`hil_lab` 的 AN9767/AN706、AX7010 FPGA-Lite 和 Raspberry Pi IgH 不等于本板已实现的 PHY。

## 继续推进的顺序

原理图功能拓扑已经收口到 15 页，U20~U23 exact AD3542R footprint、五个机械接口和 C105 exact land pattern 均已关闭，native on-board blank footprint 数量为 **0**。**下一步可以正式进入 PCB Layout：先建立板框/安装孔/连接器 keepout 与层叠/规则，再做电源与模拟关键器件 placement、回流路径/地分区、敏感模拟和高速数字布线。** Layout 过程中不得删除当前 exact-part/source binding。并行继续把 Coilcraft/TDK 原厂曲线做成 hash-bound evidence；完成真实 DUT adapter、partial-power/backfeed、Vivado functional active XDC/top/clocks + STA/CDC 与低能量夹具计划。板子完成后再执行 mounted-board thermal、真实 EMC、掉电、故障注入及 FOC 闭环验收；这些项目继续阻塞 Gerber/fabrication/release，而不是阻塞开始 Layout。

**AO 断开为高阻而非安全零位；单个许可触点不是冗余 STO，元件额定值不是板级认证。
没有匹配实际硬件和 DUT 的原始实测证据，就不把生产资格或安全门禁改成 PASS。**
