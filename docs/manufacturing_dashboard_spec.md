# 制造业成本管控报告与可视化看板实施规范

## 1. 交付目标

本项目的第一阶段交付两个相互一致的产物：

1. **经营分析报告**：用于面试作品集展示，按“结论—证据—行动—边界”叙事，回答费用、产品成本、库存及采购中哪些异常最值得优先处理。
2. **交互式可视化看板**：用于模拟月度经营复盘和周度异常跟进，让阅读者能从总览下钻到部门、产品、仓库、供应商和项目明细。

两个产物必须共用同一组经审阅数据、稳定 query ID、指标口径和来源标签。报告可提出有证据支持的结论；看板标题保持中性、事实性，不预先声称因果。

## 2. 受众、使用场景与决策

### 主要受众

- 招聘经理、财务经理、成本会计：判断候选人是否掌握数据清洗、成本口径、差异定位和管理沟通。
- 模拟经营层：在月度经营会中判断哪些超支、库存差异、采购价差和项目风险应优先处理。
- 模拟业务部门负责人：查看本部门或责任对象的异常明细。

### 看板支持的关键决策

| 决策 | 所需证据 | 预期动作 |
|---|---|---|
| 本月应优先管控哪类费用 | 实际金额、预算金额、偏差额、偏差率、连续超支月数 | 将调查聚焦于金额重大且超预算的部门×科目 |
| 哪个产品或工单的成本偏差最大 | 标准成本、实际成本、产量、报废、材料价格/用量差异 | 区分价格端、耗用端和报废端问题 |
| 哪些仓库需要优先复盘 | 账面数、盘点数、差异数/金额、盘点覆盖率 | 输出高价值差异的盘点复核队列 |
| 哪些供应商值得议价或调整份额 | 采购单价、基准价、价差额、拒收率、交期 | 在价格、质量、交付之间做有证据的权衡 |
| 哪些项目有超支风险 | 目标成本、实际成本、完成进度、预计完工成本 | 优先复核成本消耗快于进度的项目 |

### 运营节奏

- 默认是**月度经营复盘**：显示最新已完整月，与当月预算和上月对比。
- 异常明细支持**每周跟进**：按风险金额从高到低排序。
- 数据时间粒度不足时，不伪造周趋势；用月度比较或当期排名替代。

## 3. 数据范围与标签政策

### 数据分类

| 类型 | 预期来源 | 标签 | 可用于 |
|---|---|---|---|
| 公开制造业样例 | Microsoft AdventureWorks 产品、BOM、工单、工序、采购、库存等表 | `PUBLIC_SAMPLE` | 客观描述样例中的数量、金额、差异和分布 |
| 公开能耗数据 | UCI Steel Industry Energy Consumption（若本期实际接入） | `PUBLIC_EXTERNAL` | 单独展示能耗模式，或用于校准仿真分布 |
| 规则生成数据 | 预算、盘点、项目进度、成本分摊、责任部门映射 | `SYNTHETIC` | 演示管控方法、阈值和异常工作流 |
| 映射/重构字段 | AdventureWorks 产品与场景映射为电池制造语义 | `MODELED_MAPPING` | 作品集场景叙事，不得声称是真实电池企业数据 |

### 展示要求

- 看板页脚和报告“数据与方法”中固定显示：**本项目使用公开教学样例与规则生成数据，不代表真实企业经营结果。**
- 经营金额开头标注“样例口径”或在来源侧边栏中明确 `dataClassification`。
- 应将观测值、预算/目标、预测/场景三者分开存储和编码；不得把生成的预算当成公开源数据的观测值。
- UCI 能耗数据与 AdventureWorks 不是同一家企业，除非明确实现“校准后生成”方法，不得按产品、工单或日期直接关联。
- 每个 query 的 `source.files`、`source.links`、`source.executedAt`、`query.methods` 和 `source.metricDefinitions` 必须可在源数据视图中恢复。

## 4. 指标字典

### 4.1 顶层指标

