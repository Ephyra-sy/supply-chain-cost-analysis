# AdventureWorks 数据来源与完整性记录

## 1. 数据集定位

- 数据集：Microsoft AdventureWorks OLTP 安装脚本随附 CSV。
- 官方仓库：[microsoft/sql-server-samples](https://github.com/microsoft/sql-server-samples)
- 官方目录：[adventure-works/oltp-install-script](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/adventure-works/oltp-install-script)
- 官方建库脚本：[instawdb.sql](https://github.com/microsoft/sql-server-samples/blob/master/samples/databases/adventure-works/oltp-install-script/instawdb.sql)
- 下载日期：2026-09-22（Asia/Shanghai）。
- 下载分支：仓库 `master` 分支的当日快照；以下 SHA-256 用于固定本项目实际使用的文件版本。

AdventureWorks 是微软用于数据库教学、演示和产品示例的**虚构企业样例数据**，不是某家真实制造企业的内部经营数据。本项目只将其用于成本、采购、生产工单和库存分析演示；报告中不得将结果表述为真实企业经营结论。

仓库许可与使用边界见微软仓库的 [LICENSE](https://github.com/microsoft/sql-server-samples/blob/master/license.txt)。

## 2. 原始文件格式

- 文件无表头。
- 字段以 Tab（`\t`）分隔；不要按逗号读取。
- 空字段表示 SQL `NULL`；数值 `0` 不是空值。
- 字段顺序依据官方 `instawdb.sql` 的建表定义恢复，并保存在 [`schema.json`](../data/raw/adventureworks/schema.json)。
- 官方 CSV 中包含部分计算列的落地值，例如 `StockedQty`、`LineTotal`、`TotalDue`。

## 3. 文件清单与校验值

每个文件的直接下载地址均为：

`https://raw.githubusercontent.com/microsoft/sql-server-samples/master/samples/databases/adventure-works/oltp-install-script/<文件名>`

| 文件 | 业务用途 | 记录数 | 字节数 | SHA-256 |
|---|---|---:|---:|---|
| `Product.csv` | 产品主数据、标准成本 | 504 | 88,536 | `df0379a7cba8b11b97ea5d104cf1313ef9f683137b6426f2fac6bb8c74c2a2ea` |
| `ProductCostHistory.csv` | 历史标准成本 | 395 | 28,978 | `afed7eb09583840258462cfbf003c4705cc4dc7a565dec50919fc1aa68f8160f` |
| `BillOfMaterials.csv` | BOM 与单位耗用 | 2,679 | 198,923 | `a27765426bd4ee19ffb62150d087de88d2a199fddb55ffad55c2479079844c71` |
| `ProductInventory.csv` | 产品—库位账面库存 | 1,069 | 81,385 | `0eb400b3a9f0abea533ca91746950ac18ec01788ace01fd1b5cfa729904c2e86` |
| `Location.csv` | 生产地点/库位维表 | 14 | 752 | `7bb94b3313fa91dcf451b5a4f43f31bc2b5061a1c9370849a0ba1234ba5a0d47` |
| `TransactionHistory.csv` | 采购、生产、销售库存流水 | 113,443 | 8,937,794 | `af17e234f9640d3b1d76e3ad46a09df2bb14eae865fea0aca7fae0822f9cd91a` |
| `WorkOrder.csv` | 工单、产量、报废量 | 72,591 | 8,239,894 | `e6618bf291defe9fa645d795b1a951ecdfc04bc88746b12b196337485b2289b1` |
| `WorkOrderRouting.csv` | 工序工时、计划与实际成本 | 67,131 | 10,598,429 | `1e15eed408d37ca355167e505b4b1e65cfabf4909f92abe54839b158453f9000` |
| `ScrapReason.csv` | 报废原因维表 | 16 | 780 | `cc0cab5472e4f94922500329286677c6209fe77114e1d6edcf713d1cf5919e8f` |
| `Vendor.csv` | 供应商主数据 | 104 | 7,161 | `075c70b53fc860bf4a562b56df027b961ac4051f0fd0b75faaa106b5dae110e3` |
| `ProductVendor.csv` | 产品—供应商报价与交期 | 460 | 40,182 | `d66c695e30deeb206f3b329a922fea905b42078ef9cbf546c421b49789bcc6fe` |
| `PurchaseOrderHeader.csv` | 采购订单头、税费和运费 | 4,012 | 516,974 | `fd3b6d356238c5adc938e427fd5c523ee9e405fba1343852dfba85a0a888113c` |
| `PurchaseOrderDetail.csv` | 采购数量、单价、收货和拒收 | 8,845 | 868,775 | `4e2e27e7a165bf1aa7e7675a7eebcb25c22a1c7bd0e2e3d7ce0f8ff53060c2d9` |
| `UnitMeasure.csv` | 计量单位维表 | 38 | 1,424 | `6e4d07534b6900f035c3b5200880a9b54190e3db63c13280e1e98788178fdeb7` |
| **合计** | 14 张表 | **271,301** | **29,609,987** | — |

## 4. 基础质量检查（2026-09-22）

检查范围为原始文件本身，不包含后续仿真预算、盘点或项目成本数据。

| 检查 | 结果 | 风险判断 |
|---|---|---|
| 文件可读性 | 14/14 文件可用 UTF-8 和 Tab 分隔读取 | 通过 |
| 字段宽度 | 271,301/271,301 行字段数与 `schema.json` 一致 | 通过 |
| 主键唯一性 | 14/14 表未发现重复主键 | 通过 |
| 产品关联 | 成本历史、BOM、库存、流水、工单、采购明细中的产品键无孤儿记录 | 通过 |
| 工单工序关联 | 67,131 条工序记录均能关联工单、产品和地点 | 通过 |
| 采购关联 | 4,012 张采购订单均能关联供应商；8,845 条采购明细均能关联订单头和产品 | 通过 |

关键外键共检查 15 组，孤儿记录均为 0。该结果说明当前快照适合构建教学型制造成本与采购库存看板；它不代表数据具有现实企业的时效性或行业代表性。

## 5. 使用注意事项

1. 原始表保留微软产品/自行车制造语义；若在展示层映射为动力电池业务，必须明确标注为“场景重构”，不得声称是原始行业字段。
2. AdventureWorks 未提供真实部门月度预算、盘点实数和工程项目成本；此类表需单独生成，并记录规则、随机种子与异常注入逻辑。
3. `TransactionType` 的官方约束值为 `W`、`S`、`P`，使用前应在指标口径中解释其业务含义。
4. 计算列既可直接读取，也应在处理层复算核对，例如 `LineTotal = OrderQty × UnitPrice`、`StockedQty = ReceivedQty - RejectedQty`。
5. 下游脚本应读取 `schema.json`，不要依赖自动猜测列名或分隔符。
