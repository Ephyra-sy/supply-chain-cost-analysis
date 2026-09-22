"""Build the reviewed JSON snapshot consumed by the report and dashboard apps."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
GENERATED = ROOT / "data" / "generated"
RAW = ROOT / "data" / "raw" / "adventureworks"


def _records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.copy()
    for column in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[column]):
            clean[column] = clean[column].dt.strftime("%Y-%m-%d")
    clean = clean.where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


def _source(label: str, files: list[str], classification: str, definitions: list[dict], assumptions=None) -> dict:
    source = {
        "label": label,
        "tables": files,
        "filters": ["Portfolio demonstration dataset; reporting year 2026 for scenario tables"],
        "assumptions": assumptions or [],
        "metricDefinitions": definitions,
        "classification": classification,
    }
    return source


def _read_raw(name: str) -> pd.DataFrame:
    schemas = json.loads((RAW / "schema.json").read_text(encoding="utf-8"))
    table_name = Path(name).stem
    if "tables" in schemas:
        fields = schemas["tables"][table_name]["columns"]
    elif "files" in schemas:
        fields = schemas["files"][name]["columns"]
    else:
        fields = schemas[name]
    if fields and isinstance(fields[0], dict):
        fields = [item["name"] for item in fields]
    return pd.read_csv(RAW / name, sep="\t", header=None, names=fields, na_values=["", "NULL"])


def build_snapshot() -> Path:
    budget = pd.read_csv(PROCESSED / "budget_execution.csv", parse_dates=["month"])
    inventory = pd.read_csv(PROCESSED / "inventory_variance.csv")
    projects = pd.read_csv(PROCESSED / "project_cost_forecast.csv")
    ppv = pd.read_csv(PROCESSED / "purchase_price_variance.csv")
    scrap = pd.read_csv(PROCESSED / "scrap_loss.csv")
    waste = pd.read_csv(GENERATED / "waste_audit.csv", parse_dates=["month"])

    product = _read_raw("Product.csv")
    work_order = _read_raw("WorkOrder.csv")
    scrap_reason = _read_raw("ScrapReason.csv")

    monthly_budget = (
        budget.groupby("month", as_index=False)
        .agg(budget_amount=("budget_amount", "sum"), actual_amount=("actual_amount", "sum"), red_cells=("warning_level", lambda s: int((s == "red").sum())))
    )
    monthly_budget["variance_amount"] = monthly_budget["actual_amount"] - monthly_budget["budget_amount"]
    monthly_budget["execution_rate"] = monthly_budget["actual_amount"] / monthly_budget["budget_amount"]

    department_budget = (
        budget.groupby("department", as_index=False)
        .agg(budget_amount=("budget_amount", "sum"), actual_amount=("actual_amount", "sum"), red_cells=("warning_level", lambda s: int((s == "red").sum())))
    )
    department_budget["variance_amount"] = department_budget["actual_amount"] - department_budget["budget_amount"]
    department_budget["execution_rate"] = department_budget["actual_amount"] / department_budget["budget_amount"]
    department_budget = department_budget.sort_values("execution_rate", ascending=False)

    account_budget = budget.groupby("account", as_index=False).agg(
        budget_amount=("budget_amount", "sum"), actual_amount=("actual_amount", "sum")
    )
    account_budget["variance_amount"] = account_budget["actual_amount"] - account_budget["budget_amount"]
    account_budget["execution_rate"] = account_budget["actual_amount"] / account_budget["budget_amount"]
    account_budget = account_budget.sort_values("actual_amount", ascending=False)

    inv_location = inventory.groupby("location_id", as_index=False).agg(
        records=("product_id", "size"), matched=("is_matched", "sum"),
        book_quantity=("book_quantity", "sum"), counted_quantity=("counted_quantity", "sum"),
        value_variance=("value_variance", "sum"), absolute_value_variance=("value_variance", lambda s: float(s.abs().sum())),
    )
    inv_location["match_rate"] = inv_location["matched"] / inv_location["records"]

    project_view = projects[[
        "project_id", "project_name", "target_cost", "completion_rate", "actual_amount",
        "cost_consumption_rate", "estimate_at_completion", "forecast_overrun", "risk_level",
    ]].sort_values(["risk_level", "forecast_overrun"], ascending=[True, False])

    waste_type = waste.groupby("waste_type", as_index=False).agg(
        waste_amount=("waste_amount", "sum"), incidents=("audit_id", "size"), quantity=("quantity", "sum")
    ).sort_values("waste_amount", ascending=False)
    waste_monthly = waste.groupby("month", as_index=False).agg(waste_amount=("waste_amount", "sum"), incidents=("audit_id", "size"))

    work_order.columns = [str(c).strip().lower() for c in work_order.columns]
    product.columns = [str(c).strip().lower() for c in product.columns]
    scrap_reason.columns = [str(c).strip().lower() for c in scrap_reason.columns]
    # schema.json uses Microsoft names; normalize the few fields used below.
    rename = {
        "workorderid": "work_order_id", "productid": "product_id", "scrappedqty": "scrap_quantity",
        "scrapreasonid": "scrap_reason_id", "startdate": "start_date", "standardcost": "standard_cost",
        "name": "name", "scrapreasonid": "scrap_reason_id",
    }
    work_order = work_order.rename(columns=rename)
    product = product.rename(columns=rename)
    scrap_reason = scrap_reason.rename(columns=rename)
    if "scrap_quantity" not in work_order and "scrapqty" in work_order:
        work_order = work_order.rename(columns={"scrapqty": "scrap_quantity"})
    wo_scrap = work_order[["product_id", "scrap_quantity", "scrap_reason_id", "start_date"]].copy()
    wo_scrap["start_date"] = pd.to_datetime(wo_scrap["start_date"], errors="coerce")
    wo_scrap = wo_scrap.merge(product[["product_id", "standard_cost"]], on="product_id", how="left")
    reason_name = "name" if "name" in scrap_reason else scrap_reason.columns[1]
    wo_scrap = wo_scrap.merge(scrap_reason[["scrap_reason_id", reason_name]], on="scrap_reason_id", how="left")
    wo_scrap["reason"] = wo_scrap[reason_name].fillna("未记录原因")
    wo_scrap["scrap_loss_amount"] = wo_scrap["scrap_quantity"] * wo_scrap["standard_cost"]
    scrap_by_reason = wo_scrap.groupby("reason", as_index=False).agg(
        scrap_loss_amount=("scrap_loss_amount", "sum"), scrap_quantity=("scrap_quantity", "sum"), work_orders=("product_id", "size")
    ).sort_values("scrap_loss_amount", ascending=False).head(12)

    product_names = product[["product_id", "name"]].rename(columns={"name": "product_name"}) if "name" in product else product[["product_id"]].assign(product_name=lambda x: x.product_id.astype(str))
    valid_ppv = ppv.loc[ppv["standard_cost"] > 0].copy()
    excluded_ppv_rows = int((ppv["standard_cost"] <= 0).sum())
    ppv_product = valid_ppv.merge(product_names, on="product_id", how="left")
    ppv_product = ppv_product.groupby(["product_id", "product_name"], as_index=False).agg(
        purchase_price_variance=("purchase_price_variance", "sum"), order_quantity=("order_quantity", "sum"),
        purchase_orders=("purchase_order_id", "nunique")
    ).sort_values("purchase_price_variance", ascending=False).head(12)

    total_budget = float(budget["budget_amount"].sum())
    total_actual = float(budget["actual_amount"].sum())
    total_project_overrun = float(projects["forecast_overrun"].clip(lower=0).sum())
    summary = pd.DataFrame([{
        "budget_amount": total_budget,
        "actual_amount": total_actual,
        "budget_execution_rate": total_actual / total_budget,
        "red_warning_cells": int((budget["warning_level"] == "red").sum()),
        "inventory_match_rate": float(inventory["is_matched"].mean()),
        "inventory_absolute_variance": float(inventory["value_variance"].abs().sum()),
        "scrap_loss_amount": float(scrap["scrap_loss_amount"].sum()),
        "purchase_price_variance": float(valid_ppv["purchase_price_variance"].sum()),
        "purchase_rows_excluded_zero_standard_cost": excluded_ppv_rows,
        "high_risk_projects": int((projects["risk_level"] == "high").sum()),
        "project_count": int(len(projects)),
        "forecast_project_overrun": total_project_overrun,
    }])

    common_assumptions = [
        "AdventureWorks records are Microsoft fictional teaching data, not a real company's results.",
        "Budget, stocktake, project and waste records are reproducible scenarios generated with seed 20260922.",
        "Currency values are scenario units and are displayed as ¥-equivalent solely for portfolio presentation.",
    ]

    queries = {
        "executive_summary": {
            "rows": _records(summary),
            "source": _source("Manufacturing cost control summary", ["data/processed/*.csv"], "mixed_sample_and_scenario", [
                {"label": "预算执行率", "definition": "仿真费用实际额合计 ÷ 仿真预算额合计。", "componentIds": ["kpi-budget", "report-summary"]},
                {"label": "账实相符率", "definition": "盘点数量等于账面数量的库位产品记录数 ÷ 全部盘点记录数。", "componentIds": ["kpi-inventory", "inventory-location"]},
                {"label": "高风险项目", "definition": "成本消耗快于进度15个百分点或预计完工成本超目标的仿真项目。", "componentIds": ["kpi-project", "project-risk"]},
            ], common_assumptions),
        },
        "monthly_budget": {"rows": _records(monthly_budget), "source": _source("月度预算与费用场景", ["monthly_budget.csv", "expense_ledger.csv"], "synthetic_scenario", [], common_assumptions)},
        "department_budget": {"rows": _records(department_budget), "source": _source("部门预算执行场景", ["budget_execution.csv"], "synthetic_scenario", [], common_assumptions)},
        "account_budget": {"rows": _records(account_budget), "source": _source("费用科目结构场景", ["budget_execution.csv"], "synthetic_scenario", [], common_assumptions)},
        "inventory_by_location": {"rows": _records(inv_location), "source": _source("仓库盘点场景", ["ProductInventory.csv", "stocktake.csv"], "synthetic_scenario_anchored_to_sample", [], common_assumptions)},
        "project_risk": {"rows": _records(project_view), "source": _source("项目成本组合场景", ["project_master.csv", "project_cost.csv"], "synthetic_scenario", [], common_assumptions)},
        "waste_by_type": {"rows": _records(waste_type), "source": _source("浪费稽核场景", ["waste_audit.csv"], "synthetic_scenario", [], common_assumptions)},
        "waste_monthly": {"rows": _records(waste_monthly), "source": _source("月度浪费趋势场景", ["waste_audit.csv"], "synthetic_scenario", [], common_assumptions)},
        "scrap_by_reason": {"rows": _records(scrap_by_reason), "source": _source("AdventureWorks 报废原因", ["WorkOrder.csv", "Product.csv", "ScrapReason.csv"], "observed_fictional_sample", [], common_assumptions)},
        "purchase_price_variance": {"rows": _records(ppv_product), "source": _source("AdventureWorks 采购价格差异", ["PurchaseOrderDetail.csv", "Product.csv"], "observed_fictional_sample", [], common_assumptions + [f"Excluded {excluded_ppv_rows} purchase lines whose standard cost was zero; their price variance has no usable baseline."])},
    }

    snapshot = {
        "surface": "dashboard",
        "title": "制造成本管控",
        "generatedAt": pd.Timestamp.now(tz="UTC").isoformat(),
        "buildStatus": "creating",
        "status": "reviewed_portfolio_sample",
        "filters": [{"id": "month", "label": "月份", "field": "month", "defaultValue": "all"}],
        "queries": queries,
    }
    output = ROOT / "data" / "reviewed_snapshot.json"
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    print(build_snapshot())