| 指标 ID | 名称 | 定义/公式 | 角色 | 方向与注意事项 |
|---|---|---|---|---|
| `m_actual_cost` | 当月实际成本 | 所选月份实际成本明细之和 | 结果 | 单独金额无好坏，需与预算和产出共同解读 |
| `m_budget_variance` | 预算偏差额 | `actual_cost - budget_cost` | 结果 | 正数为超支，负数为节约；必须显示符号 |
| `m_budget_variance_rate` | 预算偏差率 | `(actual_cost - budget_cost) / budget_cost` | 诊断 | 预算为 0 时返回 null，不返回 0% |
| `m_unit_actual_cost` | 实际单位成本 | `actual_product_cost / completed_qty` | 结果 | 仅完工数量 > 0 时计算 |
| `m_cost_variance` | 产品成本差异 | `actual_product_cost - standard_product_cost` | 诊断 | 正数表示不利偏差 |
| `m_scrap_rate` | 报废率 | `scrapped_qty / (completed_qty + scrapped_qty)` | 护栏 | 分母为 0 时为 null；显示分母产量 |
| `m_inventory_accuracy` | 账实相符率 | `matched_sku_location_count / counted_sku_location_count` | 护栏 | “相符”的数量/金额容差须写入生成方法；不以未盘点记录作分母 |
| `m_inventory_variance_value` | 库存差异金额 | `sum(abs(counted_qty - book_qty) * unit_cost)` | 诊断 | 用绝对金额表示暴露；净盘盈/盘亏另存字段 |
| `m_purchase_price_variance` | 采购价格差异 | `sum(received_qty * (actual_unit_price - baseline_unit_price))` | 诊断 | 正数为不利价差；基准价必须声明是标准价、上期价或合同价 |
| `m_rejection_rate` | 采购拒收率 | `rejected_qty / received_qty` | 护栏 | 不能使用订购数量作分母 |
| `m_project_at_risk` | 风险项目数 | 预计完工成本超目标成本，或成本消耗率超进度阈值的项目数 | 护栏 | 阈值必须作为明确的仿真规则展示 |

### 4.2 诊断指标

| 指标 ID | 名称 | 定义/公式 |
|---|---|---|
| `m_material_price_variance` | 材料价格差异 | `actual_qty * (actual_price - standard_price)`，按工单/产品汇总 |
| `m_material_usage_variance` | 材料用量差异 | `standard_price * (actual_qty - standard_qty_allowed)` |
| `m_cost_consumption_rate` | 项目成本消耗率 | `cumulative_actual_project_cost / target_project_cost` |
| `m_project_progress_gap` | 项目成本进度差 | `cost_consumption_rate - completion_rate` |
| `m_estimate_at_completion` | 预计完工成本 | 默认 `cumulative_actual_project_cost / completion_rate`；完成进度为 0 时为 null，并明确这是简化线性场景，不是统计预测 |
| `m_stocktake_coverage` | 盘点覆盖率 | `counted_sku_location_count / eligible_sku_location_count` |
| `m_supplier_score` | 供应商综合得分 | 若实现，为公开权重的仿真评分；价格 40%、质量 30%、交付 20%、账期 10% |

注：综合分数只能作为筛选器，不能替代价格、质量和交付的分项证据。若无可验证的交期或账期字段，不得生成表面精确的综合分。

## 5. reviewed snapshot 的 query 设计

下列 ID 为建议的稳定 ID。一个 query 只服务与其粒度兼容的组件，不将月度趋势、供应商排名和单据明细强行塞入同一个 query。

