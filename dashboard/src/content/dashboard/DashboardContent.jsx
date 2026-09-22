import React from "react";

import { DataComponent, DataTable, EvidenceChart, MetricCard, useDataApp } from "../../data-app-public.jsx";
import "./example.css";

const usd = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "USD", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const number = (value, digits = 0) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(Number(value ?? 0));
const pct = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;

const shipmentTrendSpec = {
  type: "line", x: "delivery_year", y: "line_item_value_usd", currency: "USD", valueDecimals: 0,
  colors: { line_item_value_usd: "var(--chart-1)" },
};
const modeSpec = {
  type: "bar", x: "shipment mode", y: "on_time_pct", valueDecimals: 1,
  colors: { on_time_pct: "var(--chart-2)" },
};
const countrySpec = {
  type: "horizontalBar", x: "country", y: "line_item_value_usd", currency: "USD", valueDecimals: 0,
  colors: { line_item_value_usd: "var(--chart-3)" },
};
const energyMonthlySpec = {
  type: "line", x: "month", y: "usage_kwh", valueDecimals: 0,
  colors: { usage_kwh: "var(--chart-4)" },
};
const hourlySpec = {
  type: "line", x: "hour_label", y: "average_interval_kwh", valueDecimals: 1,
  colors: { average_interval_kwh: "var(--chart-5)" },
};
const loadSpec = {
  type: "bar", x: "Load_Type", y: "usage_kwh", valueDecimals: 0,
  colors: { usage_kwh: "var(--chart-1)" },
};

