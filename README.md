# ServoHIL — Rev.B 单 SoC / 可替换载板

**当前主方案：一颗 ZU2CG 同时运行实时 Plant 与 I/O 引擎；自研 I/O 板不再放第二颗 FPGA。**

| 形态 | 当前状态 | 自研范围 |
|---|---|---|
| 原版 AXU2CGB + ServoHIL 扩展板 | 已建立 J12/J15 文档级物理映射、64 路功能分配和可重建 KiCad 审阅工程 | ADC/DAC、前端、保护、供电和安全接口 |
| 市售 ZU2CG SoM + ServoHIL 底板 | 共用 I/O 契约已定义；厂商/型号/版本未绑定，物理生成受阻 | 模块插座、供电适配和相同 HIL I/O |

不是在 AXU2CGB 上再添加一块 FPGA 核心板。两种载板形式是**替代关系**，不是两颗计算芯片同时工作；也不宣称不同核心板机械或针脚兼容。

## 本次迁移的交付边界

完成架构与工程入口迁移、两种 carrier profile、物理 pinout/功能 assignment 分离、直接接口 XDC 预览、原生 KiCad 重建、网表级检查和新验证门禁。

**生成的原理图是“直接接口 + 8 AO”的审阅/分阶段 bring-up 版本，不是生产图。** ADC/数字 PHY、独立安全模块及板载稳压电源仍以明确的集成接口表示。外部实验电源接口不是已完成的板载电源，安全接口不是安全认证电路。未完成的电路不会通过虚构 IC 符号或关闭 ERC 检查来冒充已完成。

## 新结构

```text
Purchased AXU2CGB OR purchased ZU2CG SoM
  ZU2CG PL: PWM capture / inverter / PMSM / mechanics / sensor / I/O engines
  ZU2CG PS: configuration / logging / API
             |
        carrier binding (direct peripherals, NOT HIL-Link)
             |
  common HIL I/O: DAC / reserved ADC / PWM / dual encoder / RS485 / safety
             |
       reviewed DUT adapter
```

- `hardware/revB/io_contract.json`：共用逻辑信号、电压、方向和指标目标。
- `hardware/carriers/axu2cgb/physical_pinout.csv`：原版开发板的物理事实，不含功能分配。
- `hardware/carriers/axu2cgb/assignments.csv`：本项目如何使用引脚。
- `hardware/carriers/zu2cg_som/profile.json`：未绑定的核心板适配契约。
- `hardware/revB/gates.json`：新门禁；旧门禁为 SUPERSEDED，不是 PASS。
- `tools/revb_schematic.py`：可重建的原生 KiCad 设计源，生成 `.kicad_sch/.kicad_sym`，不是图片原理图。
- `bom/revb-common.csv`：公共电路候选 BOM；载板连接器分别在 `axu2cgb-carrier.csv` 与 `zu2cg-som-carrier.csv`，不混入公共电路。
- 生成的 `generated_bom.csv` 按实际图纸逐位号列出器件与 DNP 状态；封装未冻结，不作为采购单。
- `carrier_references.json` 与 `derived_pin_map.csv` 保留 SoM 厂商连接器名称到原理图 J100+ 位号的映射，避免与公共 J1～J5 冲突。
- `revb-power-candidates.csv` 为复用候选。
- `archive/revA/snapshot/`：原双 FPGA 工程的字节级历史快照，不参与当前构建。

## 重建和验证

需要 Python 3.11+；原理图审阅/网表/ERC 需要 KiCad 9+ CLI。CI 沿用仓库的 KiCad 10 安装源并记录实际版本。

```sh
python -m unittest discover -s tests -v
python tools/revb.py validate --carrier axu2cgb
python tools/revb.py validate --carrier zu2cg_som
python tools/revb.py generate --carrier axu2cgb --output build/revB
# 打开 build/revB/servohil_io_revB.kicad_pro
kicad-cli sch export netlist --format kicadxml -o build/revB/netlist.xml build/revB/servohil_io_revB.kicad_sch
python tools/check_revb_netlist.py build/revB/netlist.xml build/revB/expected_connections.json
kicad-cli sch erc --format json --exit-code-violations -o build/revB/erc.json build/revB/servohil_io_revB.kicad_sch
python tools/check_revb_erc.py build/revB/erc.json
```

`carrier.xdc.preview` 仅包含已转录的 SoC ball 与 I/O 电平，**不包含伪造的时钟/输入输出延迟约束，不允许直接作为完整 bitstream 的时序文件。** 必须在现有 AXU2CGB host 工程中做 I/O DRC、Bank 和时序复核。

```sh
python tools/revb.py release --carrier axu2cgb       # 当前应 BLOCKED
python tools/revb.py generate --carrier zu2cg_som   # 当前应因 UNBOUND 而 BLOCKED
```

目前使用 J12 32/34、J15 32/34，共 64/68 路 I/O，保留 4 路余量。双编码器按 profile 复用，不是每种协议同时独立可用；不承诺原来的 32DI+32DO+全部总线满配。

## 不继承旧版验收

Rev.A 的 ERC、PR 合并和 Issue 状态不构成 Rev.B 的硬件证据。新版本重新验证：载板映射、电压与掉电反灌、独立安全、模拟供电、DAC 稳定性、ADC 时序、Vivado DRC/timing、ERC 和实际 FOC 闭环。

`layout_allowed` 仍为 false。`hil_lab` 的 AN9767/AN706 原型、AX7010 FPGA-Lite 和 Raspberry Pi IgH 不在本次修改范围内。

## PR #16 续作：载板兼容与独立网表检查

详见 [载板绑定与兼容验收](docs/design/carrier-compatibility-review.md)。

SoM 未选型时仍为 UNBOUND。回归中的三连接器/160-pin 核心板仅为
`SYNTHETIC_TEST_ONLY` 测试数据，不是实际厂商硬件，不会写回生产 profile。
生成器按核心板连接器数量分页，并按引脚数量选择 A3/A2/A1；不再将 SoM 图纸
标注为 AXU2CGB。实际模块供电/启动/电平适配仍需另行审查。

网表检查除逐项比对生成的 expected_connections，还独立读取所选 carrier 的物理表与
assignments，对载板触点和 DAC 接地、反馈、DNC/NC 检查，避免生成器与预期文件
同时出错时误报 PASS。`--carrier zu2cg_som --root <vendor-binding-root>` 只接受完整绑定。

CI artifact 增加实际测试提交的 `source.zip`、`source.zip.sha256` 与 `source_commit.txt`；
可在离线环境重建相同审阅工程。旧版历史快照及 Notion 同步逻辑不变。