| Query ID | 粒度 | 必需字段 | 主要消费者 |
|---|---|---|---|
| `q_exec_monthly` | 月份 | `month, actual_cost, budget_cost, budget_variance, budget_variance_rate, completed_qty, unit_actual_cost, scrap_rate, inventory_variance_value, purchase_price_variance, data_classification` | 总览 KPI、月度趋势 |
| `q_budget_dept_account` | 月×工厂×部门×费用科目 | `month, plant, department, account, actual_cost, budget_cost, variance, variance_rate, consecutive_overrun_months, record_count, data_classification` | 预算趋势、超支排名、异常明细 |
| `q_product_cost_monthly` | 月×产品 | `month, plant, product_id, product_name, product_family, completed_qty, standard_cost_total, actual_cost_total, standard_unit_cost, actual_unit_cost, cost_variance, cost_variance_rate, scrap_qty, scrap_rate, data_classification` | 单位成本、产品差异排名 |
| `q_cost_components` | 月×产品×成本项目 | `month, plant, product_id, product_name, cost_component, standard_cost, actual_cost, variance, variance_share, data_classification` | 成本结构、差异瀑布或排名 |
| `q_work_order_variance` | 工单×物料/工序 | `month, plant, work_order_id, product_id, product_name, variance_type, standard_qty, actual_qty, standard_price, actual_price, variance_amount, scrap_qty, scrap_reason, data_classification` | 材料价格/用量差异、工单调查表 |
| `q_inventory_stocktake` | 盘点期×仓库×库位×SKU | `stocktake_date, month, warehouse, location, product_id, product_name, book_qty, counted_qty, qty_variance, unit_cost, signed_variance_value, absolute_variance_value, match_flag, counted_flag, days_since_movement, data_classification` | 账实相符率、差异排名、复核队列 |
| `q_procurement_vendor_monthly` | 月×供应商×物料 | `month, vendor_id, vendor_name, product_id, product_name, ordered_qty, received_qty, rejected_qty, actual_unit_price, baseline_unit_price, purchase_amount, price_variance, rejection_rate, average_lead_days, on_time_receipt_rate, data_classification` | 供应商价差、质量/交付散点、议价队列 |
| `q_project_monthly` | 月×项目 | `month, project_id, project_name, project_type, target_cost, cumulative_actual_cost, completion_rate, cost_consumption_rate, progress_gap, estimate_at_completion, forecast_overrun, risk_level, data_classification` | 项目风险排名、进度对比 |
| `q_project_cost_detail` | 月×项目×成本类别 | `month, project_id, project_name, cost_category, period_cost, cumulative_cost, target_cost_category, variance, data_classification` | 项目成本结构与调查明细 |
| `q_exception_queue` | 异常记录 | `as_of_date, exception_id, exception_domain, severity, entity_type, entity_id, entity_name, plant, owner_department, metric_name, actual_value, benchmark_value, variance_amount, risk_value, rule_id, evidence_query_id, data_classification` | 首页高优先级异常表 |
| `q_data_quality` | 规则×数据集 | `dataset, rule_id, rule_name, checked_rows, failed_rows, failure_rate, severity, status, notes` | 数据与方法页 |

### snapshot 元数据要求

每个 query 至少包含：

- `id`、`title`、`rows`、`source`、`methods`；
- `source.files`：工作区内的可恢复文件路径，不写不存在的 SQL；
- `source.links`：已实际阅读的官方或数据集链接；
- `source.metricDefinitions`：只绑定实际消费该指标的 `componentIds`；
- `source.executedAt`、分析期间、货币/单位、时区；
- `methods`：按执行顺序记录过滤、聚合、分摊、阈值及异常注入规则；
- 若行数过大，为看板保留有界的经审阅汇总和必要的 Top-N/异常队列，原始明细保留在可复现的 processed 文件中。

## 6. 看板信息架构

### 全局控件

- `期间`：默认最新已完整月；可切换近 3 月、近 12 月或自定义月。
- `工厂`：默认全部；仅应用于存在 `plant` 字段的 query。
- `产品系列`：默认全部；仅影响产品成本、工单和相关采购视图。
- `数据分类`：默认全部；不允许使用该控件隐藏公开样例和仿真数据的边界说明。

筛选器需与图表、KPI、来源行和导出共用同一选中总体。“全部”表示移除该维度约束，不是查找一条名为 All 的汇总行。

### Tab A：经营总览（默认页）

**目标：** 30 秒内判断本月哪些风险最值得跟进。

1. KPI 条：当月实际成本、预算偏差额/率、实际单位成本、报废率、库存差异金额、采购价差、风险项目数。KPI 只显示对当期决策最关键的 5–7 个，不为填满卡片而添加数字。
2. `c_exec_cost_budget_trend`：实际成本与预算趋势，折线，共享金额纵轴，不使用双轴。
3. `c_exec_variance_domains`：当期各领域风险金额比较，横向条形；只比较同一货币口径下的可加总暴露，比率不与金额并排。
4. `t_priority_exceptions`：高优先级异常队列，默认按 `risk_value` 降序，显示领域、对象、实际、基准、差异、严重度、数据分类和证据 query。

