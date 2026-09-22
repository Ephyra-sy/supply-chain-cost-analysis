"""Build generated scenario tables and processed manufacturing KPI files."""

from __future__ import annotations

from pathlib import Path

from .adventureworks import load_core_tables
from .metrics import (
    budget_execution,
    inventory_variance,
    project_cost_forecast,
    purchase_price_variance,
    scrap_loss,
    work_order_cost_variance,
)
from .synthetic import ScenarioConfig, generate_scenario_tables


def build_manufacturing_outputs(project_root: str | Path, config: ScenarioConfig = ScenarioConfig()) -> dict[str, Path]:
    root = Path(project_root)
    raw_dir = root / "data" / "raw" / "adventureworks"
    generated_dir = root / "data" / "generated"
    processed_dir = root / "data" / "processed"
    generated_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    observed = load_core_tables(raw_dir)
    scenarios = generate_scenario_tables(observed, config)
    written: dict[str, Path] = {}
    for name, frame in scenarios.items():
        path = generated_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        written[name] = path

    metrics = {
        "budget_execution": budget_execution(scenarios["monthly_budget"], scenarios["expense_ledger"]),
        "work_order_cost_variance": work_order_cost_variance(observed["routing"]),
        "scrap_loss": scrap_loss(observed["work_orders"], observed["products"]),
        "inventory_variance": inventory_variance(scenarios["stocktake"]),
        "purchase_price_variance": purchase_price_variance(observed["purchases"], observed["products"]),
        "project_cost_forecast": project_cost_forecast(scenarios["project_master"], scenarios["project_cost"]),
    }
    for name, frame in metrics.items():
        path = processed_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        written[name] = path
    return written
