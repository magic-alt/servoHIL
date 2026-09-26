# ServoHIL — Rev.B 单 SoC 实时 HIL 扩展板

**一颗 ZU2CG 同时承担 Plant 与实时 I/O，自研扩展板不增加第二颗 FPGA。**

ServoHIL 面向伺服驱动器和关节模组的实时 Hardware-in-the-Loop 验证。
当前原生 KiCad 已从接口占位推进到电源、DAC、安全链、ADC 与数字接口器件电路；
**仍是工程开发版，不是可生产、可直接打板或通过功能安全认证的完整 HIL 板。**
`hardware/revB/gates.json` 的 `layout_allowed=false` 保持不变。

## 当前实现与资格状态

| 模块 | 已实现 | 尚未完成 / 不能据此声称 |
|---|---|---|
| 单 ZU2CG / 原生工程 | 15 页，可直接编辑；载板分配保持 64 路信号 | 完整板级 bitstream、Vivado STA/IO DRC 未验收 |
| 输入保护 / 正负电源 / 参考 | 实际器件、原生值驱动计算与 ngspice 矩阵 | DAC 电源跨度/输出裕量、热、厂家模型、MLCC、启动及反灌门禁未关闭 |
| 独立 watchdog / AO disconnect / DUT permit | PR #21 的窗口 watchdog、八路 ADG5412F、常开 PhotoMOS 许可触点 | 实际 DUT 的安全偏置、漏电流、断线与最大关断时间未验收；不是 STO |
| 有效进度心跳 RTL | Plant/I/O 序号、主机会话租约、超时锁存、显式恢复/重新 ARM；已增加 completion-only runtime wrapper | 真实 Plant/主机 producer、AXI/CDC、顶层与板级集成仍未完成 |
| ADC 输入前端 | AD7606C-16、8 路单端低能量输入、RC、参考/去耦、1.8 V 八数据线连接；初始化/CONFIG 回读/8-lane 采样 RTL 已实现并通过 Icarus 回归 | 通道模拟精度、抗混叠、校准、输入故障能量、1 MSPS 与实板时序仍未验收 |
| 数字 PHY | 六路 PWM 缓冲、双 SSI/BiSS 差分接口、RS-485、辅助逻辑/I2C | 不代表任意编码器或工业 24 V 输入兼容；电缆/部分供电/协议实测未验收 |
| EtherCAT / CAN | 本扩展板没有独立引脚分配或对应板载实现 | 不借用 AUX 来假装已实现；新增接口需独立分配、控制器和 PHY 审查 |
| PCB Layout / 生产资格 | 门禁与验收路径保留 | 未授权 Layout/Gerber/采购/生产，无实板、EMC 或完整故障验证证据 |

