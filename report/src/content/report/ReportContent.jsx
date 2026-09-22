import React from "react";

import { DataComponent, DataTable, EvidenceChart, MetricCard, ReportSection, RichNarrative, useDataApp } from "../../data-app-public.jsx";

const usd = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "USD", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const number = (value, digits = 0) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(Number(value ?? 0));
const pct = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;

const shipmentSpec = { type: "line", x: "delivery_year", y: "line_item_value_usd", currency: "USD", valueDecimals: 0, colors: { line_item_value_usd: "var(--chart-1)" } };
const modeSpec = { type: "bar", x: "shipment mode", y: "on_time_pct", valueDecimals: 1, colors: { on_time_pct: "var(--chart-2)" } };
const energySpec = { type: "line", x: "month", y: "usage_kwh", valueDecimals: 0, colors: { usage_kwh: "var(--chart-4)" } };
const hourlySpec = { type: "line", x: "hour_label", y: "average_interval_kwh", valueDecimals: 1, colors: { average_interval_kwh: "var(--chart-5)" } };

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
  const lowestMode = [...modeSource].filter((row) => row["shipment mode"] !== "未记录").sort((a, b) => a.on_time_rate - b.on_time_rate)[0];
  const topCountry = countries[0];
  const topHour = [...energyHourly].sort((a, b) => b.average_interval_kwh - a.average_interval_kwh)[0];

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

  const executiveText = `## 执行摘要

- USAID 的 ${number(summary.shipment_lines)} 条真实发运明细覆盖 ${summary.destination_countries ?? 0} 个目的国，行项目货值合计 **${usd(summary.line_item_value_usd)}**，整体准时交付率 **${pct(summary.on_time_rate)}**。
- ${lowestMode ? `在有明确运输方式的记录中，**${lowestMode["shipment mode"]}** 准时率最低（${pct(lowestMode.on_time_rate)}），应作为承运方案复盘入口；` : ""}这只是描述性定位，不能单凭该数据证明运输方式导致延迟。
- 可直接数值化的运费合计 **${usd(summary.known_freight_usd)}**，但仅覆盖 **${pct(summary.freight_numeric_coverage)}** 的发运明细，因此不能把它当作完整物流总成本。
- UCI 钢厂 2018 年用电合计 **${number(summary.energy_usage_kwh)} kWh**，${summary.peak_energy_month ?? "-"} 为峰值月份；${topHour ? `全年分时平均值在 ${topHour.hour_label} 最高。` : ""}`;

  return <article className="cost-report" aria-label="真实供应链成本与制造能耗分析报告">
    <header className="report-hero">
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); } } : undefined}>{appTitle}</h1>
      <RichNarrative id="report:intro" className="report-deck"
        value="使用 USAID 真实国际供应链发运数据和 UCI 真实钢厂能耗数据，展示采购物流分析、交付风险识别、数据质量控制与制造能耗诊断。两套数据不属于同一家企业，因此只形成方法链路，不合并为虚构的企业损益。" />
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
      <ReportSection id="report-logistics" queryId="shipment_by_year" sourceRows={years} showHeading={false}>
        <RichNarrative id="report-logistics:body" value={`## 1. 发运规模与交付表现

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
        <RichNarrative id="report-freight:body" value={`## 2. 运输方式是复盘入口，不是因果结论

不同运输方式的准时率存在差异，可用于提出核查清单：订单紧急度、目的国、供应商备货和清关条件是否不同。但数据没有随机分配运输方式，不能把准时率差异直接解释成方式优劣。运费字段还含“货值已含运费”“另行开票”等文本状态，项目只累计 ${pct(summary.freight_numeric_coverage)} 可数值化记录并单独披露覆盖率。`} />
      </ReportSection>
      <EvidenceChart id="report-mode-chart" queryId="shipment_by_mode" title="运输方式准时率"
        spec={modeSpec} rows={modes} sourceRows={modeSource} height={320} />
    </section>

    <section className="report-section">
      <ReportSection id="report-energy" queryId="energy_monthly" sourceRows={energyMonthly} showHeading={false}>
        <RichNarrative id="report-energy:body" value={`## 3. 制造能耗按月与时段定位

钢厂全年 ${number(summary.energy_observations)} 个15分钟观测共记录 ${number(summary.energy_usage_kwh)} kWh。最大负荷类型贡献 ${pct(summary.maximum_load_energy_share)} 的电量，${summary.peak_energy_month} 用电最高（${number(summary.peak_energy_month_kwh)} kWh）。在缺少生产量和电价的情况下，项目不计算单位产量能耗或金额节省，避免制造“降本成果”。`} />
      </ReportSection>
      <EvidenceChart id="report-energy-chart" queryId="energy_monthly" title="月度用电量"
        spec={energySpec} rows={energyMonthly} sourceRows={energyMonthly} height={320} />
      <EvidenceChart id="report-hour-chart" queryId="energy_hourly" title="分时平均15分钟用电"
        spec={hourlySpec} rows={energyHourly} sourceRows={energyHourly} height={300} />
    </section>

    <section className="report-section">
      <ReportSection id="report-actions" queryId="executive_summary" sourceRows={summaryRows} showHeading={false}>
        <RichNarrative id="report-actions:body" value={`## 4. 建议的管理动作

1. 对低准时率运输方式进一步按目的国、供应商和年份分层，确认是否由业务结构造成。
2. 对运费字段建立“数值金额 / 已含货值 / 另行开票 / 引用其他单据”四类标准，先提高数据覆盖再设成本目标。
3. 以月度峰值和高负荷时段作为排产、空载检查和设备启停审计入口；接入产量与电价后，再计算单位产品能耗和节省金额。
4. 面试中明确本项目完成的是公开真实数据的诊断方法，不声称为某企业实现了实际降本。`} />
      </ReportSection>
    </section>

    <section className="report-section report-methods">
      <RichNarrative id="report:methods" value="## 数据边界\n\n- USAID 数据是公开真实行政记录，原始门户标识为 a3rc-nmf6；门户当前不可访问，本地文件来自公开镜像。\n- UCI 数据来自韩国一家钢铁企业的真实 2018 年观测，许可为 CC BY 4.0。\n- USAID 与 UCI 数据来自不同组织、不同年份，不合并计算企业总成本。\n- 原 AdventureWorks 和固定随机种子生成数据均已退出主报告、主看板和主指标。" />
      <DataComponent id="report-quality-table" queryId="data_quality" kind="table" title="数据质量检查结果"
        sourceRows={quality} displayRows={quality}>
        <DataTable rows={quality} columns={qualityColumns} rowKey="check" searchable={false} />
      </DataComponent>
    </section>
  </article>;
}
