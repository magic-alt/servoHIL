# ServoHIL — Rev.B 单 SoC / 原生 KiCad 工程

**一颗 ZU2CG 同时承担 Plant 与实时 I/O；自研扩展板不增加第二颗 FPGA。**

## 直接打开当前原理图

当前硬件源文件在 Git 中，直接用 KiCad 打开，不需要运行生成器：

```text
hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro
```

- [原生工程目录](hardware/kicad/revB/axu2cgb_expansion/)
- [原理图 PDF](docs/review/revb-readability/schematic-review.pdf)
- [逐页 PNG 预览](docs/review/revb-readability/previews/)
- [本轮连线整理与独立修复记录](docs/review/revb-readability/README.md)

当前原生工程包含 11 页：载板接口、输入保护、正电源、负电源/参考、电源监控、状态输出、外设边界、两页 DAC、模拟输出和顶层索引。输入/稳压/参考/电源判定有实际器件电路；**独立心跳 watchdog、AO disconnect、完整 DUT 硬件禁止、ADC/数字 PHY 仍未完成，不能称为可生产的完整 HIL 板。**

## Electrical Design Verification

当前开发先完成电气验证，不继续扩展 ADC/PHY 或 PCB Layout。
[EDV 使用说明](sim/power/README.md) 包含原生器件驱动计算、25 工况 ngspice、
LTspice 厂商模型准备、具体磁性器件/MLCC 候选及证据校验。
[已复核结果与阻塞项](docs/review/revb-edv/README.md) 明确区分自动化通过与电气不合格：
双模拟电源全条件裕量、Cuk 模型适用性、热、降容与实测仍需关闭。
**仿真执行成功不授权布局；`--strict-design` 当前应返回 2。**

## 原理图编辑规则

`.kicad_sch/.kicad_sym/.kicad_pro`、项目库表及封装库是活动设计源，可直接人工编辑。页内优先导线与标准电源符号；仅真正跨页的信号使用 global label，页内反馈等网络使用 local label。不要用同名 global/local 混合标签消除视觉重复。

器件 Value 是原生属性，不是旁边复制的一段静态文字；修改器件值会正常反映在图纸中。`READABILITY_PROGRESS.json` 是本轮迁移历史记录，不是阻止后续人工编辑的工具。

本轮一次性编辑脚本与写仓库的临时 workflow 已完成任务并从活动树移除，Git 历史中保留。普通 CI 只读检查，不重画或覆盖原理图。

## 两种载板形式

| 形式 | 当前状态 |
|---|---|
| 原版 AXU2CGB＋扩展板 | J12 32/34、J15 32/34，64/68 GPIO；原生电源与 DAC 电路见上述工程 |
| 市售 ZU2CG SoM＋底板 | 共用 I/O 契约与绑定流程；具体厂商/型号/版本仍 UNBOUND |

两种形式是替代关系，不是两颗芯片同时工作。SoM 未绑定时禁止生成物理原理图/XDC；不能把 HP-only 的 1.8 V 引脚声明成 3.3 V 以假装兼容。模块供电、启动、连接器和电平转换必须分别审查。

载板物理事实与本项目分配分别位于：

```text
hardware/carriers/axu2cgb/physical_pinout.csv
hardware/carriers/axu2cgb/assignments.csv
hardware/carriers/zu2cg_som/profile.json
hardware/revB/io_contract.json
```

## 原生工程验证

需要 Python 3.11+ 和 KiCad CLI；当前 CI 记录实际 KiCad 版本。

```sh
mkdir -p build/native
python tools/check_native_readability.py
kicad-cli sch export netlist --format kicadxml -o build/native/netlist.xml hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch
python tools/check_native_readability.py --normalize build/native/netlist.xml --output build/native/canonical.xml
python tools/verify_native_all.py build/native/canonical.xml --stage supervision
python tools/check_revb_netlist.py build/native/canonical.xml hardware/kicad/revB/axu2cgb_expansion/expected_connections.json
kicad-cli sch erc --format json --exit-code-violations -o build/native/erc.json hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_sch
python tools/check_revb_erc.py build/native/erc.json
```

Linux/macOS 可用 `NATIVE_NETLIST=build/native/canonical.xml python -m unittest discover -s tests -v` 运行全部回归；PowerShell 先设 `$env:NATIVE_NETLIST='build/native/canonical.xml'`。

原始 XML 保留 KiCad 的页路径。`canonical.xml` 只是兼容既有断言的检查副本；归一化工具遇到不同页面同名网络会拒绝合并。真实连接等价检查直接比较原始网表的器件/数值/封装和 pin 分组，不依赖标签名称。

## 旧版生成器与历史资料

`tools/revb.py generate` 仍用于接口契约/载板兼容工具回归，输出到独立 `build/`，**它生成的早期接口审阅图不是当前活动硬件，不能覆盖上述原生工程**。正常硬件修改直接编辑原生文件。

`archive/revA/snapshot/` 保存原双 FPGA 历史，不参加当前构建。旧 FGG484/HIL-Link 门禁是 SUPERSEDED，而不是 PASS。`hil_lab` 的 AN9767/AN706、AX7010 FPGA-Lite 和 Raspberry Pi IgH 不在本次修改范围。

## 不授权打板

原生图 ERC、网表与逻辑回归通过不表示器件额定、启动、模拟稳定、热、EMC、反灌或安全实测通过。`hardware/revB/gates.json` 的 `layout_allowed` 仍为 false；未完成硬件门禁保持原状态。正常的后续电路变更须独立审查并更新相关网表基准/测试，不能跳过等价检查来隐藏误接。