### Tab B：预算与产品成本

**目标：** 从“超了多少”下钻到“哪个部门/产品/成本要素贡献了偏差”。

1. `c_budget_actual_monthly`：月度预算与实际，分组柱，可筛选部门/科目。
2. `c_budget_variance_rank`：当期超支的部门×科目 Top 6，横向条形，从零开始；负向节约另分组，不用相同排名误导。
3. `c_product_unit_cost`：标准单位成本 vs 实际单位成本，产品粒度分组柱；仅展示完工数量 > 0 的产品。
4. `c_cost_component_variance`：成本要素差异的可加总桥接；只在起点标准成本 + 各项签名差异 = 实际成本能够对账时使用瀑布图，否则用差异排名条形图。
5. `t_work_order_variance`：工单异常表，支持按偏差类型、报废原因和产品过滤。

### Tab C：库存与盘点

**目标：** 识别账实差异的集中位置，并生成可执行复核清单。

1. KPI：盘点覆盖率、账实相符率、差异绝对金额、净盘盈/盘亏、长期未动金额（若字段支持）。
2. `c_inventory_variance_warehouse`：各仓库差异绝对金额，横向条形。
3. `c_inventory_variance_signed`：盘盈与盘亏金额，发散条形，显示零线和直接符号标签，不仅靠颜色。
4. `t_stocktake_review_queue`：复核队列，显示仓库、库位、SKU、账面数、盘点数、差异数、单位成本、差异金额及数据分类。

### Tab D：采购与供应商

**目标：** 在采购价差、质量和交付之间做权衡，不把“最低价”等同于“最优”。

1. KPI：采购金额、采购价差、加权拒收率、加权交付及时率（有字段时）。
2. `c_purchase_price_trend`：按物料类别的实际单价与基准单价趋势；单价用收货数量加权，不平均平均值。
3. `c_vendor_price_quality`：供应商粒度散点，x=采购价差率，y=拒收率，点大小=收货金额；工具提示显示供应商、分母收货量和期间。
4. `t_vendor_action_queue`：供应商异常表，精确展示价差、拒收、交期和采购金额。

### Tab E：项目成本

**目标：** 对比项目进度与成本消耗，提前识别目标成本风险。

1. KPI：目标成本、累计实际成本、预计完工成本、预计超支、风险项目数。
2. `c_project_progress_cost`：项目粒度分组条形，并排完成进度与成本消耗率，共享 0–100% 标尺；超过 100% 时延展同一标尺。
3. `c_project_forecast_overrun`：预计超支金额排名，横向条形。
4. `t_project_risk_queue`：项目明细表，显示目标、实际、进度、消耗率、预计完工成本、超支和风险规则。

### Tab F：数据与方法

- 数据集来源、时间范围、行数、文件指纹、许可/使用边界。
- 公开样例、外部能耗、仿真、映射字段的分类说明。
- 仿真随机种子、生成规则、异常注入规则及阈值。
- 数据质量结果表 `q_data_quality`，将未通过记录与业务异常区分。
- 指标口径、计算公式、分母与 null 规则。

## 7. 图表规范

- 金额指标按统一币种和单位展示，大数在 KPI/正文中可用 `k/M`，数据表保留可检索精度。
- 比率在轴、工具提示和卡片中都使用百分比；百分点变化写为“上升 2.3 个百分点”，不写“上升 2.3%”。
- 绝对金额条形从零开始；签名偏差图显示零线、符号和精确工具提示。
- 报告可使用“发现型”标题，但数字必须来自已复核 query；看板使用“预算与实际”等中性标题。
- 成本构成优先用 100% 堆叠条形或并排条形，不使用多切片饼图。
- 图例最多使用 5 个有意义类别；其他情况用直接标签、Top-N + “其他”或表格。仅有互斥、非负且可加总的类别才可合并“其他”。
- 视觉不仅靠红/绿：风险同时使用深浅、实心/空心、符号、标签或排序表达。
- 折线图至少显示首月和末月；不通过缩小字号解决密集标签。
- 工具提示必须包含对象名称、期间、实际值、比较值、单位，必要时显示分母。
- 窄屏时图表纵向堆叠；长表在自身容器中横向滚动，不截断列名。