ADC/PHY 原生实现已由 [PR #22](https://github.com/magic-alt/servoHIL/pull/22) 合入。
当前资格门禁、DUT adapter contract、ADC runtime 与健康链集成在
[PR #23](https://github.com/magic-alt/servoHIL/pull/23) 继续推进。
PR #21 的 13 页 / 144 项测试仅作为历史检查点，不再冒充当前工程状态。

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
`03_peripheral_boundaries` 已替换 J3/J4 预留模块接口，避免与板载器件并接。

当前电路有 **409 个物理器件**：PR #21 的 263 个减去 2 个预留连接器，
新增 148 个 ADC/PHY/无源/连接器器件。独立外设契约检查 461 个引脚，
原有 47 个安全链器件 / 168 个引脚检查继续保留。
实际 KiCad 10.0.6 的 15 页网表、ERC、PDF 与回归检查见 PR 的原生 CI artifact。

**当前 PDF 不在历史目录中。** 最新 `native-schematic-readability` artifact 包含
原理图 PDF、原生 source ZIP、XML、ERC、测试日志与确切 source commit。
[旧 11 页 PDF](docs/review/revb-readability/schematic-review.pdf) 只作历史参考。

## ADC 与数字接口范围

### ADC：原生电路已实现，采样系统未验收

U801 为 **AD7606C-16BSTZ**，不是供电条件不同的旧 AD7606。
AVCC 接 `+5V0_DAC`，VDRIVE 接 `1V8_D`；内部参考、两路独立 REGCAP、
REFCAP 去耦、软件模式和串行模式固定脚都已画入。
J801 提供 8 路单端输入及信号地，每路正/负腿 100 Ω、差分 1 nF。
这是低能量实验室输入候选，不是承受 24 V 或长线浪涌的工业 AI 端口。

八条 DOUT 接线不等于上电后自动进入八线采样。当前
`rtl/revb/ad7606c16_controller.sv` 已实现明确的软件模式初始化：
RESET 后向 CONFIG 地址 `0x02` 写入 `0x18`（`CONFIG[4:3]=11`，
八 DOUT），随后发起寄存器读命令，并要求下一帧 DOUTA 回读 `0x18`
后才允许进入采样状态。

采样事务按 `CONVST -> BUSY 高 -> BUSY 低 -> 16 个串行时钟` 执行，
八条 DOUT 同步形成 8×16-bit 样本；只有完整捕获后才生成
`sample_valid/sample_seq`。CONFIG 回读不符或 BUSY 超时会锁存故障。
Icarus 已覆盖配置成功、CONFIG mismatch、BUSY 不响应及八通道捕获。
这些数字回归**不等于**模拟精度、校准、抗混叠、1 MSPS 或实板时序验收。

### 编码器、PWM 与 RS-485

双编码器各有时钟和数据两个差分对，使用 THVD1450，接收器持续开启。
每对 `DE = SAFE_ENABLE AND DIR`；DIR、发送数据和 DE 都有默认下拉。
`IO0/IO2` 固定为发送数据，`IO1/IO3` 固定为接收数据；通用载板契约中的
inout 不意味着可以在本板上任意交换发送与接收。
SSI/BiSS 主端发送时钟、接收数据；从端仿真角色相反。
当前 PHY **不提供 ABZ 三对或任意四线/三线 SPI 的通用兼容承诺**。

RS-485 同样经过安全许可门控；120 Ω 终端通过跳线接入，默认不装短接帽。
六路 PWM 使用 SN74LVC541A 缓冲及输入默认下拉；AUX/I2C 为 3.3 V 逻辑接口。
这些接口非隔离，不供应编码器电源，不直接接栅极功率、电机相线或 24 V PLC 信号。

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

[RTL 接口与集成边界](rtl/revb/README.md) 说明同步事务、CDC、会话和 ARM 时序。
`rtl/revb/runtime_health_integration.sv` 已把 completed Plant sequence、
completed ADC sample sequence 和 validated lease renewal sequence 接入
`health_heartbeat`，接口中没有 command/request 事件，因此提交命令不能冒充完成进度。
重复 ADC 完成序号不会刷新 I/O deadline，相关 Icarus 集成回归已通过。

真实 Plant producer、主机 lease producer、AXI/CDC adapter、顶层/XDC、Vivado STA/IO DRC
和板测仍是下一阶段工作；completion wrapper 只关闭语义接线 seam，不代替真实系统集成。

## Rev.B 资格门禁与 DUT adapter 绑定

当前分支新增三个 fail-closed 资格文件：

- `hardware/revB/dut_adapter_profile.json`：实际 DUT/adapter 的中性偏置、
  许可输入阈值、最大输入漏电、线缆开路/短路行为、最大端到端关断时间及
  原始实测证据路径。仓库默认值刻意保持 **UNBOUND/null**。
- `hardware/revB/qualification_requirements.json`：区分 analytical、
  physical 和 Vivado evidence；不会把仿真或器件额定值自动升级为板级 PASS。
- `tools/revb_qualification.py`：验证 profile 的数值一致性和证据绑定，
  缺少真实文件、阈值矛盾、线缆故障不进入 inhibited state 或任一关键门禁未 PASS
  都保持 `qualification=BLOCKED`、`layout_allowed=false`。

这套门禁的目标不是“让 CI 变绿”，而是防止未来把分析结果、catalog rating、
ERC 或模拟 fixture 误写成真实 DUT/实板资格证据。

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
原 DAC 电源跨度/输出裕量、真实稳压器模型、MLCC 偏压曲线及输入保护能量问题未关闭。
Cuk transfer 的 1 µF / 50 V / 1210 候选已从 NRND 商用品
`C3225X7R1H105K160AA` 切换为当前 Production / AEC-Q200 的
`CGA6L2X7R1H105K160AA`；但 exact-MPN DC-bias 曲线、RMS 电流和实际温升仍是 blocker。
输入保护电容 C105 仍未绑定真实 MPN，不能为了“闭环”而猜选料。

ADC 外部 RC 的简化计算也不等于完整抗混叠设计或 16 位精度证明。
100 Ω 正腿和 1 MΩ 简化输入负载会引入约 100 ppm 的未校准增益误差，
必须结合内部滤波、源阻抗、校准与实板精度预算处理。

`sim/power/analysis.py --strict-design` 与外设筛查的 strict 模式都应返回 **2**：
**自动化执行通过 ≠ 电气设计合格 ≠ 制造放行。**

## 本地验证

需要 Python 3.11+、KiCad CLI、ngspice 和 Icarus Verilog。下面为 shell 命令：

```sh
mkdir -p build/native
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
python tools/revb_qualification.py
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

当前数字侧已完成 **AD7606C-16 初始化/CONFIG 回读/8-lane capture** 和
**Plant/ADC/lease completion-only 健康链集成**，并通过真实 Icarus 回归。
下一步优先级因此调整为：

1. 继续关闭电源/热/MLCC/磁性及新增负载问题；补 exact-MPN 曲线、L(I,T)、
   AC/core loss、startup/short、板级温升等可追溯证据。
2. 用实际 DUT adapter 填写并实测中性偏置、许可输入阈值/漏电、线缆开路/短路、
   AO 高阻断开后的残余状态以及最大允许端到端关断时间。
3. 将真实 Plant producer、ADC completion 和 host lease producer 经过正式 AXI/CDC
   接入当前 runtime health seam。
4. 完成 Vivado 顶层、XDC、综合、IO DRC、CDC 与 STA，并将 source SHA、part/top、
   XDC digest、WNS/WHS 和 unconstrained path 数量绑定为可验证证据。
5. 最终原理图、完整 BOM/封装/连接器、部分供电、DUT inhibit 与低能量夹具验证
   获得工程审签后，才允许讨论 Layout。
6. 样机完成后继续真实 EMC、热、掉电、故障注入及 FOC 闭环验收。

**AO 断开为高阻而非安全零位；单个许可触点不是冗余 STO，元件额定值不是板级认证。
没有匹配实际硬件和 DUT 的原始实测证据，就不把生产资格或安全门禁改成 PASS。**
