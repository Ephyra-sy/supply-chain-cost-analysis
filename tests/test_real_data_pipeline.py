import unittest

from src.real_data_pipeline import (
    build_analysis_tables,
    build_energy_cost_scenarios,
    build_shipment_review_queue,
    load_energy,
    load_shipments,
)


class RealDataPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shipments = load_shipments()
        cls.energy = load_energy()
        cls.tables = build_analysis_tables()

    def test_source_row_counts_and_dates(self):
        self.assertEqual(len(self.shipments), 10_324)
        self.assertEqual(len(self.energy), 35_040)
        self.assertEqual(self.shipments["delivered to client date"].isna().sum(), 0)
        self.assertEqual(self.energy["timestamp"].isna().sum(), 0)

    def test_shipment_metrics_keep_missing_freight_visible(self):
        summary = self.tables["executive_summary"].iloc[0]
        self.assertAlmostEqual(summary["on_time_rate"], 0.8851220457, places=8)
        self.assertAlmostEqual(summary["freight_numeric_coverage"], 0.6003487021, places=8)
        self.assertAlmostEqual(summary["known_freight_usd"], 68_817_849.41, places=2)
        self.assertLess(summary["freight_numeric_coverage"], 1.0)

    def test_energy_aggregation_reconciles_to_raw(self):
        summary = self.tables["executive_summary"].iloc[0]
        monthly_total = self.tables["energy_monthly"]["usage_kwh"].sum()
        self.assertAlmostEqual(summary["energy_usage_kwh"], 959_636.71, places=2)
        self.assertAlmostEqual(monthly_total, self.energy["Usage_kWh"].sum(), places=6)
        self.assertEqual(summary["peak_energy_month"], "2018-01")

    def test_mode_aggregation_reconciles_to_raw(self):
        by_mode = self.tables["shipment_by_mode"]
        self.assertEqual(int(by_mode["shipment_lines"].sum()), len(self.shipments))
        self.assertEqual(set(by_mode["shipment mode"]), {"Air", "Air Charter", "Ocean", "Truck", "未记录"})

    def test_lane_matrix_reconciles_and_has_string_key(self):
        lanes = self.tables["shipment_cost_delivery_matrix"]
        self.assertEqual(int(lanes["shipment_lines"].sum()), len(self.shipments))
        self.assertTrue(lanes["lane_key"].map(type).eq(str).all())
        self.assertTrue({"shipment_mode", "manufacturing_site", "late_lines", "late_rate"}.issubset(lanes.columns))
        self.assertAlmostEqual(lanes["known_freight_usd"].sum(), self.shipments["freight_cost_usd_numeric"].sum(), places=2)
        self.assertTrue(lanes["freight_numeric_coverage"].between(0, 1).all())

    def test_review_queue_traceability_and_triggers(self):
        queue = self.tables["shipment_review_queue"]
        self.assertGreater(len(queue), 0)
        self.assertTrue(queue["review_id"].str.startswith("usaid-").all())
        self.assertEqual(queue["id"].nunique(), len(queue))
        self.assertTrue(queue["review_status"].eq("待人工核实").all())
        self.assertTrue({"source_shipment_id", "project_code", "po_so_number", "priority", "evidence_summary", "suggested_owner"}.issubset(queue.columns))
        self.assertEqual(set(queue["priority"]), {"P1", "P2", "P3"})
        self.assertTrue(queue["trigger_codes"].str.len().gt(0).all())
        # Unquantified freight is a distinct review reason and never appears as a numeric zero.
        unknown = queue[queue["trigger_freight_unquantified"]]
        self.assertGreater(len(unknown), 0)
        self.assertTrue(unknown["freight_cost_usd_numeric"].isna().all())
        self.assertTrue(unknown["freight_status"].ne("numeric_amount").all())

    def test_energy_profile_grain_demand_and_scenario_range(self):
        profile = self.tables["energy_period_profile"]
        self.assertEqual(
            set(profile.columns),
            {"week_status", "tariff_period", "load_type", "usage_kwh", "observations", "average_interval_kwh", "max_interval_kwh", "observed_peak_kw", "interval_minutes", "profile_key"},
        )
        self.assertEqual(int(profile["observations"].sum()), len(self.energy))
        self.assertAlmostEqual(profile["usage_kwh"].sum(), self.energy["Usage_kWh"].sum(), places=6)
        self.assertEqual(set(profile["tariff_period"]), {"峰", "平", "谷"})
        self.assertTrue(profile["profile_key"].is_unique)
        monthly = self.tables["energy_monthly_demand"]
        self.assertEqual(len(monthly), 12)
        self.assertTrue(monthly["observed_peak_kw"].ge(0).all())
        scenarios = self.tables["energy_cost_scenarios"].set_index("scenario")
        self.assertEqual(scenarios.loc["基准情景", "load_shift_share"], 0)
        self.assertEqual(scenarios.loc["基准情景", "peak_shave_share"], 0)
        self.assertLess(scenarios.loc["强化优化", "modeled_total_cost_cny"], scenarios.loc["轻度优化", "modeled_total_cost_cny"])
        self.assertLess(scenarios.loc["轻度优化", "modeled_total_cost_cny"], scenarios.loc["基准情景", "modeled_total_cost_cny"])
        sensitivity = self.tables["energy_cost_sensitivity"]
        self.assertEqual(len(sensitivity), 18)
        self.assertEqual(set(["parameter", "scenario", "parameter_value", "total_cost_cny", "change_vs_base_pct", "sensitivity_key"]) - set(sensitivity.columns), set())
        self.assertTrue(sensitivity["sensitivity_key"].is_unique)
        self.assertLess(sensitivity["change_vs_base_pct"].abs().max(), 1)
        self.assertTrue({"scenario_id", "label", "total_modeled_cost_cny", "delta_vs_baseline_cny"}.issubset(scenarios.columns))
        self.assertTrue(scenarios["interpretation"].str.contains("不是该韩国钢厂真实账单").all())


if __name__ == "__main__":
    unittest.main()
