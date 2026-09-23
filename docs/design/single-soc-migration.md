# Rev.A → Rev.B：单 SoC 架构迁移

## 保留与删除

历史快照：`archive/revA/snapshot/`，基线 `dbd0d32a030bcda0427fec31894c01db29717d8a`。

| 原设计 | 新处理 |
|---|---|
| XC7A35T Local FPGA、FGG484 ball plan | 从活动设计移除；历史可追溯 |
| Local FPGA QSPI、JTAG、XO、1.0V 核心电源 | 从活动设计移除 |
| HIL-Link 双向 DDR/CRC/链路调度 | 不再是物理板间接口；模块间连接在同一 ZU2CG PL 内实现 |
| AXU2CGB J12 物理 ball/pin 信息 | 保留并核对；增加 J15；不与功能映射混写 |
| ADP5054/ADM1186 等本地 FPGA 电源树 | 不自动沿用；按新的 I/O 供电与安全需求重新设计 |
| LT3045/LT3094/LTC7149/ADR4525 电路研究 | 历史和候选 BOM 保留；不能把旧参数当成新电源验证完成 |
| AD3542R / 输出范围 / 参考 / CFB | 在共同 I/O 设计中保留候选；模拟稳定性和封装仍待审查 |
| Plant/传感器/校准/provider 边界 | 保留；ADC/DAC 类型不进入 Plant 方程 |

## 两种载板的边界

AXU2CGB 扩展板使用原版 J12/J15，电源触点全部 NC。使用经过转录的固定 SoC ball，仍需对用户手上实物版本和主机工程核对。J15 的公开手册给出 Bank25/26 组；本版本不臆造每个 ball 的独立 Bank 归属。

SoM 底板与扩展板共享逻辑契约，但**不共享未经证实的连接器 pinout**。必须在选定模块后录入厂商、版本、供电/启动要求、可用 PL I/O、Bank VCCO、时钟脚和物理映射。只有 HP/1.8V I/O 的核心板不能直接连接 3.3V 数字前端；需有实际且经过审查的转换电路，再扩展对应适配实现，不能用 CSV 别名假装转换。

## 门禁替换

- `xc7a35t_pinplan` → SUPERSEDED；替换为 `carrier_pinout_review` 和 `vivado_io_drc`。
- `hil_link_crosscheck` → SUPERSEDED；替换为 `carrier_schematic_xdc_crosscheck`。
- Rev.A ERC → SUPERSEDED；Rev.B 原生工程重新运行。
- 不用合并 PR/关闭 Issue 表示实机 PASS。

新门禁均从 NOT_RUN 开始。允许检查“未绑定 SoM 的 schema 正确”，不允许把它表述为“核心板物理兼容通过”。

## 当前原理图为何使用明确接口

原工程存在功能级符号、未冻结的电源参数和未知安全/封装细节。迁移不复制这些未完成部分并重命名为已完成电路。

新原生 KiCad 工程包含直接载板接口、完整的 8-AO DAC 电气候选以及明确的外部稳压供电/独立安全/ADC与PHY边界。它支持分阶段审阅和实验室连接规划，不授权直接打板或接入功率级。下一轮应在同一接口契约下完成板载 I/O 电源、独立 inhibit/safe-output 网络、ADC AFE 和数字 PHY，再进行硬件评审。

## 供应与安全要求

1. AXU 与 I/O 板任意上/掉电顺序，既查电源针也查信号针反灌。
2. I/O 没供电、SoC 未配置、时钟停止、模型超时，DUT 功率级保持硬件禁止。
3. WDI 必须证明实时链路取得进展，不能由无关自由运行定时器持续喂狗。
4. DAC RESET 与安全电流反馈不同：中点偏置、钳位和模拟开关安全状态按 DUT profile 定义。
5. `<1us` 和 `5ns` 为目标，分别是路径时延与时间戳分辨率，不是已测性能。
