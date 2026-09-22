import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from src.manufacturing import (
    ScenarioConfig,
    budget_execution,
    generate_scenario_tables,
    inventory_variance,
    project_cost_forecast,
    purchase_price_variance,
    scrap_loss,
    work_order_cost_variance,
)


class ManufacturingModelTests(unittest.TestCase):
    def setUp(self):
        self.products = pd.DataFrame({"product_id": [1, 2], "standard_cost": [10.0, 20.0]})

    def test_scenario_is_reproducible_and_provenance_is_explicit(self):
        observed = {
            "products": self.products,
            "inventory": pd.DataFrame({"product_id": [1, 2], "location_id": [10, 20], "quantity": [100, 200]}),
        }
        config = ScenarioConfig(seed=42, expense_rows=48, projects=2)
        first = generate_scenario_tables(observed, config)
        second = generate_scenario_tables(observed, config)
        self.assertEqual(set(first), {"monthly_budget", "expense_ledger", "stocktake", "project_master", "project_cost", "waste_audit"})
        for name in first:
            assert_frame_equal(first[name], second[name])
            self.assertEqual(set(first[name]["source_class"]), {"synthetic_scenario"})

    def test_budget_execution_and_thresholds(self):
        budget = pd.DataFrame({
            "month": pd.to_datetime(["2026-01-01"] * 3),
            "department": ["A"] * 3,
            "account": ["green", "amber", "red"],
            "budget_amount": [100.0] * 3,
        })
        expense = budget.rename(columns={"budget_amount": "actual_amount"}).copy()
        expense["actual_amount"] = [80.0, 95.0, 110.0]
        result = budget_execution(budget, expense).set_index("account")
        self.assertEqual(result.loc["green", "warning_level"], "green")
        self.assertEqual(result.loc["amber", "warning_level"], "amber")
        self.assertEqual(result.loc["red", "warning_level"], "red")
        self.assertAlmostEqual(result.loc["red", "variance_amount"], 10.0)

    def test_cost_scrap_inventory_and_purchase_metrics(self):
        routing = pd.DataFrame({
            "work_order_id": [11, 11], "product_id": [1, 1],
            "planned_cost": [100.0, 50.0], "actual_cost": [120.0, 40.0],
            "planned_hours": [5.0, 2.0], "actual_hours": [6.0, 1.5],
        })
        variance = work_order_cost_variance(routing).iloc[0]
        self.assertAlmostEqual(variance["cost_variance"], 10.0)
        self.assertAlmostEqual(variance["cost_variance_rate"], 10 / 150)

        orders = pd.DataFrame({"work_order_id": [11], "product_id": [1], "scrap_quantity": [3]})
        self.assertAlmostEqual(scrap_loss(orders, self.products).iloc[0]["scrap_loss_amount"], 30.0)

        stock = pd.DataFrame({"book_quantity": [100], "counted_quantity": [97], "standard_cost": [10.0]})
        counted = inventory_variance(stock).iloc[0]
        self.assertEqual(counted["quantity_variance"], -3)
        self.assertEqual(counted["value_variance"], -30.0)
        self.assertFalse(counted["is_matched"])

        purchases = pd.DataFrame({
            "purchase_order_id": [21], "product_id": [1], "order_quantity": [10], "unit_price": [12.0]
        })
        self.assertEqual(purchase_price_variance(purchases, self.products).iloc[0]["purchase_price_variance"], 20.0)

    def test_project_forecast_and_zero_progress(self):
        projects = pd.DataFrame({
            "project_id": ["A", "B"], "target_cost": [1000.0, 1000.0], "completion_rate": [0.5, 0.0]
        })
        costs = pd.DataFrame({"project_id": ["A", "B"], "actual_amount": [600.0, 20.0]})
        result = project_cost_forecast(projects, costs).set_index("project_id")
        self.assertEqual(result.loc["A", "estimate_at_completion"], 1200.0)
        self.assertEqual(result.loc["A", "forecast_overrun"], 200.0)
        self.assertEqual(result.loc["A", "risk_level"], "high")
        self.assertTrue(np.isnan(result.loc["B", "estimate_at_completion"]))


if __name__ == "__main__":
    unittest.main()
