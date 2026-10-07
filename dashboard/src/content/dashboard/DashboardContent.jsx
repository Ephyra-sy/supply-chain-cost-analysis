import React from "react";

import { DataComponent, DataTable, EvidenceChart, MetricCard, Slider, useDataApp } from "../../data-app-public.jsx";
import "./example.css";
import "./dashboard.css";

const usd = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "USD", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const number = (value, digits = 0) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(Number(value ?? 0));
const pct = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;
const cny = (value) => new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value ?? 0));

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
  const riskQueue = reviewedRows("shipment_risk_queue");
  const laneRows = reviewedRows("logistics_lane_performance");
  const years = reviewedRows("shipment_by_year");
  const modeSource = reviewedRows("shipment_by_mode");
  const modes = modeSource.map((row) => ({ ...row, on_time_pct: Number(row.on_time_rate) * 100 }));
  const countries = reviewedRows("country_performance");
  const sites = reviewedRows("manufacturing_sites");
  const energyMonthly = reviewedRows("energy_monthly");
  const energyHourly = reviewedRows("energy_hourly");
  const energyLoad = reviewedRows("energy_by_load_type");
  const quality = reviewedRows("data_quality");
  const [selectedReview, setSelectedReview] = React.useState(null);
  const [tariffs, setTariffs] = React.useState({ peak: 0.9, shoulder: 0.6, offpeak: 0.3, demand: 40, shift: 5, shave: 3 });
  const periodProfile = reviewedRows("energy_period_profile");
  const monthlyDemand = reviewedRows("energy_monthly_demand");
  const energyScenarioSummary = reviewedRows("energy_scenario_summary");
  const energySensitivity = reviewedRows("energy_sensitivity");

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
  const energyGroups = periodProfile.reduce((acc, row) => {
    const label = String(row.tariff_period ?? "").toLowerCase();
    const key = label.includes("off") || label.includes("谷") ? "offpeak"
      : label.includes("shoulder") || label.includes("平") ? "shoulder" : "peak";
    acc[key] = (acc[key] ?? 0) + Number(row.usage_kwh ?? 0);
    return acc;
  }, { peak: 0, shoulder: 0, offpeak: 0 });
  const observedMonthlyKw = monthlyDemand.reduce((sum, row) => sum + Number(row.observed_peak_kw ?? 0), 0);
  const baselineEnergyCost = energyGroups.peak * tariffs.peak + energyGroups.shoulder * tariffs.shoulder + energyGroups.offpeak * tariffs.offpeak;
  const modeledDemand = observedMonthlyKw * tariffs.demand;
  const shiftedPeakKwh = energyGroups.peak * tariffs.shift / 100;
  const adjustedEnergyCost = (energyGroups.peak - shiftedPeakKwh) * tariffs.peak
    + energyGroups.shoulder * tariffs.shoulder + (energyGroups.offpeak + shiftedPeakKwh) * tariffs.offpeak;
  const adjustedDemand = observedMonthlyKw * (1 - tariffs.shave / 100) * tariffs.demand;
  const modeledBaseCost = baselineEnergyCost + modeledDemand;
  const modeledAdjustedCost = adjustedEnergyCost + adjustedDemand;
  const queueColumns = [
    { key: "priority", label: "优先级", presentation: "status" },
    { key: "review_id", label: "复核编号" },
    { key: "source_shipment_id", label: "原始发运ID" },
    { key: "project_code", label: "项目" },
    { key: "po_so_number", label: "采购/销售单号" },
    { key: "country", label: "目的国" },
    { key: "shipment_mode", label: "运输方式" },
    { key: "manufacturing_site", label: "制造地点" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "delay_days", label: "延期天数", renderCell: (v) => `${number(v, 1)} 天` },
    { key: "known_freight_usd", label: "已知运费", renderCell: (v) => v == null ? "未提供数值" : usd(v) },
    { key: "freight_status", label: "运费状态" },
    { key: "trigger_codes", label: "触发规则" },
    { key: "suggested_owner", label: "建议复核部门" },
    { key: "review_status", label: "复核状态" },
  ];
  const laneColumns = [
    { key: "shipment_mode", label: "运输方式" },
    { key: "country", label: "目的国" },
    { key: "manufacturing_site", label: "制造地点" },
    { key: "shipment_lines", label: "明细行" },
    { key: "line_item_value_usd", label: "货值", renderCell: (v) => usd(v) },
    { key: "late_lines", label: "晚交行数" },
    { key: "late_rate", label: "晚交率", renderCell: (v) => pct(v) },
    { key: "average_delay_days", label: "平均交付偏差", renderCell: (v) => `${number(Math.abs(Number(v)), 1)} 天${Number(v) < 0 ? "提前" : "延后"}` },
    { key: "known_freight_usd", label: "已知运费", renderCell: (v) => v == null ? "未提供数值" : usd(v) },
    { key: "freight_numeric_coverage", label: "运费覆盖率", renderCell: (v) => pct(v) },
  ];

  return <article className="cost-dashboard" aria-label="制造供应链成本管控与经营分析看板">
    <section className="action-queue-section" aria-label="物流异常复核队列">
      <div className="action-queue-heading">
        <div>
          <h2>物流异常复核队列</h2>
          <p>按规则筛出的发运明细候选项，可凭原始发运 ID 回查来源记录；队列用于人工核查，不代表已确认事故。</p>
        </div>
        <div className="queue-count"><strong>{number(riskQueue.length)}</strong><span>条待复核候选</span></div>
      </div>
      {visible("shipment-risk-queue") && <DataComponent id="shipment-risk-queue" queryId="shipment_risk_queue" kind="table"
        title="优先处理项" description="依据规则优先级、原始发运编号、延期、货值、运费状态和建议责任部门逐条复核。空白/非数值运费按状态展示，不会作为 0 美元。"
        sourceRows={riskQueue} displayRows={riskQueue}>
          <DataTable rows={riskQueue} columns={queueColumns} rowKey="review_id" searchable
          caption="物流异常复核队列；记录由真实公开发运明细按规则筛选，需人工复核。"
          selectedRowKey={selectedReview?.review_id}
          onRowSelect={setSelectedReview} rowActionLabel={(row) => `查看复核证据 ${row.review_id}`} />
      </DataComponent>}
      {selectedReview && <div className="review-evidence" data-reviewed-rows>
        <div><span>复核编号</span><strong>{selectedReview.review_id}</strong></div>
        <div><span>触发依据</span><strong>{selectedReview.evidence_summary || selectedReview.trigger_codes}</strong></div>
        <div><span>核查建议</span><strong>{selectedReview.suggested_owner}：{selectedReview.recommended_action}</strong></div>
      </div>}
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

    <section className="dashboard-intro">
      <p><strong>数据范围：</strong>USAID 发运数据为 2006–2015 年公开记录；UCI 钢厂能耗为 2018 年15分钟观测。两套数据属于不同组织与时期，分别分析，不作企业级合并归因。后续电价情景为参数模型，不是实际电费或已实现节省。</p>
    </section>

    <section className="chart-grid--single">
      <DataComponent id="logistics-lane-performance" queryId="logistics_lane_performance" kind="table" title="运输方式 × 目的国 × 制造地点"
        description="按三项业务维度联合汇总货值、交付和运费覆盖，便于定位需要深入核查的具体线路组合。小样本组合请结合明细量谨慎解释。"
        sourceRows={laneRows} displayRows={laneRows}>
        <DataTable rows={laneRows} columns={laneColumns} rowKey="lane_key" searchable
          caption="运输方式、目的国与制造地点联合表现" />
      </DataComponent>
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

    <section className="energy-scenario-section" aria-label="制造能耗成本情景分析">
      <div className="energy-scenario-heading">
        <div><h2>制造能耗成本情景</h2><p>基于钢厂15分钟用电观测和可编辑费率参数估算；结果为模型情景，不代表该工厂实际电费或可实现节省。</p></div>
      </div>
      <DataComponent id="energy-scenario-controls" queryId="energy_period_profile" queryIds={["energy_monthly_demand"]} kind="custom" title="可调参数与模型结果"
        description="默认参数仅用于演示：峰/平/谷电价按元/kWh，需量费按元/kW·月；峰段负荷转移至谷段，削峰比例作用于各月观测最大15分钟负荷。"
        sourceRows={periodProfile} displayRows={periodProfile}
        sourceRowsByQuery={{ energy_period_profile: periodProfile, energy_monthly_demand: monthlyDemand }}>
        <div className="scenario-layout" data-reviewed-rows>
          <div className="scenario-controls">
            <Slider label="峰段电价（元/kWh）" min={0.6} max={1.5} step={0.05} value={tariffs.peak} showBounds
              formatValue={(v) => v.toFixed(2)} onChange={(value) => setTariffs((old) => ({ ...old, peak: value }))} />
            <Slider label="平段电价（元/kWh）" min={0.3} max={1} step={0.05} value={tariffs.shoulder} showBounds
              formatValue={(v) => v.toFixed(2)} onChange={(value) => setTariffs((old) => ({ ...old, shoulder: value }))} />
            <Slider label="谷段电价（元/kWh）" min={0.1} max={0.6} step={0.05} value={tariffs.offpeak} showBounds
              formatValue={(v) => v.toFixed(2)} onChange={(value) => setTariffs((old) => ({ ...old, offpeak: value }))} />
            <Slider label="需量费（元/kW·月）" min={0} max={80} step={5} value={tariffs.demand} showBounds
              formatValue={(v) => `${v}`} onChange={(value) => setTariffs((old) => ({ ...old, demand: value }))} />
            <Slider label="峰段负荷转移至谷段" min={0} max={20} step={1} value={tariffs.shift} showBounds
              formatValue={(v) => `${v}%`} onChange={(value) => setTariffs((old) => ({ ...old, shift: value }))} />
            <Slider label="月峰值削减比例" min={0} max={15} step={1} value={tariffs.shave} showBounds
              formatValue={(v) => `${v}%`} onChange={(value) => setTariffs((old) => ({ ...old, shave: value }))} />
          </div>
          <div className="scenario-results">
            <h3>模型情景结果</h3>
            <div className="scenario-result-row"><span>基准估算年成本</span><strong>{cny(modeledBaseCost)}</strong></div>
            <div className="scenario-result-row"><span>调整后估算年成本</span><strong>{cny(modeledAdjustedCost)}</strong></div>
            <div className="scenario-result-row"><span>模型成本差额</span><strong>{cny(modeledBaseCost - modeledAdjustedCost)}</strong></div>
            <div className="scenario-result-row"><span>年电量成本</span><strong>{cny(adjustedEnergyCost)}</strong></div>
            <div className="scenario-result-row"><span>年需量费估算</span><strong>{cny(adjustedDemand)}</strong></div>
            <p>计算依据：峰/平/谷分时电量 × 对应假设电价；需量费按每月最高15分钟负荷之和 × 假设需量单价。默认费率和调整比例是可修改的演示参数，未使用真实电费账单。</p>
          </div>
        </div>
      </DataComponent>
      <DataComponent id="energy-scenario-summary" queryId="energy_scenario_summary" kind="table" title="预设成本区间情景"
        description="由基准、轻度优化和强化优化组成的参数化范围示例；全部金额是人民币模型估算，不是实际账单节省。"
        sourceRows={energyScenarioSummary} displayRows={energyScenarioSummary}>
        <DataTable rows={energyScenarioSummary} columns={[
          { key: "scenario", label: "模型情景" }, { key: "tariff_multiplier", label: "电价倍率" },
          { key: "modeled_energy_charge_cny", label: "电量费用（模型）", renderCell: (v) => cny(v) },
          { key: "modeled_demand_charge_cny", label: "需量费用（模型）", renderCell: (v) => cny(v) },
          { key: "modeled_total_cost_cny", label: "总成本（模型）", renderCell: (v) => cny(v) },
          { key: "estimated_savings_vs_baseline_cny", label: "较基准模型差额", renderCell: (v) => cny(v) },
          { key: "interpretation", label: "说明" },
        ]} rowKey="scenario" searchable={false} caption="基准、轻度优化与强化优化成本情景" />
      </DataComponent>
      <DataComponent id="energy-period-profile" queryId="energy_period_profile" kind="table" title="工作日、周末与分时用电分布"
        description="用电量按工作日/周末、假设峰平谷时段和负荷类型拆分；时段划分属于演示模型口径。"
        sourceRows={periodProfile} displayRows={periodProfile}>
        <DataTable rows={periodProfile} columns={[
          { key: "week_status", label: "工作日/周末" }, { key: "tariff_period", label: "分时段" },
          { key: "load_type", label: "负荷类型" }, { key: "usage_kwh", label: "用电量（kWh）", renderCell: (v) => number(v, 1) },
          { key: "observations", label: "15分钟记录数" }, { key: "average_interval_kwh", label: "平均区间用电（kWh）", renderCell: (v) => number(v, 3) },
          { key: "observed_peak_kw", label: "观测区间最大负荷（kW）", renderCell: (v) => number(v, 1) },
        ]} rowKey="profile_key" searchable={false} caption="工作日、周末、分时段与负荷类型用电分布" />
      </DataComponent>
      <div className="chart-grid">
        <DataComponent id="energy-monthly-demand" queryId="energy_monthly_demand" kind="table" title="月度最大15分钟负荷"
          description="每月最高15分钟用电量乘以4换算为平均kW，作为需量费情景的计费基础。"
          sourceRows={monthlyDemand} displayRows={monthlyDemand}>
          <DataTable rows={monthlyDemand} columns={[
            { key: "month", label: "月份" }, { key: "peak_usage_kwh", label: "峰段电量（kWh）", renderCell: (v) => number(v, 1) },
            { key: "shoulder_usage_kwh", label: "平段电量（kWh）", renderCell: (v) => number(v, 1) },
            { key: "offpeak_usage_kwh", label: "谷段电量（kWh）", renderCell: (v) => number(v, 1) },
            { key: "observed_peak_kw", label: "月最大15分钟负荷（kW）", renderCell: (v) => number(v, 1) },
          ]} rowKey="month" searchable={false} caption="月度分时用电与最大负荷" />
        </DataComponent>
        <DataComponent id="energy-sensitivity" queryId="energy_sensitivity" kind="table" title="模型敏感性分析"
          description="以基准电价与负荷参数为参照改变单项假设，显示模型成本变化；并非实际账单节省。"
          sourceRows={energySensitivity} displayRows={energySensitivity}>
          <DataTable rows={energySensitivity} columns={[
            { key: "parameter", label: "变化参数" }, { key: "scenario", label: "假设情景" },
            { key: "parameter_value", label: "参数值" }, { key: "total_cost_cny", label: "模型总成本（元）", renderCell: (v) => cny(v) },
            { key: "change_vs_base_pct", label: "较基准变化", renderCell: (v) => pct(v) },
          ]} rowKey="sensitivity_key" searchable={false} caption="能源成本模型参数敏感性" />
        </DataComponent>
      </div>
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