export function DashboardContent() {
  const { reviewedRows, visible } = useDataApp();
  const summaryRows = reviewedRows("executive_summary");
  const [summary = {}] = summaryRows;
  const years = reviewedRows("shipment_by_year");
  const modeSource = reviewedRows("shipment_by_mode");
  const modes = modeSource.map((row) => ({ ...row, on_time_pct: Number(row.on_time_rate) * 100 }));
  const countries = reviewedRows("country_performance");
  const sites = reviewedRows("manufacturing_sites");
  const energyMonthly = reviewedRows("energy_monthly");
  const energyHourly = reviewedRows("energy_hourly");
  const energyLoad = reviewedRows("energy_by_load_type");
  const quality = reviewedRows("data_quality");

  const modeColumns = [
    { key: "shipment mode", label: "运输方式" },
    { key: "shipment_lines", label: "明细行" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "on_time_rate", label: "准时率", renderCell: (v) => pct(v) },
    { key: "freight_numeric_coverage", label: "运费覆盖", renderCell: (v) => pct(v) },
  ];
  const siteColumns = [
    { key: "manufacturing site", label: "制造地点" },
    { key: "shipment_lines", label: "明细行" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "on_time_rate", label: "准时率", renderCell: (v) => pct(v) },
  ];
  const qualityColumns = [
    { key: "dataset", label: "数据集" }, { key: "check", label: "检查项" },
    { key: "result", label: "结果" }, { key: "status", label: "状态" },
  ];

  return <article className="cost-dashboard" aria-label="真实供应链与制造能耗分析看板">
    <section className="dashboard-intro">
      <p><strong>全部主指标来自真实公开观测数据。</strong> USAID 发运数据覆盖 2006–2015 年；UCI 钢厂能耗数据覆盖 2018 年。两套数据属于不同组织与时期，只并列展示，不做企业级合并归因。</p>
    </section>

    <section className="kpi-grid" aria-label="核心指标">
      {visible("kpi-value") && <MetricCard id="kpi-value" title="发运行项目货值" queryId="executive_summary"
        sourceRows={summaryRows} value={usd(summary.line_item_value_usd)}
        description={`${number(summary.shipment_lines)} 条明细，覆盖 ${summary.destination_countries ?? 0} 个国家`} />}
      {visible("kpi-ontime") && <MetricCard id="kpi-ontime" title="准时交付率" queryId="executive_summary"
        sourceRows={summaryRows} value={pct(summary.on_time_rate)} description={`晚交付率 ${pct(summary.late_shipment_rate)}`} />}
      {visible("kpi-freight") && <MetricCard id="kpi-freight" title="已知数值运费" queryId="executive_summary"
        sourceRows={summaryRows} value={usd(summary.known_freight_usd)}
        description={`仅覆盖 ${pct(summary.freight_numeric_coverage)} 的发运明细`} />}
      {visible("kpi-energy") && <MetricCard id="kpi-energy" title="钢厂全年用电" queryId="executive_summary"
        sourceRows={summaryRows} value={`${number(summary.energy_usage_kwh)} kWh`}
        description={`CO₂ ${number(summary.co2_tonnes, 2)} 吨；不虚构电价`} />}
    </section>

    <section className="chart-grid chart-grid--wide">
      <EvidenceChart id="shipment-value-trend" queryId="shipment_by_year" title="年度发运行项目货值"
        description="按实际交付年份汇总；2015 年为截至数据末期的非完整年度。"
        spec={shipmentTrendSpec} rows={years} sourceRows={years} height={310} />
      <EvidenceChart id="mode-ontime" queryId="shipment_by_mode" title="运输方式准时率"
        description="实际交付日不晚于计划交付日即计为准时。"
        spec={modeSpec} rows={modes} sourceRows={modeSource} height={310} />
    </section>

    <section className="chart-grid">
      <EvidenceChart id="country-value" queryId="country_performance" title="主要目的国货值"
        description="按货值排名前12个目的国；用于识别业务暴露，不代表利润。"
        spec={countrySpec} rows={countries} sourceRows={countries} height={360} />
      <DataComponent id="freight-coverage" queryId="shipment_by_mode" kind="table" title="运输方式成本与交付"
        description="已知运费仅汇总可数值化记录，覆盖率用于提示口径完整性。"
        sourceRows={modeSource} displayRows={modeSource}>
        <DataTable rows={modeSource} columns={modeColumns} rowKey="shipment mode" searchable={false} />
      </DataComponent>
    </section>

    <section className="chart-grid chart-grid--wide">
      <EvidenceChart id="energy-monthly" queryId="energy_monthly" title="钢厂月度用电量"
        description={`2018 年真实15分钟观测；峰值月份为 ${summary.peak_energy_month ?? "-"}。`}
        spec={energyMonthlySpec} rows={energyMonthly} sourceRows={energyMonthly} height={310} />
      <EvidenceChart id="energy-load" queryId="energy_by_load_type" title="负荷类型用电结构"
        description="Maximum、Medium 与 Light Load 的全年用电量。"
        spec={loadSpec} rows={energyLoad} sourceRows={energyLoad} height={310} />
    </section>

    <section className="chart-grid">
      <EvidenceChart id="energy-hourly" queryId="energy_hourly" title="分时平均15分钟用电"
        description="按小时汇总全年同一时段观测，用于定位高负荷时段。"
        spec={hourlySpec} rows={energyHourly} sourceRows={energyHourly} height={310} />
      <DataComponent id="manufacturing-sites" queryId="manufacturing_sites" kind="table" title="主要制造地点"
        description="按发运行项目货值排序的前12个制造地点。"
        sourceRows={sites} displayRows={sites}>
        <DataTable rows={sites} columns={siteColumns} rowKey="manufacturing site" searchable={false} />
      </DataComponent>
    </section>

    <section className="chart-grid chart-grid--single">
      <DataComponent id="data-quality" queryId="data_quality" kind="table" title="数据质量检查"
        description="caution 表示字段可用但覆盖不完整，使用时必须同时披露覆盖率。"
        sourceRows={quality} displayRows={quality}>
        <DataTable rows={quality} columns={qualityColumns} rowKey="check" searchable={false} />
      </DataComponent>
    </section>
  </article>;
}