## 8. 报告叙事结构

报告是一份“决策型经营分析”，不是图表画廊。在结果未经复核前，使用中性工作标题；完成分析后，将报告主标题更换为最强且不夸大的结论。

1. **标题与执行摘要**
   - 2–4 条，直接回答“哪些风险重大、为什么、建议优先做什么”。
   - 每条至少包含一个金额、比率、排名或比较证据；不把方法说明放在摘要之前。
2. **费用超支集中在哪里**
   - 月度预算 vs 实际、部门×科目偏差排名，说明累计和当月口径。
3. **产品成本偏差由什么构成**
   - 标准/实际单位成本，再展示价格、用量、加工和报废差异；只在对账成立时用“贡献”。
4. **账实差异和采购问题的可执行队列**
   - 展示差异集中度及 Top 明细；供应商建议必须同时考虑价格和质量/交付。
5. **项目成本是否早于进度消耗**
   - 项目进度 vs 成本消耗、预计完工成本，将线性外推标注为简化场景。
6. **行动建议**
   - 只提出由异常队列直接支持的下一步，例如“复核 Top 10 高价值盘点差异”。
   - 不虚构责任人、截止日期、降本金额或已实施成果。
7. **数据与方法**
   - 放在报告后部，交代来源、仿真规则、口径、局限和可复现路径。

每个报告段落用稳定 `ReportSection` ID，并仅绑定其证据所需 query：

| Report section ID | Query IDs |
|---|---|
| `r_exec_summary` | `q_exec_monthly, q_exception_queue` |
| `r_budget_findings` | `q_budget_dept_account` |
| `r_product_cost_findings` | `q_product_cost_monthly, q_cost_components, q_work_order_variance` |
| `r_inventory_procurement_findings` | `q_inventory_stocktake, q_procurement_vendor_monthly` |
| `r_project_findings` | `q_project_monthly, q_project_cost_detail` |
| `r_actions` | `q_exception_queue` |
| `r_methods` | `q_data_quality` 及各 query 的来源元数据 |

## 9. 默认视图

- 打开看板后进入“经营总览”。
- 时间选中数据中最新已完整月，趋势图显示截至该月的近 12 个可用月；不将不完整月与完整月比较。
- 工厂、产品系列、部门默认为全部。
- KPI 的比较基准优先顺序：当月预算/目标 > 上一完整月 > 无比较。每张卡片明示其比较对象。
- 异常队列只显示最新完整期的开放异常，按 `risk_value` 降序，首屏 10 条，可展开全部。
- 如某模块无数据，显示“当前筛选下无可用记录”，不显示 0 或使用样例回退值。

## 10. 验证清单

### 10.1 数据与计算

- [ ] 每个 query 的粒度与消费组件一致，不存在多对多连接造成的金额倍增。
- [ ] 所有金额的货币和单位一致；价格及单位成本使用数量加权而非简单平均。
- [ ] 月度总额 = 部门/科目加总，差异 = 实际 - 预算。
- [ ] 产品实际成本 = 各成本项目之和；瀑布图终点可与实际成本对账。
- [ ] 报废率、拒收率、账实相符率从分子/分母重新计算，不平均子组比率。
- [ ] 库存差异绝对金额与签名净差异分开，不允许盘盈和盘亏互相抵消后代表风险暴露。
- [ ] 采购价差的基准价和收货数量分母可恢复。
- [ ] 项目预计完工成本在进度为 0 时返回 null，而非无穷大或 0。
- [ ] 空值保留为空值，不静默转换为 0。
- [ ] 随机生成使用固定种子，输入参数和异常注入规则有记录，重跑产出可重现。

### 10.2 来源与叙事

- [ ] 所有“公开数据”声明都能追溯到本地文件和已阅读来源链接。
- [ ] 所有仿真指标、预算、盘点差异和项目风险都标记 `SYNTHETIC`或`MODELED_MAPPING`。
- [ ] 报告结论的数字可在对应 query 中重算，“发现”与“解释/假设”清晰分开。
- [ ] 报告不宣称数据是真实企业内部数据，不声称建议已实施或已产生降本收益。
- [ ] 不将相关性、差异分解或时间上同期出现表述为因果。

