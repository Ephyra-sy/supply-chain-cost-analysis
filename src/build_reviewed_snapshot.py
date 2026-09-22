"""Build the reviewed JSON snapshot consumed by the report and dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.real_data_pipeline import build_analysis_tables, write_processed_tables


ROOT = Path(__file__).resolve().parents[1]


def _records(frame: pd.DataFrame) -> list[dict]:
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def _source(label: str, tables: list[str], definitions: list[dict], assumptions: list[str]) -> dict:
    return {
        "label": label,
        "tables": tables,
        "filters": ["USAID: 2006–2015 delivery history; UCI: 2018 full-year 15-minute observations"],
        "assumptions": assumptions,
        "metricDefinitions": definitions,
        "classification": "observed_public_real_data",
    }


USAID_LIMITS = [
    "USAID records are real public administrative shipment data, not data from the portfolio author's employer.",
    "The original USAID portal is currently unavailable; the local CSV was retrieved from a public mirror and is identified by original portal dataset ID a3rc-nmf6.",
    "Freight Cost contains text states such as 'included in commodity cost' and 'invoiced separately'; only directly numeric rows are summed.",
    "USAID cautions against using the data to infer precise item/country transport cost or lead-time causality; this project reports descriptive patterns only.",
]
ENERGY_LIMITS = [
    "UCI observations come from a steel facility in South Korea and represent real 2018 electricity-use measurements.",
    "No verified electricity tariff is supplied, so this project reports kWh and CO2 rather than inventing a monetary energy cost.",
]


def build_snapshot(build_status: str = "complete") -> Path:
    tables = build_analysis_tables()
    write_processed_tables(tables)
    queries = {
        "executive_summary": {
            "rows": _records(tables["executive_summary"]),
            "source": _source("USAID shipment history + UCI steel energy summary", [
                "data/raw/usaid_supply_chain/usaid_supply_chain_shipments.csv",
                "data/raw/steel_energy/Steel_industry_data.csv",
            ], [
                {"label": "准时交付率", "definition": "实际交付日期早于或等于计划交付日期的明细行数 ÷ 全部明细行数。", "componentIds": ["kpi-ontime", "report-summary"]},
                {"label": "已知运费", "definition": "Freight Cost (USD) 中可直接转换为数值的金额合计；文本状态不视为0。", "componentIds": ["kpi-freight", "freight-coverage"]},
                {"label": "总用电量", "definition": "UCI 2018年35,040个15分钟观测值的 Usage_kWh 合计。", "componentIds": ["kpi-energy", "energy-monthly"]},
            ], USAID_LIMITS + ENERGY_LIMITS),
        },
        "shipment_by_year": {"rows": _records(tables["shipment_by_year"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [], USAID_LIMITS)},
        "shipment_by_mode": {"rows": _records(tables["shipment_by_mode"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [], USAID_LIMITS)},
        "country_performance": {"rows": _records(tables["country_performance"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [], USAID_LIMITS)},
        "manufacturing_sites": {"rows": _records(tables["manufacturing_sites"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [], USAID_LIMITS)},
        "energy_monthly": {"rows": _records(tables["energy_monthly"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_hourly": {"rows": _records(tables["energy_hourly"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_by_load_type": {"rows": _records(tables["energy_by_load_type"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_by_week_status": {"rows": _records(tables["energy_by_week_status"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_peak_days": {"rows": _records(tables["energy_peak_days"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "data_quality": {"rows": _records(tables["data_quality"]), "source": _source("本地数据质量检查", ["src/real_data_pipeline.py"], [], USAID_LIMITS + ENERGY_LIMITS)},
    }
    snapshot = {
        "surface": "dashboard",
        "title": "真实供应链与制造能耗分析",
        "generatedAt": pd.Timestamp.now(tz="UTC").isoformat(),
        "buildStatus": build_status,
        "status": "reviewed_public_observed_data",
        "filters": [],
        "queries": queries,
    }
    output = ROOT / "data" / "reviewed_snapshot.json"
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    print(build_snapshot())
