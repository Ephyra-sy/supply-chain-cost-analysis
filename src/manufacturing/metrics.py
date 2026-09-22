"""Auditable manufacturing-finance calculations on normalized tables."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _require(frame: pd.DataFrame, columns: set[str], table: str) -> None:
    missing = sorted(columns.difference(frame.columns))
    if missing:
        raise ValueError(f"{table} missing required columns: {', '.join(missing)}")


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.astype(float)
    return numerator.astype(float).div(denominator.where(denominator.ne(0)))


def budget_execution(budget: pd.DataFrame, expenses: pd.DataFrame) -> pd.DataFrame:
    """Return monthly department/account budget execution and warning level."""
    keys = ["month", "department", "account"]
    _require(budget, set(keys + ["budget_amount"]), "budget")
    _require(expenses, set(keys + ["actual_amount"]), "expenses")
    planned = budget.groupby(keys, as_index=False)["budget_amount"].sum()
    actual = expenses.groupby(keys, as_index=False)["actual_amount"].sum()
    result = planned.merge(actual, on=keys, how="left").fillna({"actual_amount": 0.0})
    result["variance_amount"] = result["actual_amount"] - result["budget_amount"]
    result["execution_rate"] = _safe_divide(result["actual_amount"], result["budget_amount"])
    result["warning_level"] = np.select(
        [result["execution_rate"] > 1.0, result["execution_rate"] >= 0.9],
        ["red", "amber"],
        default="green",
    )
    # Budget and expense ledgers are disclosed scenario data in this project.
    result["source_class"] = "synthetic_scenario"
    result["source_note"] = "Calculated from synthetic budget and expense scenario"
    return result.sort_values(keys).reset_index(drop=True)


def work_order_cost_variance(routing: pd.DataFrame) -> pd.DataFrame:
    """Aggregate AdventureWorks routing planned/actual costs by work order.

    Normalized fields mirror ``Production.WorkOrderRouting``.
    """
    required = {"work_order_id", "product_id", "planned_cost", "actual_cost"}
    _require(routing, required, "routing")
    aggregations: dict[str, tuple[str, str]] = {
        "planned_cost": ("planned_cost", "sum"),
        "actual_cost": ("actual_cost", "sum"),
    }
    if {"planned_hours", "actual_hours"}.issubset(routing.columns):
        aggregations.update({
            "planned_hours": ("planned_hours", "sum"),
            "actual_hours": ("actual_hours", "sum"),
        })
    result = routing.groupby(["work_order_id", "product_id"], as_index=False).agg(**aggregations)
    result["cost_variance"] = result["actual_cost"] - result["planned_cost"]
    result["cost_variance_rate"] = _safe_divide(result["cost_variance"], result["planned_cost"])
    if {"planned_hours", "actual_hours"}.issubset(result.columns):
        result["hours_variance"] = result["actual_hours"] - result["planned_hours"]
    result["source_class"] = "observed_sample"
    return result


def scrap_loss(work_orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Value recorded scrap quantity at product standard cost."""
    _require(work_orders, {"work_order_id", "product_id", "scrap_quantity"}, "work_orders")
    _require(products, {"product_id", "standard_cost"}, "products")
    result = work_orders[["work_order_id", "product_id", "scrap_quantity"]].merge(
        products[["product_id", "standard_cost"]], on="product_id", how="left", validate="many_to_one"
    )
    if result["standard_cost"].isna().any():
        missing = result.loc[result["standard_cost"].isna(), "product_id"].drop_duplicates().tolist()
        raise ValueError(f"products missing standard cost for product_id: {missing}")
    result["scrap_loss_amount"] = result["scrap_quantity"] * result["standard_cost"]
    result["source_class"] = "observed_sample"
    return result


def inventory_variance(stocktake: pd.DataFrame) -> pd.DataFrame:
    """Calculate count variance in units and currency."""
    _require(stocktake, {"book_quantity", "counted_quantity", "standard_cost"}, "stocktake")
    result = stocktake.copy()
    result["quantity_variance"] = result["counted_quantity"] - result["book_quantity"]
    result["value_variance"] = result["quantity_variance"] * result["standard_cost"]
    result["is_matched"] = result["quantity_variance"].eq(0)
    return result


def purchase_price_variance(purchases: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Calculate actual purchase price variance against product standard cost."""
    _require(purchases, {"purchase_order_id", "product_id", "order_quantity", "unit_price"}, "purchases")
    _require(products, {"product_id", "standard_cost"}, "products")
    result = purchases.merge(
        products[["product_id", "standard_cost"]], on="product_id", how="left", validate="many_to_one"
    )
    if result["standard_cost"].isna().any():
        raise ValueError("purchase records contain product_id without standard_cost")
    result["price_variance_per_unit"] = result["unit_price"] - result["standard_cost"]
    result["purchase_price_variance"] = result["order_quantity"] * result["price_variance_per_unit"]
    result["source_class"] = "observed_sample"
    return result


def project_cost_forecast(projects: pd.DataFrame, costs: pd.DataFrame) -> pd.DataFrame:
    """Calculate cost consumption and estimate-at-completion (EAC).

    EAC uses actual cost / physical progress.  A zero-progress project has no
    defensible EAC and is returned as NaN instead of infinity.
    """
    _require(projects, {"project_id", "target_cost", "completion_rate"}, "projects")
    _require(costs, {"project_id", "actual_amount"}, "costs")
    actual = costs.groupby("project_id", as_index=False)["actual_amount"].sum()
    result = projects.merge(actual, on="project_id", how="left").fillna({"actual_amount": 0.0})
    result["cost_consumption_rate"] = _safe_divide(result["actual_amount"], result["target_cost"])
    result["estimate_at_completion"] = _safe_divide(result["actual_amount"], result["completion_rate"])
    result["forecast_overrun"] = result["estimate_at_completion"] - result["target_cost"]
    progress_gap = result["cost_consumption_rate"] - result["completion_rate"]
    result["risk_level"] = np.select(
        [(progress_gap > 0.15) | (result["forecast_overrun"] > 0), progress_gap > 0.05],
        ["high", "medium"],
        default="low",
    )
    return result