### 10.3 看板交互与视觉

- [ ] 首页默认视图无需交互即能回答本期状态、对标和优先异常。
- [ ] 从一个有数据的工厂/产品子组切回“全部”后，KPI、图表、表格、来源预览和导出使用同一总体并对账。
- [ ] 切换最新月/近 12 月时，所有受影响的卡片、比较、趋势和表格使用同一期间。
- [ ] 空选择、全 null、分母为 0 与真实测得的 0 有不同展示。
- [ ] 普通宽度与窄屏下所有实际图形可见，无裁切、文本重叠、溢出或遮挡控件。
- [ ] 检查每张图的标题、单位、图例、工具提示、排序、轴起点及首末日期。
- [ ] 超支/节约、盘盈/盘亏和风险等状态不只靠颜色区分，并通过灰度可读性检查。
- [ ] 图表图形与 reviewed rows 抽样比对；成功构建或 DOM 中存在容器不等于可视验收。
- [ ] 每个来源组件保留稳定 component ID/query ID 与单一 Copy link 行为。

### 10.4 报告验证

- [ ] 执行摘要独立可读，且不与 KPI 条、标题和第一段重复同一句话。
- [ ] 每个结论性标题都不超过证据强度，并保留会改变解读的局限。
- [ ] 每个 `ReportSection` 的 `sourceRowsByQuery` 只包含其声明的 query IDs，不把整份报告的行全部绑定进来。
- [ ] 动作建议可回指异常对象和证据，没有凭空添加责任人、时间承诺或收益预测。
- [ ] 数据来源、仿真边界、方法和指标定义可在报告末尾和来源视图中恢复，但不挤占开头的结论空间。

## 11. 实施顺序

1. 生成 processed 事实表和 `q_data_quality`，验证粒度、键和金额对账。
2. 生成 reviewed snapshot，先实现 `q_exec_monthly`、`q_budget_dept_account`、`q_product_cost_monthly`、`q_inventory_stocktake`、`q_procurement_vendor_monthly`和 `q_exception_queue`。
3. 用同一 snapshot 搭建看板“经营总览”及三个核心下钻页（预算/产品成本、库存、采购），完成第一次可视验收。
4. 在证据数字已复核后撰写报告，先写证据段，再写执行摘要和结论型标题。
5. 补充项目成本页和报告对应章节；如项目数据未生成，明确标记为未实现，不用假值占位。
6. 运行计算验证、常宽/窄宽渲染检查和主筛选器检查，修正后将 `buildStatus` 设为 `complete`。

## 12. 当前 12 张结果表的 MVP 绑定

本节优先于前文的完整态设计，用于直接构建第一版报告和看板。当前文件的 `source_class` 实际值为 `observed_sample` 与 `synthetic_scenario`；首版应保留该值，只在界面上分别显示为“公开虚构样例观测”和“仿真场景”，不必为展示而重写处理表。

