import React from "react";

import { DataComponent, DataTable, EvidenceChart, MetricCard, ReportSection, RichNarrative, useDataApp } from "../../data-app-public.jsx";

const usd = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "USD", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const cny = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "CNY", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const number = (value, digits = 0) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(Number(value ?? 0));
const pct = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;

const shipmentSpec = { type: "line", x: "delivery_year", y: "line_item_value_usd", currency: "USD", valueDecimals: 0, colors: { line_item_value_usd: "var(--chart-1)" } };
const modeSpec = { type: "bar", x: "shipment mode", y: "on_time_pct", valueDecimals: 1, colors: { on_time_pct: "var(--chart-2)" } };
const energySpec = { type: "line", x: "month", y: "usage_kwh", valueDecimals: 0, colors: { usage_kwh: "var(--chart-4)" } };
const hourlySpec = { type: "line", x: "hour_label", y: "average_interval_kwh", valueDecimals: 1, colors: { average_interval_kwh: "var(--chart-5)" } };
const scenarioCostSpec = { type: "bar", x: "label", y: "total_modeled_cost_cny", currency: "CNY", valueDecimals: 0, colors: { total_modeled_cost_cny: "var(--chart-3)" } };

export function ReportContent() {
  const { appTitle, canEdit, mode, reviewedRows, setAppTitle } = useDataApp();
  const summaryRows = reviewedRows("executive_summary");
  const [summary = {}] = summaryRows;
  const years = reviewedRows("shipment_by_year");
  const modeSource = reviewedRows("shipment_by_mode");
  const modes = modeSource.map((row) => ({ ...row, on_time_pct: Number(row.on_time_rate) * 100 }));
  const energyMonthly = reviewedRows("energy_monthly");
  const energyHourly = reviewedRows("energy_hourly");
  const countries = reviewedRows("country_performance");
  const quality = reviewedRows("data_quality");
  const riskQueueRaw = reviewedRows("shipment_risk_queue");
  const riskQueue = riskQueueRaw.map((row) => {
    const rawPriority = row.priority ?? row.review_priority ?? "P3";
    return {
      ...row,
      source_shipment_id: row.source_shipment_id ?? row.id,
      project_code: row.project_code ?? row["project code"],
      po_so_number: row.po_so_number ?? row["po / so #"],
      shipment_mode: row.shipment_mode ?? row["shipment mode"],
      manufacturing_site: row.manufacturing_site ?? row["manufacturing site"],
      line_item_value_usd: row.line_item_value_usd ?? row["line item value"],
      known_freight_usd: row.known_freight_usd ?? row.freight_cost_usd_numeric,
      priority: String(rawPriority).split(/[ -]/)[0],
      evidence_summary: row.evidence_summary ?? row.rule_evidence ?? row.trigger_reasons,
      suggested_owner: row.suggested_owner ?? row.suggested_department,
    };
  });
  const lanesRaw = reviewedRows("logistics_lane_performance");
  const lanes = lanesRaw.map((row) => ({
    ...row,
    shipment_mode: row.shipment_mode ?? row["shipment mode"],
    manufacturing_site: row.manufacturing_site ?? row["manufacturing site"],
    line_item_value_usd: row.line_item_value_usd ?? row["line item value"],
    late_lines: row.late_lines ?? row.delayed_lines,
    late_rate: row.late_rate ?? row.late_delivery_rate,
  }));
  const freightStatusesRaw = reviewedRows("freight_status_summary");
  const freightStatuses = freightStatusesRaw.map((row) => ({
    ...row,
    line_item_value_usd: row.line_item_value_usd ?? null,
    share: row.share ?? (Number(row.shipment_lines) / Number(summaryRows[0]?.shipment_lines || 1)),
  }));
  const scenarioAssumptions = reviewedRows("energy_scenario_assumptions");
  const scenariosRaw = reviewedRows("energy_scenario_summary");
  const baselineScenarioCost = Number(scenariosRaw.find((row) => (row.label ?? row.scenario) === "基准情景")?.total_modeled_cost_cny
    ?? scenariosRaw.find((row) => (row.label ?? row.scenario) === "基准情景")?.modeled_total_cost_cny ?? 0);
  const scenarios = scenariosRaw.map((row) => ({
    ...row,
    label: row.label ?? row.scenario,
    energy_charge_cny: row.energy_charge_cny ?? row.modeled_energy_charge_cny,
    demand_charge_cny: row.demand_charge_cny ?? row.modeled_demand_charge_cny,
    total_modeled_cost_cny: row.total_modeled_cost_cny ?? row.modeled_total_cost_cny,
    delta_vs_baseline_cny: row.delta_vs_baseline_cny ?? Number(row.modeled_total_cost_cny ?? row.total_modeled_cost_cny ?? 0) - baselineScenarioCost,
    load_shift_kwh: row.load_shift_kwh ?? row.shifted_peak_energy_kwh,
    modeled_peak_kw: row.modeled_peak_kw ?? row.monthly_max_demand_kw,
  }));
  const sensitivityRaw = reviewedRows("energy_sensitivity");
  const sensitivity = sensitivityRaw.map((row) => ({
    ...row,
    parameter: row.parameter ?? `电价倍率 ${row.tariff_multiplier} / 需量费 ${row.demand_charge_cny_per_kw_month}`,
    value: row.value ?? row.parameter_value ?? `转移${number(row.load_shift_share * 100)}% / 削峰${number(row.peak_shave_share * 100)}%`,
    total_modeled_cost_cny: row.total_modeled_cost_cny ?? row.total_cost_cny ?? row.modeled_total_cost_cny,
    delta_vs_baseline_cny: row.delta_vs_baseline_cny ?? Number(row.total_cost_cny ?? row.modeled_total_cost_cny ?? row.total_modeled_cost_cny ?? 0) - baselineScenarioCost,
  }));
  const energyPeriods = reviewedRows("energy_period_profile");
  const lowestMode = [...modeSource].filter((row) => row["shipment mode"] !== "未记录").sort((a, b) => a.on_time_rate - b.on_time_rate)[0];
  const topCountry = countries[0];
  const topHour = [...energyHourly].sort((a, b) => b.average_interval_kwh - a.average_interval_kwh)[0];
  const p1Count = riskQueue.filter((row) => row.priority === "P1").length;
  const topLane = [...lanes].sort((a, b) => Number(b.line_item_value_usd) - Number(a.line_item_value_usd))[0];

  const countryColumns = [
    { key: "country", label: "目的国" }, { key: "shipment_lines", label: "明细行" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "on_time_rate", label: "准时率", renderCell: (v) => pct(v) },
    { key: "average_delay_days", label: "平均提前/延迟天数", renderCell: (v) => number(v, 1) },
  ];
  const qualityColumns = [
    { key: "dataset", label: "数据集" }, { key: "check", label: "检查项" },
    { key: "result", label: "结果" }, { key: "status", label: "状态" },
  ];
  const queueColumns = [
    { key: "priority", label: "优先级" }, { key: "source_shipment_id", label: "原始发运ID" },
    { key: "project_code", label: "项目代码" }, { key: "po_so_number", label: "PO/SO编号" },
    { key: "country", label: "目的国" }, { key: "shipment_mode", label: "运输方式" },
    { key: "manufacturing_site", label: "制造地点" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "delay_days", label: "延期天数" },
    { key: "known_freight_usd", label: "已知运费", renderCell: (v) => v == null ? "未获得数值" : usd(v) },
    { key: "freight_status", label: "运费状态" }, { key: "trigger_codes", label: "触发规则" },
    { key: "evidence_summary", label: "复核证据" }, { key: "suggested_owner", label: "建议复核部门" },
    { key: "review_status", label: "状态" },
  ];
  const laneColumns = [
    { key: "shipment_mode", label: "运输方式" }, { key: "country", label: "目的国" },
    { key: "manufacturing_site", label: "制造地点" }, { key: "shipment_lines", label: "发运行数" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "late_lines", label: "延期行数" }, { key: "late_rate", label: "延期率", renderCell: (v) => pct(v) },
    { key: "average_delay_days", label: "平均延期天数", renderCell: (v) => number(v, 1) },
    { key: "known_freight_usd", label: "已知运费", renderCell: (v) => v == null ? "未获得数值" : usd(v) },
    { key: "freight_numeric_coverage", label: "运费数值覆盖率", renderCell: (v) => pct(v) },
  ];
  const scenarioColumns = [
    { key: "label", label: "情景" }, { key: "energy_charge_cny", label: "电量电费", renderCell: (v) => cny(v) },
    { key: "demand_charge_cny", label: "需量电费", renderCell: (v) => cny(v) },
    { key: "total_modeled_cost_cny", label: "模型测算总额", renderCell: (v) => cny(v) },
    { key: "delta_vs_baseline_cny", label: "相对基准差额", renderCell: (v) => cny(v) },
    { key: "load_shift_kwh", label: "转移电量(kWh)", renderCell: (v) => number(v, 1) },
  ];
  const sensitivityColumns = [
    { key: "parameter", label: "敏感参数" }, { key: "value", label: "取值" },
    { key: "total_modeled_cost_cny", label: "测算总额", renderCell: (v) => cny(v) },
    { key: "delta_vs_baseline_cny", label: "相对基准差额", renderCell: (v) => cny(v) },
  ];

  const executiveText = `## 执行摘要

- USAID 的 ${number(summary.shipment_lines)} 条真实发运明细覆盖 ${summary.destination_countries ?? 0} 个目的国，行项目货值合计 **${usd(summary.line_item_value_usd)}**，整体准时交付率 **${pct(summary.on_time_rate)}**。
- ${lowestMode ? `在有明确运输方式的记录中，**${lowestMode["shipment mode"]}** 准时率最低（${pct(lowestMode.on_time_rate)}），应作为承运方案复盘入口；` : ""}这只是描述性定位，不能单凭该数据证明运输方式导致延迟。
- 可直接数值化的运费合计 **${usd(summary.known_freight_usd)}**，但仅覆盖 **${pct(summary.freight_numeric_coverage)}** 的发运明细，因此不能把它当作完整物流总成本。
- 已按触发规则生成 **${number(riskQueue.length)}** 条可回指原始发运记录的复核待办，其中 P1 ${number(p1Count)} 条；它们是规则筛查结果，仍需业务核实。
- UCI 钢厂 2018 年用电合计 **${number(summary.energy_usage_kwh)} kWh**，${summary.peak_energy_month ?? "-"} 为峰值月份；${topHour ? `全年分时平均值在 ${topHour.hour_label} 最高。` : ""}`;

  return <article className="cost-report" aria-label="制造供应链成本管控与经营分析报告">
    <header className="report-hero">
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); } } : undefined}>{appTitle}</h1>
      <RichNarrative id="report:intro" className="report-deck"
        value="制造供应链成本管控与经营分析项目围绕真实发运记录建立分层分析和逐单复核队列，并对真实钢厂用电数据构建可编辑的电价与负荷情景。USAID 与 UCI 数据来自不同主体，情景成本用于假设比较，不代表真实电费或节省。" />
    </header>

    <ReportSection id="report-summary" queryId="executive_summary" sourceRows={summaryRows} showHeading={false}>
      <RichNarrative id="report-summary:body" className="report-summary-lead" value={executiveText} />
    </ReportSection>

    <section className="report-facts" aria-label="核心数字">
      <MetricCard id="report-metric-value" title="行项目货值" queryId="executive_summary" sourceRows={summaryRows}
        value={usd(summary.line_item_value_usd)} description={`${number(summary.shipment_lines)} 条发运明细`} />
      <MetricCard id="report-metric-ontime" title="准时交付率" queryId="executive_summary" sourceRows={summaryRows}
        value={pct(summary.on_time_rate)} description={`晚交付率 ${pct(summary.late_shipment_rate)}`} />
      <MetricCard id="report-metric-energy" title="全年用电" queryId="executive_summary" sourceRows={summaryRows}
        value={`${number(summary.energy_usage_kwh)} kWh`} description={`CO₂ ${number(summary.co2_tonnes, 2)} 吨`} />
    </section>

    <section className="report-section">
      <ReportSection id="report-lane-section" queryId="logistics_lane_performance" sourceRows={lanes} showHeading={false}>
        <RichNarrative id="report-lanes:body" value={`## 1. 按运输方式、目的国和制造地点定位物流风险

将三类维度组合成可复核的物流线路切片，查看发运行数、货值、延期率、平均延期、可数值运费及运费覆盖率。${topLane ? `当前货值最高的组合为 ${topLane.shipment_mode} / ${topLane.country} / ${topLane.manufacturing_site}，货值 ${usd(topLane.line_item_value_usd)}。` : ""}小样本组合需要谨慎解读，分组差异用于确定核查顺序，不作运输方式或地点的因果判断。`} />
      </ReportSection>
      <DataComponent id="report-lane-table" queryId="logistics_lane_performance" kind="table" title="运输方式 × 目的国 × 制造地点"
        sourceRows={lanes} displayRows={lanes}>
        <DataTable rows={lanes} columns={laneColumns} rowKey="lane_key" />
      </DataComponent>
    </section>

    <section className="report-section">
      <ReportSection id="report-risk-queue-section" queryId="shipment_risk_queue" sourceRows={riskQueue} showHeading={false}>
        <RichNarrative id="report-risk-queue:body" value={`## 2. 从汇总分析转为逐单复核待办

系统将行货值不低于全体 P95、延期至少30天、可数值运费不低于其 P95，以及所有非数值运费状态作为触发条件。P1 包含延期至少30天且同时高货值/高运费、延期至少60天或货值达到 P99；P2 为其余高货值、长延期或高运费单项；P3 用于仅需检查运费完整性的记录。队列保留原始发运ID、触发代码、证据摘要、建议复核部门和处理状态。当前待办共 ${number(riskQueue.length)} 条，P1 ${number(p1Count)} 条。优先级用于安排复核注意力，不自动判定责任或损失。`} />
      </ReportSection>
      <DataComponent id="report-risk-queue-table" queryId="shipment_risk_queue" kind="table" title="物流异常复核队列"
        sourceRows={riskQueue} displayRows={riskQueue}>
        <DataTable rows={riskQueue} columns={queueColumns} rowKey="review_id" />
      </DataComponent>
      <DataComponent id="report-freight-status-table" queryId="freight_status_summary" kind="table" title="运费字段状态分布"
        sourceRows={freightStatuses} displayRows={freightStatuses}>
        <DataTable rows={freightStatuses} columns={[
          { key: "freight_status", label: "字段状态" }, { key: "shipment_lines", label: "发运行数" },
          { key: "numeric_amount_rows", label: "数值金额行数" },
          { key: "known_freight_usd", label: "已知运费金额", renderCell: (v) => usd(v) },
          { key: "share", label: "明细占比", renderCell: (v) => pct(v) },
        ]} rowKey="freight_status" searchable={false} />
      </DataComponent>
    </section>

    <section className="report-section">
      <ReportSection id="report-logistics" queryId="shipment_by_year" sourceRows={years} showHeading={false}>
        <RichNarrative id="report-logistics:body" value={`## 3. 发运规模与交付表现

项目先将计划交付日和实际交付日标准化，再计算准时标记、延迟天数，并按年度、运输方式、目的国和制造地点聚合。${topCountry ? `${topCountry.country} 的行项目货值最高（${usd(topCountry.line_item_value_usd)}），是业务暴露最大的目的国。` : ""} 年度趋势反映历史发运结构变化，不用于预测当前市场。`} />
      </ReportSection>
      <EvidenceChart id="report-shipment-chart" queryId="shipment_by_year" title="年度发运行项目货值"
        description="2006–2015 年历史交付记录；2015 年为非完整年度。" spec={shipmentSpec} rows={years} sourceRows={years} height={320} />
      <DataComponent id="report-country-table" queryId="country_performance" kind="table" title="主要目的国交付表现"
        sourceRows={countries} displayRows={countries}>
        <DataTable rows={countries} columns={countryColumns} rowKey="country" searchable={false} />
      </DataComponent>
    </section>

    <section className="report-section">
      <ReportSection id="report-freight" queryId="shipment_by_mode" sourceRows={modeSource} showHeading={false}>
        <RichNarrative id="report-freight:body" value={`## 4. 运费状态决定成本口径

不同运输方式的准时率存在差异，可用于提出核查清单：订单紧急度、目的国、供应商备货和清关条件是否不同。但数据没有随机分配运输方式，不能把准时率差异直接解释成方式优劣。运费字段还含“货值已含运费”“另行开票”等文本状态，项目只累计 ${pct(summary.freight_numeric_coverage)} 可数值化记录并单独披露覆盖率。`} />
      </ReportSection>
      <EvidenceChart id="report-mode-chart" queryId="shipment_by_mode" title="运输方式准时率"
        spec={modeSpec} rows={modes} sourceRows={modeSource} height={320} />
    </section>

    <section className="report-section">
      <ReportSection id="report-energy" queryId="energy_monthly" sourceRows={energyMonthly} showHeading={false}>
        <RichNarrative id="report-energy:body" value={`## 5. 制造能耗按月与时段定位

钢厂全年 ${number(summary.energy_observations)} 个15分钟观测共记录 ${number(summary.energy_usage_kwh)} kWh。最大负荷类型贡献 ${pct(summary.maximum_load_energy_share)} 的电量，${summary.peak_energy_month} 用电最高（${number(summary.peak_energy_month_kwh)} kWh）。数据没有产量和设备运行台账，因此不能计算单位产品能耗或将峰值归因到具体设备。`} />
      </ReportSection>
      <EvidenceChart id="report-energy-chart" queryId="energy_monthly" title="月度用电量"
        spec={energySpec} rows={energyMonthly} sourceRows={energyMonthly} height={320} />
      <EvidenceChart id="report-hour-chart" queryId="energy_hourly" title="分时平均15分钟用电"
        spec={hourlySpec} rows={energyHourly} sourceRows={energyHourly} height={300} />
    </section>

    <section className="report-section">
      <ReportSection id="report-energy-scenario" queryId="energy_scenario_summary" sourceRows={scenarios} showHeading={false}>
        <RichNarrative id="report-energy-scenario:body" value={`## 6. 用可编辑费率开展能耗成本情景比较

基于 UCI 15 分钟用电序列，按情景参数估算峰、平、谷电量电费和月需量费用，并比较基准与负荷转移/削峰情景。输入包含峰平谷电价、需量单价、转移比例和削峰比例；情景金额及其与基准的差额均为模型结果，不是经账单验证的真实成本或节省。${scenarios.length ? `本次展示 ${number(scenarios.length)} 个参数情景。` : "情景结果尚未生成。"}`} />
      </ReportSection>
      {scenarios.length > 0 && <EvidenceChart id="report-energy-scenario-chart" queryId="energy_scenario_summary" title="不同假设下的模型测算能耗成本"
        description="金额由情景参数推算，仅用于假设比较。" spec={scenarioCostSpec} rows={scenarios} sourceRows={scenarios} height={320} />}
      <DataComponent id="report-energy-assumption-table" queryId="energy_scenario_assumptions" kind="table" title="情景参数和数据属性"
        sourceRows={scenarioAssumptions} displayRows={scenarioAssumptions}>
        <DataTable rows={scenarioAssumptions} columns={[
          { key: "parameter", label: "参数" }, { key: "value", label: "当前值" },
          { key: "unit", label: "单位" }, { key: "editable", label: "可编辑" },
          { key: "evidence_type", label: "数据属性" },
        ]} rowKey="parameter" searchable={false} />
      </DataComponent>
      {scenarios.length > 0 && <DataComponent id="report-energy-scenario-table" queryId="energy_scenario_summary" kind="table" title="情景成本拆分与基准差额"
        sourceRows={scenarios} displayRows={scenarios}>
        <DataTable rows={scenarios} columns={scenarioColumns} rowKey="scenario_id" searchable={false} />
      </DataComponent>}
      {sensitivity.length > 0 && <DataComponent id="report-energy-sensitivity-table" queryId="energy_sensitivity" kind="table" title="参数敏感性分析"
        sourceRows={sensitivity} displayRows={sensitivity}>
        <DataTable rows={sensitivity} columns={sensitivityColumns} rowKey="sensitivity_key" />
      </DataComponent>}
      {energyPeriods.length > 0 && <DataComponent id="report-energy-period-table" queryId="energy_period_profile" kind="table" title="工作日/周末峰平谷用电结构"
        sourceRows={energyPeriods} displayRows={energyPeriods}>
        <DataTable rows={energyPeriods} columns={[
          { key: "week_status", label: "日期类型" }, { key: "tariff_period", label: "时段" },
          { key: "load_type", label: "负荷类型" },
          { key: "usage_kwh", label: "用电量(kWh)", renderCell: (v) => number(v, 1) },
          { key: "observations", label: "15分钟观测数" },
          { key: "average_interval_kwh", label: "平均间隔用电(kWh)", renderCell: (v) => number(v, 3) },
          { key: "observed_peak_kw", label: "观测区间峰值(kW)", renderCell: (v) => number(v, 1) },
        ]} rowKey="profile_key" searchable={false} />
      </DataComponent>}
    </section>

    <section className="report-section">
      <ReportSection id="report-actions" queryId="executive_summary" sourceRows={summaryRows} showHeading={false}>
        <RichNarrative id="report-actions:body" value={`## 7. 建议的管理动作

1. 对低准时率运输方式进一步按目的国、制造地点和年份分层，确认是否由业务结构造成。
2. 对运费字段建立“数值金额 / 已含货值 / 另行开票 / 引用其他单据”四类标准，先提高数据覆盖再设成本目标。
3. 逐条处理复核队列，补充合同、订单紧急度、承运和清关记录，再决定是否升级异常。
4. 用当地电费账单和合同校准峰平谷电价、需量费口径及计费周期；校准前只把情景金额作为假设比较。
5. 接入产量、设备运行和电费账单后，再评估单位产品能耗与可验证的改善收益。`} />
      </ReportSection>
    </section>

    <section className="report-section report-methods">
      <RichNarrative id="report:methods" value="## 数据边界\n\n- USAID 数据是公开真实行政记录，原始门户标识为 a3rc-nmf6；门户当前不可访问，本地文件来自公开镜像。\n- UCI 数据来自韩国一家钢铁企业的真实 2018 年观测，许可为 CC BY 4.0。\n- USAID 与 UCI 数据来自不同组织、不同年份，不合并计算企业总成本。\n- 物流队列是规则筛查结果；阈值和部门建议需要业务复核，不代表已确认异常或责任归属。\n- 能耗成本情景采用可编辑峰平谷费率、需量价格及负荷转移假设。数据为15分钟粒度；若费率时段、计量口径和需量计费周期未校准，金额只用于敏感性比较，不能称作真实电费或节省。\n- 原 AdventureWorks 和固定随机种子生成数据均已退出主报告、主看板和主指标。" />
      <DataComponent id="report-quality-table" queryId="data_quality" kind="table" title="数据质量检查结果"
        sourceRows={quality} displayRows={quality}>
        <DataTable rows={quality} columns={qualityColumns} rowKey="check" searchable={false} />
      </DataComponent>
    </section>
  </article>;
}
