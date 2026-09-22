import React from "react";

import {
  DataComponent, DataTable, EvidenceChart, MetricCard, ReportSection, RichNarrative, useDataApp,
} from "../../data-app-public.jsx";

const money = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "CNY", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const pct = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;

const budgetSpec = {
  type: "line", x: "month", y: "budget_amount", fields: ["budget_amount", "actual_amount"],
  currency: "CNY", valueDecimals: 0,
  colors: { budget_amount: "var(--secondary)", actual_amount: "var(--chart-1)" },
  legend: { labels: { budget_amount: "预算", actual_amount: "实际" } },
};
const projectSpec = {
  type: "bar", x: "project_name", y: "forecast_overrun", currency: "CNY", valueDecimals: 0,
  colors: { forecast_overrun: "var(--chart-4)" }, xTickLabelLayout: "angled",
};
const scrapSpec = {
  type: "horizontalBar", x: "reason", y: "scrap_loss_amount", currency: "CNY", valueDecimals: 0,
  colors: { scrap_loss_amount: "var(--chart-5)" },
};

export function ReportContent() {
  const { appTitle, canEdit, mode, reviewedRows, setAppTitle } = useDataApp();
  const summaryRows = reviewedRows("executive_summary");
  const [summary = {}] = summaryRows;
  const monthly = reviewedRows("monthly_budget");
  const projects = reviewedRows("project_risk");
  const highRisk = projects.filter((row) => row.risk_level === "high");
  const scrap = reviewedRows("scrap_by_reason");
  const ppv = reviewedRows("purchase_price_variance");
  const inventory = reviewedRows("inventory_by_location");

  const topProject = [...projects].sort((a, b) => Number(b.forecast_overrun) - Number(a.forecast_overrun))[0];
  const topScrap = scrap[0];
  const topPpv = ppv[0];
  const lowestInventory = [...inventory].sort((a, b) => Number(a.match_rate) - Number(b.match_rate))[0];

  const projectColumns = [
    { key: "project_name", label: "项目" },
    { key: "completion_rate", label: "进度", renderCell: (v) => pct(v) },
    { key: "cost_consumption_rate", label: "成本消耗", renderCell: (v) => pct(v) },
    { key: "forecast_overrun", label: "预计超支", renderCell: (v) => money(v, false) },
    { key: "risk_level", label: "风险" },
  ];

  const executiveText = `## 执行摘要

- 2026年仿真预算执行率为 **${pct(summary.budget_execution_rate)}**，整体未超预算，但存在 **${summary.red_warning_cells ?? 0}** 个超预算组合，需下沉到部门和费用科目复核。
- ${summary.high_risk_projects ?? 0}个仿真项目被标记为高风险，预计超支正值合计 **${money(summary.forecast_project_overrun)}**。${topProject ? ` 其中 ${topProject.project_name} 的预计超支最高。` : ""}
- 仿真盘点的账实相符率为 **${pct(summary.inventory_match_rate)}**；${lowestInventory ? `库位 ${lowestInventory.location_id} 的相符率最低，应优先抽盘。` : ""}
- AdventureWorks样例中，报废损失估值合计 **${money(summary.scrap_loss_amount)}**。${topScrap ? `最大的已记录原因是 ${topScrap.reason}。` : ""}`;

  return <article className="cost-report" aria-label="制造成本分析报告">
    <header className="report-hero">
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => {
          if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); }
        } : undefined}>{appTitle}</h1>
      <RichNarrative id="report:intro" className="report-deck"
        value="面向制造费用、项目成本、库存稽核和采购降本岗位的作品集分析。公开教学样例与仿真场景分开呈现，不代表真实企业绩效。" />
    </header>

    <ReportSection id="report-summary" queryId="executive_summary" sourceRows={summaryRows} showHeading={false}>
      <RichNarrative id="report-summary:body" className="report-summary-lead" value={executiveText} />
    </ReportSection>

    <section className="report-facts" aria-label="核心数字">
      <MetricCard id="report-metric-budget" title="预算执行率" queryId="executive_summary"
        sourceRows={summaryRows} value={pct(summary.budget_execution_rate)} description={`${money(summary.actual_amount)} / ${money(summary.budget_amount)}`} />
      <MetricCard id="report-metric-project" title="高风险项目" queryId="executive_summary"
        sourceRows={summaryRows} value={`${summary.high_risk_projects ?? 0}/${summary.project_count ?? 0}`} description={`预计超支 ${money(summary.forecast_project_overrun)}`} />
      <MetricCard id="report-metric-inventory" title="账实相符率" queryId="executive_summary"
        sourceRows={summaryRows} value={pct(summary.inventory_match_rate)} description={`差异绝对额 ${money(summary.inventory_absolute_variance)}`} />
    </section>

    <section className="report-section">
      <ReportSection id="report-budget" queryId="monthly_budget" sourceRows={monthly} showHeading={false}>
        <RichNarrative id="report-budget:body" value={`## 总额可控不等于过程无风险\n\n全年实际费用低于预算，但月份×部门×科目层面仍有 ${summary.red_warning_cells ?? 0} 个红色预警。月度趋势用于判断压力是持续还是局部发生，不直接证明管控措施的效果。`} />
      </ReportSection>
      <EvidenceChart id="report-budget-chart" queryId="monthly_budget" title="月度预算与实际费用"
        spec={budgetSpec} rows={monthly} sourceRows={monthly} height={320} />
    </section>

    <section className="report-section">
      <ReportSection id="report-project" queryId="project_risk" sourceRows={projects} showHeading={false}>
        <RichNarrative id="report-project:body" value={`## 项目风险应在完工前暴露\n\n高风险标记使用成本消耗率、物理进度和预计完工成本。它是仿真预警机制，用于展示动态成本管理方法，不是对真实项目的审计结论。`} />
      </ReportSection>
      <EvidenceChart id="report-project-chart" queryId="project_risk" title="项目预计超支"
        spec={projectSpec} rows={projects} sourceRows={projects} height={320} />
      <DataComponent id="report-project-table" queryId="project_risk" kind="table" title="高风险项目明细"
        sourceRows={projects} displayRows={highRisk}>
        <DataTable rows={highRisk} columns={projectColumns} rowKey="project_id" searchable={false} />
      </DataComponent>
    </section>

    <section className="report-section">
      <ReportSection id="report-observed" queryId="scrap_by_reason" sourceRows={scrap} showHeading={false}>
        <RichNarrative id="report-observed:body" value={`## 公开样例支撑报废与采购价差分析\n\nAdventureWorks中的报废原因可用于构建浪费复盘清单。${topPpv ? `${topPpv.product_name} 的采购价格差异在已纳入物料中最高，` : ""}但样例没有企业内部议价、合同和市场行情证据，因此只能定位复核对象，不能直接归因。`} />
      </ReportSection>
      <EvidenceChart id="report-scrap-chart" queryId="scrap_by_reason" title="报废损失原因"
        spec={scrapSpec} rows={scrap} sourceRows={scrap} height={340} />
    </section>

    <section className="report-section report-methods">
      <RichNarrative id="report:methods" value={`## 数据边界与使用方式\n\n- Microsoft AdventureWorks 为公开虚构教学数据，不是真实公司内部台账。\n- 预算、盘点、项目成本和浪费稽核使用固定随机种子 20260922 生成。\n- 采购价格差异已排除 ${summary.purchase_rows_excluded_zero_standard_cost ?? 0} 条标准成本为0、无可用基准的采购行。\n- AdventureWorks全期汇总不与2026年仿真数据拼接为同一条时间趋势。`} />
    </section>
  </article>;
}
