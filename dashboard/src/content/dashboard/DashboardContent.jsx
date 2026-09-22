import React from "react";

import {
  DataComponent, DataTable, EvidenceChart, MetricCard, useDataApp,
} from "../../data-app-public.jsx";
import "./example.css";

const money = (value, compact = true) => new Intl.NumberFormat("zh-CN", {
  style: "currency", currency: "CNY", notation: compact ? "compact" : "standard",
  maximumFractionDigits: compact ? 1 : 0,
}).format(Number(value ?? 0));
const pct = (value) => `${(Number(value ?? 0) * 100).toFixed(1)}%`;

const monthlyBudgetSpec = {
  type: "line", x: "month", y: "budget_amount", fields: ["budget_amount", "actual_amount"],
  currency: "CNY", valueDecimals: 0,
  colors: { budget_amount: "var(--secondary)", actual_amount: "var(--chart-1)" },
  legend: { labels: { budget_amount: "预算", actual_amount: "实际" } },
};
const departmentSpec = {
  type: "horizontalBar", x: "department", y: "Execution (%)", valueDecimals: 1,
  colors: { "Execution (%)": "var(--chart-2)" },
};
const wasteSpec = {
  type: "bar", x: "waste_type", y: "waste_amount", currency: "CNY", valueDecimals: 0,
  colors: { waste_amount: "var(--chart-4)" },
};
const scrapSpec = {
  type: "horizontalBar", x: "reason", y: "scrap_loss_amount", currency: "CNY", valueDecimals: 0,
  colors: { scrap_loss_amount: "var(--chart-5)" },
};
const ppvSpec = {
  type: "horizontalBar", x: "product_name", y: "purchase_price_variance", currency: "CNY", valueDecimals: 0,
  colors: { purchase_price_variance: "var(--chart-3)" },
};

export function DashboardContent() {
  const { reviewedRows, visible } = useDataApp();
  const summaryRows = reviewedRows("executive_summary");
  const [summary = {}] = summaryRows;
  const monthly = reviewedRows("monthly_budget");
  const departmentSourceRows = reviewedRows("department_budget");
  const departments = departmentSourceRows.map((row) => ({
    ...row,
    "Execution (%)": row.execution_rate * 100,
  }));
  const waste = reviewedRows("waste_by_type");
  const projects = reviewedRows("project_risk");
  const inventory = reviewedRows("inventory_by_location");
  const scrap = reviewedRows("scrap_by_reason");
  const ppv = reviewedRows("purchase_price_variance");

  const projectColumns = [
    { key: "project_name", label: "项目" },
    { key: "completion_rate", label: "完成进度", renderCell: (v) => pct(v) },
    { key: "cost_consumption_rate", label: "成本消耗", renderCell: (v) => pct(v) },
    { key: "estimate_at_completion", label: "预计完工成本", renderCell: (v) => money(v, false) },
    { key: "forecast_overrun", label: "预计超支", renderCell: (v) => money(v, false) },
    { key: "risk_level", label: "风险" },
  ];
  const inventoryColumns = [
    { key: "location_id", label: "库位" },
    { key: "records", label: "盘点记录" },
    { key: "match_rate", label: "相符率", renderCell: (v) => pct(v) },
    { key: "book_quantity", label: "账面数量" },
    { key: "counted_quantity", label: "盘点数量" },
    { key: "absolute_value_variance", label: "差异绝对额", renderCell: (v) => money(v, false) },
  ];

  return <article className="cost-dashboard" aria-label="制造成本管控看板">
    <section className="dashboard-intro">
      <p>预算、盘点、项目和浪费为可复现仿真场景；报废与采购价差来自 Microsoft AdventureWorks 虚构教学样例。</p>
    </section>

    <section className="kpi-grid" aria-label="核心指标">
      {visible("kpi-budget") && <MetricCard id="kpi-budget" title="预算执行率" queryId="executive_summary"
        sourceRows={summaryRows} value={pct(summary.budget_execution_rate)}
        description={`${money(summary.actual_amount)} / ${money(summary.budget_amount)}`} />}
      {visible("kpi-warning") && <MetricCard id="kpi-warning" title="红色预警" queryId="executive_summary"
        sourceRows={summaryRows} value={String(summary.red_warning_cells ?? 0)}
        description="月份×部门×科目中实际额超预算的组合" />}
      {visible("kpi-inventory") && <MetricCard id="kpi-inventory" title="账实相符率" queryId="executive_summary"
        sourceRows={summaryRows} value={pct(summary.inventory_match_rate)}
        description={`差异绝对额 ${money(summary.inventory_absolute_variance)}`} />}
      {visible("kpi-project") && <MetricCard id="kpi-project" title="高风险项目" queryId="executive_summary"
        sourceRows={summaryRows} value={`${summary.high_risk_projects ?? 0}/${summary.project_count ?? 0}`}
        description={`预计超支合计 ${money(summary.forecast_project_overrun)}`} />}
    </section>

    <section className="chart-grid chart-grid--wide">
      <EvidenceChart id="chart-budget-monthly" queryId="monthly_budget" title="月度预算与实际费用"
        description="2026年仿真场景；按月汇总全部部门和费用科目。"
        spec={monthlyBudgetSpec} rows={monthly} sourceRows={monthly} height={310} />
      <EvidenceChart id="chart-budget-department" queryId="department_budget" title="部门预算执行率"
        description="实际费用除以预算，由高到低用于定位费用压力。"
        spec={departmentSpec} rows={departments} sourceRows={departmentSourceRows} height={310} />
    </section>

    <section className="chart-grid">
      <EvidenceChart id="chart-waste-type" queryId="waste_by_type" title="浪费金额结构"
        description="仿真稽核场景；展示报废、返工、超耗等类型的金额。"
        spec={wasteSpec} rows={waste} sourceRows={waste} height={280} />
      <EvidenceChart id="chart-scrap-reason" queryId="scrap_by_reason" title="报废损失原因"
        description="AdventureWorks全期样例；报废数量按产品标准成本计价。"
        spec={scrapSpec} rows={scrap} sourceRows={scrap} height={280} />
    </section>

    <section className="table-grid">
      <DataComponent id="project-risk" queryId="project_risk" kind="table" title="项目成本风险"
        description="仿真项目组合；预计完工成本=累计实际成本÷完成进度。"
        sourceRows={projects} displayRows={projects}>
        <DataTable rows={projects} columns={projectColumns} rowKey="project_id" searchable={false} />
      </DataComponent>
      <DataComponent id="inventory-location" queryId="inventory_by_location" kind="table" title="库位盘点差异"
        description="库位编号来自公开样例，实盘数为仿真场景。"
        sourceRows={inventory} displayRows={inventory}>
        <DataTable rows={inventory} columns={inventoryColumns} rowKey="location_id" searchable={false} />
      </DataComponent>
    </section>

    <section className="chart-grid chart-grid--single">
      <EvidenceChart id="chart-product-ppv" queryId="purchase_price_variance" title="物料采购价格差异"
        description="AdventureWorks全期样例；已排除标准成本为0、无可用基准的采购行。"
        spec={ppvSpec} rows={ppv} sourceRows={ppv} height={360} />
    </section>
  </article>;
}
