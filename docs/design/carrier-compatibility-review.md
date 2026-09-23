# PR #16 续作：单 SoC 双载板兼容审查

## 架构边界不变

一颗 ZU2CG 承担 Plant 与实时 I/O；AXU2CGB 开发板和市售 SoM 是替代载体。
自研板不增加 XC7A35T、另一块 FPGA 模块、配置 Flash、本地 FPGA JTAG/XO 或核心电源。
Rev.A 原工程只在 `archive/revA/snapshot` 保留，活动工程为 `hardware/revB`。

本轮没有新增 ADC、PHY、PMIC 或安全功能级“占位芯片”。当前图纸保留明确的外部
电源、安全、ADC 与 PHY 集成接口，不宣称这些真实电路已设计完毕。

## 两种载板现在如何共用设计

| 项目 | 原版 AXU2CGB | 市售 ZU2CG SoM |
|---|---|---|
| 物理来源 | 已转录的原版 J12/J15 | 必须选定厂商、型号、硬件版本 |
| 当前状态 | MAPPING_CANDIDATE | UNBOUND / BLOCKED_VENDOR_BINDING |
| 功能分配 | J12 32/34、J15 32/34 | 绑定后使用同一 64-net I/O 契约 |
| 原理图位号 | J12、J15 保留 | J100 起独立编号，厂商原编号另存 |
| 图纸组织 | 保留现有双接口页 | 每个连接器独立页，A3/A2/A1 自动选择 |
| 电源触点 | 全部 NC | I/O 审阅图仍为 NC；厂商供电另行设计 |
| Bank 电压 | J12 1.8 V；J15 3.3 V | 必须真实匹配；不支持用 CSV 别名冒充电平转换 |
| 公共 DAC 电路 | 复用 | 复用，不复制第二套逻辑 |
| 打板状态 | BLOCKED | BLOCKED |

`carrier_references.json` 为连接器名称与原理图位号对照；`derived_pin_map.csv`
同时给出物理 connector/pin、schematic_ref、SoC ball、HDL port、方向和电压制式。
这只是直连 I/O 预览，不是 Vivado 已验证的时序约束。

SoM 审阅模板目前支持至多 8 个连接器；图幅无法容纳时明确报错，不静默截断。
原理图连接器符号是**已购买 HOST 的电气边界模型**，不是自研板新增的计算器件。
不同模块的机械连接器、供电、启动和 pinout 不宣称兼容。

## 本轮复现并修复的问题

1. SoM 连接器叫 J1/J2/J3 时，会覆盖公共电源、安全或外设接口的位号。
   现在独立分配 J100+，并在生成器遇到重复位号时直接失败。
2. 第三个连接器或 160-pin 连接器会被画到 A3 图幅之外。
   现在分别分页及选择图幅，保留完整 pin-number 映射。
3. SoM 输出仍残留“ORIGINAL AXU2CGB”说明。
   现在显示实际绑定的 vendor/module/revision。
4. 物理表的未知 contact kind、pin 0、同 Bank 不同电压未被拦截。
   即使摘要值重新计算正确，这些不合法绑定也必须失败。
5. 旧网表检查只核对生成器自己的 expected_connections，遗漏了部分 DAC GND、
   DNC 和缺失反馈节点；两个缺失节点可能因 None == None 被视为相连。
   现在独立检查 DAC 全部已定义电源/控制/反馈网络和全部未连接脚。
6. 公共 BOM 混入 AXU2CGB 专属连接器。
   现在按 common/carrier 分离，并从实际原理图实例导出逐位号 generated_bom.csv。

## 验证分层

- 单元/变异回归：原有 22 项，加本轮 15 项；涵盖拒绝错误绑定与错误网表。
- 原 Notion verification-sync 的 15 项测试保持不变。
- AXU2CGB：真实 KiCad XML 网表、独立载板/DAC 对照、JSON ERC、PDF 导出。
- SoM：真实生产 profile 仍阻止生成；另外用明确标记的 SYNTHETIC_TEST_ONLY
  三连接器和 160-pin 测试数据运行原生 KiCad 网表/ERC/导出。
- Synthetic SoM PASS 仅证明生成与检查工具兼容不同连接器结构，**不等于某款核心板兼容通过**。
- 所有新硬件门禁保持 NOT_RUN；layout_allowed=false。没有继承 Rev.A ERC 或合并状态。

最终 exact-SHA CI 结果在 PR #16 验证评论中记录，避免在本文写入会自行失效的提交号。

## 后续仍需完成的真实电路

AXU2CGB 板版本签核、板载 I/O 电源、掉电反灌/输出使能、独立 inhibit 和模拟安全输出、
ADC/PHY、DAC CFB/负载/封装、Vivado I/O DRC/时序及 FOC 实测。SoM 另需厂商模块
资料与供电/启动/电压转换的具体电路。上述未闭合前不进入 PCB layout。