| MVP Query ID | 直接来源 | 现有字段 | 首版用途 |
|---|---|---|---|
| `q_budget_execution` | `data/processed/budget_execution.csv` | `month, department, account, budget_amount, actual_amount, variance_amount, execution_rate, warning_level, source_class, source_note` | 预算 KPI、月度趋势、部门/科目超支排名 |
| `q_inventory_variance` | `data/processed/inventory_variance.csv` | `product_id, location_id, book_quantity, standard_cost, counted_quantity, count_date, quantity_variance, value_variance, is_matched, source_class, source_note` | 盘点 KPI、库位差异、SKU 复核表 |
| `q_project_forecast` | `data/processed/project_cost_forecast.csv` | `project_id, project_name, target_cost, completion_rate, actual_amount, cost_consumption_rate, estimate_at_completion, forecast_overrun, risk_level, source_class, source_note` | 项目进度对比、预计超支、风险表 |
| `q_purchase_price_variance` | `data/processed/purchase_price_variance.csv` | `purchase_order_detail_id, purchase_order_id, due_date, order_quantity, product_id, unit_price, line_total, received_quantity, rejected_quantity, stocked_quantity, standard_cost, price_variance_per_unit, purchase_price_variance, source_class, source_note` | 采购价差 KPI、物料价差排名、拒收明细 |
| `q_scrap_loss` | `data/processed/scrap_loss.csv` | `work_order_id, product_id, scrap_quantity, standard_cost, scrap_loss_amount, source_class` | 报废金额、报废工单排名 |
| `q_work_order_cost_variance` | `data/processed/work_order_cost_variance.csv` | `work_order_id, product_id, planned_cost, actual_cost, cost_variance, cost_variance_rate, source_class` | 工单成本差异 KPI和 Top-N |
| `q_expense_ledger` | `data/generated/expense_ledger.csv` | `expense_id, month, department, account, actual_amount, document_status, source_class, source_note` | 待审单据队列和预算异常追溯 |
| `q_monthly_budget` | `data/generated/monthly_budget.csv` | `month, department, account, budget_amount, source_class, source_note` | 预算底表来源检查 |
| `q_project_cost_detail` | `data/generated/project_cost.csv` | `cost_entry_id, project_id, month, cost_type, actual_amount, source_class, source_note` | 项目成本结构 |
| `q_project_master` | `data/generated/project_master.csv` | `project_id, project_name, target_cost, completion_rate, source_class, source_note` | 项目口径与主数据检查 |
| `q_stocktake_detail` | `data/generated/stocktake.csv` | `product_id, location_id, book_quantity, standard_cost, counted_quantity, count_date, source_class, source_note` | 盘点底表来源检查 |
| `q_waste_audit` | `data/generated/waste_audit.csv` | `audit_id, month, department, product_id, waste_type, quantity, standard_cost, waste_amount, root_cause, source_class, source_note` | 浪费类型/原因排名与明细 |

### MVP 必须遵守的字段边界

- 现有预算表没有 `plant`，首版的预算筛选只提供期间、部门和科目；不展示工厂筛选器。
- 现有库存表只有 `location_id`，首版称为“库位”，不在未关联 `Location.csv` 前称为仓库或工厂。
- 现有采购结果表没有 `vendor_id/vendor_name`，首版做“物料/订单价差”分析，不生成供应商排名、散点或综合得分。
- 现有工单成本结果没有日期，首版仅做全期排名，不伪造月度成本趋势。
- `purchase_price_variance` 使用 `standard_cost` 作基准；当 `standard_cost = 0` 时，单位价差不应被解读为“比标准价高 100%”，应在异常表标记“基准成本缺失/为零”并不计算偏差率。
- `inventory_variance` 中 `standard_cost = 0` 的记录可参与数量相符率，但其零金额不证明“无库存风险”；应单独显示成本未知数量。
- 当前 12 张表中只有仿真期间可形成 2026 年月度趋势；AdventureWorks 结果表的全期汇总不应与 2026 仿真数据拼成同一条时间轴。

### MVP 组件与 query 对应

| 组件 ID | Query ID |
|---|---|
| `kpi-budget-variance`, `chart-budget-monthly`, `chart-budget-dept`, `table-budget-exceptions` | `q_budget_execution` |
| `kpi-workorder-variance`, `chart-workorder-variance`, `table-workorder-exceptions` | `q_work_order_cost_variance` |
| `kpi-scrap-loss`, `chart-scrap-products` | `q_scrap_loss` |
| `chart-waste-type`, `chart-waste-root-cause`, `table-waste-audit` | `q_waste_audit` |
| `kpi-stocktake-accuracy`, `kpi-inventory-variance`, `chart-location-variance`, `table-stocktake-review` | `q_inventory_variance` |
| `kpi-purchase-ppv`, `kpi-rejection-rate`, `chart-product-ppv`, `table-purchase-exceptions` | `q_purchase_price_variance` |
| `kpi-project-risk`, `chart-project-progress-cost`, `chart-project-overrun`, `table-project-risk` | `q_project_forecast` |
| `chart-project-cost-mix` | `q_project_cost_detail` |

首版看板可将完整态的 Tab B–E 收缩为“预算与成本”、“库存与采购”、“项目成本”三个页签。等供应商、地点和产品维表关联完成后，再扩展为第 6 节的完整架构。
