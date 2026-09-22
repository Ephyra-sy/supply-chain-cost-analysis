"""Manufacturing finance scenario model.

The package deliberately separates public sample observations from synthetic
scenario records.  It is independent of the existing supply-chain pipeline.
"""

from .metrics import (
    budget_execution,
    inventory_variance,
    project_cost_forecast,
    purchase_price_variance,
    scrap_loss,
    work_order_cost_variance,
)
from .build import build_manufacturing_outputs
from .synthetic import ScenarioConfig, generate_scenario_tables

__all__ = [
    "ScenarioConfig",
    "generate_scenario_tables",
    "budget_execution",
    "work_order_cost_variance",
    "scrap_loss",
    "inventory_variance",
    "purchase_price_variance",
    "project_cost_forecast",
    "build_manufacturing_outputs",
]
