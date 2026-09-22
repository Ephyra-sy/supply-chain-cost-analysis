import unittest

from src.real_data_pipeline import build_analysis_tables, load_energy, load_shipments


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


if __name__ == "__main__":
    unittest.main()
