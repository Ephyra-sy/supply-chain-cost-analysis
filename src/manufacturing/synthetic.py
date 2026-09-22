"""Reproducible scenario tables grounded in normalized sample observations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


OBSERVED = "observed_sample"
SYNTHETIC = "synthetic_scenario"


@dataclass(frozen=True)
class ScenarioConfig:
    seed: int = 20260922
    year: int = 2026
    departments: tuple[str, ...] = ("生产一部", "生产二部", "设备部", "质量部", "仓储部", "采购部")
    accounts: tuple[str, ...] = ("直接材料", "直接人工", "能源费", "维修费", "折旧费", "其他制造费")
    projects: int = 10
    expense_rows: int = 2400


def _tag(frame: pd.DataFrame, note: str) -> pd.DataFrame:
    frame = frame.copy()
    frame["source_class"] = SYNTHETIC
    frame["source_note"] = note
    return frame


def _product_sample(observed: dict[str, pd.DataFrame]) -> pd.DataFrame:
    products = observed.get("products")
    if products is None or products.empty:
        return pd.DataFrame({"product_id": range(1, 21), "standard_cost": np.linspace(80, 800, 20)})
    required = {"product_id", "standard_cost"}
    if not required.issubset(products.columns):
        raise ValueError(f"products must contain normalized fields: {sorted(required)}")
    return products.loc[:, ["product_id", "standard_cost"]].dropna().drop_duplicates("product_id")


def generate_scenario_tables(
    observed: dict[str, pd.DataFrame] | None = None,
    config: ScenarioConfig = ScenarioConfig(),
) -> dict[str, pd.DataFrame]:
    """Generate finance-control scenario data with a fixed random seed.

    ``observed`` may contain normalized AdventureWorks-style ``products`` and
    ``inventory`` tables.  Its values are only used as anchors; all returned
    records are labelled synthetic scenarios.
    """
    observed = observed or {}
    rng = np.random.default_rng(config.seed)
    months = pd.date_range(f"{config.year}-01-01", periods=12, freq="MS")
    products = _product_sample(observed)

    # Budgets contain a mild seasonal pattern; amounts are currency units.
    budget_grid = pd.MultiIndex.from_product(
        [months, config.departments, config.accounts], names=["month", "department", "account"]
    ).to_frame(index=False)
    account_base = dict(zip(config.accounts, [900_000, 260_000, 180_000, 90_000, 150_000, 75_000]))
    budget_grid["budget_amount"] = [
        account_base[a] * (0.86 + 0.04 * m.month) * rng.uniform(0.88, 1.12)
        for m, a in zip(budget_grid["month"], budget_grid["account"])
    ]
    budget_grid["budget_amount"] = budget_grid["budget_amount"].round(2)
    budgets = _tag(budget_grid, "Scenario budget generated from disclosed seasonal rules")

    # Expense ledger is allocated across budget cells; several cells are
    # deliberately stressed to make the warning workflow demonstrable.
    # Allocate a near-equal count of ledger lines to each cell.  This avoids
    # accidental "overspend" caused only by uneven random row counts.
    sampled_index = np.arange(config.expense_rows) % len(budget_grid)
    cells = budget_grid.iloc[rng.permutation(sampled_index)].reset_index(drop=True)
    counts = cells.groupby(["month", "department", "account"])["budget_amount"].transform("size")
    per_cell_budget = cells["budget_amount"].to_numpy() / counts.to_numpy()
    stress = np.where(
        (cells["department"] == "生产一部") & (cells["account"].isin(["直接材料", "能源费"])),
        1.28,
        0.90,
    )
    expenses = cells[["month", "department", "account"]].copy()
    expenses.insert(0, "expense_id", [f"EXP-{i:06d}" for i in range(1, len(expenses) + 1)])
    expenses["actual_amount"] = (per_cell_budget * stress * rng.lognormal(0, 0.10, len(cells))).round(2)
    expenses["document_status"] = rng.choice(["approved", "pending_review"], len(cells), p=[0.96, 0.04])
    expenses = _tag(expenses, "Scenario expense ledger; stress injected into Production 1 material and energy")

    # Count quantities are generated around the observed sample inventory, or
    # around a fallback book balance when no inventory table is available.
    inventory = observed.get("inventory")
    if inventory is not None and not inventory.empty:
        needed = {"product_id", "location_id", "quantity"}
        if not needed.issubset(inventory.columns):
            raise ValueError(f"inventory must contain normalized fields: {sorted(needed)}")
        stocktake = inventory[["product_id", "location_id", "quantity"]].rename(columns={"quantity": "book_quantity"}).copy()
    else:
        n = min(60, max(12, len(products) * 3))
        stocktake = pd.DataFrame({
            "product_id": rng.choice(products["product_id"], n, replace=True),
            "location_id": rng.integers(1, 7, n),
            "book_quantity": rng.integers(30, 600, n),
        }).groupby(["product_id", "location_id"], as_index=False)["book_quantity"].sum()
    stocktake = stocktake.merge(products, on="product_id", how="left", validate="many_to_one")
    errors = rng.choice([0, -3, -1, 1, 2], len(stocktake), p=[0.94, 0.01, 0.015, 0.02, 0.015])
    stocktake["counted_quantity"] = (stocktake["book_quantity"] + errors).clip(lower=0)
    stocktake["count_date"] = pd.Timestamp(config.year, 12, 31)
    stocktake = _tag(stocktake, "Book balance anchored to sample data when supplied; physical count is simulated")

    project_names = ["电芯产线扩产", "自动化设备升级", "仓储数字化改造", "能源管理改造", "新型号电池研发"]
    project_count = config.projects
    projects = pd.DataFrame({
        "project_id": [f"PRJ-{i:03d}" for i in range(1, project_count + 1)],
        "project_name": [project_names[i % len(project_names)] + f"-{i + 1}" for i in range(project_count)],
        "target_cost": rng.integers(1_500_000, 12_000_000, project_count).astype(float),
        "completion_rate": rng.uniform(0.25, 0.95, project_count).round(3),
    })
    projects = _tag(projects, "Portfolio scenario; names and targets are fictitious")

    cost_types = np.array(["材料", "人工", "设备", "外包", "差旅及其他"])
    rows: list[dict[str, object]] = []
    entry_id = 1
    for row in projects.itertuples(index=False):
        completion_cost_multiplier = rng.choice([0.88, 0.95, 1.02, 1.12], p=[0.25, 0.45, 0.20, 0.10])
        cost_ratio = completion_cost_multiplier * row.completion_rate
        project_actual = row.target_cost * cost_ratio
        weights = rng.dirichlet([4.0, 2.0, 5.0, 1.5, 0.5])
        for month in months[months <= months[min(11, int(np.ceil(row.completion_rate * 12)) - 1)]]:
            for cost_type, weight in zip(cost_types, weights):
                rows.append({
                    "cost_entry_id": f"PC-{entry_id:06d}",
                    "project_id": row.project_id,
                    "month": month,
                    "cost_type": cost_type,
                    "actual_amount": project_actual * weight / max(1, int(np.ceil(row.completion_rate * 12))),
                })
                entry_id += 1
    project_costs = pd.DataFrame(rows)
    project_costs["actual_amount"] = project_costs["actual_amount"].round(2)
    project_costs = _tag(project_costs, "Costs allocated from disclosed progress/cost-ratio scenario")

    waste_types = np.array(["报废", "返工", "材料超耗", "设备停机", "能源超耗", "非计划领料"])
    waste_n = min(600, max(100, len(products) * 12))
    waste = pd.DataFrame({
        "audit_id": [f"WST-{i:05d}" for i in range(1, waste_n + 1)],
        "month": rng.choice(months, waste_n),
        "department": rng.choice(config.departments[:4], waste_n),
        "product_id": rng.choice(products["product_id"], waste_n),
        "waste_type": rng.choice(waste_types, waste_n, p=[0.23, 0.18, 0.25, 0.10, 0.14, 0.10]),
        "quantity": rng.integers(1, 18, waste_n),
    }).merge(products, on="product_id", how="left", validate="many_to_one")
    waste["waste_amount"] = (waste["quantity"] * waste["standard_cost"] * rng.uniform(0.35, 1.15, waste_n)).round(2)
    waste["root_cause"] = rng.choice(["工艺参数", "设备精度", "来料质量", "计划变更", "操作偏差"], waste_n)
    waste = _tag(waste, "Waste audit scenario calibrated to supplied product standard costs")

    return {
        "monthly_budget": budgets,
        "expense_ledger": expenses,
        "stocktake": stocktake,
        "project_master": projects,
        "project_cost": project_costs,
        "waste_audit": waste,
    }
