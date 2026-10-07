"""Build the reviewed JSON snapshot consumed by the report and dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.real_data_pipeline import build_analysis_tables, write_processed_tables


ROOT = Path(__file__).resolve().parents[1]


def _records(frame: pd.DataFrame) -> list[dict]:
    records = frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")
    for row in records:
        for key, value in row.items():
            if isinstance(value, pd.Timestamp):
                row[key] = value.isoformat()
    return records


def _source(label: str, tables: list[str], definitions: list[dict], assumptions: list[str], classification: str = "observed_public_real_data") -> dict:
    return {
        "label": label,
        "tables": tables,
        "filters": ["USAID: 2006–2015 delivery history; UCI: 2018 full-year 15-minute observations"],
        "assumptions": assumptions,
        "metricDefinitions": definitions,
        "classification": classification,
    }


USAID_LIMITS = [
    "USAID records are real public administrative shipment data, not data from the portfolio author's employer.",
    "The original USAID portal is currently unavailable; the local CSV was retrieved from a public mirror and is identified by original portal dataset ID a3rc-nmf6.",
    "Freight Cost contains text states such as 'included in commodity cost' and 'invoiced separately'; only directly numeric rows are summed.",
    "USAID cautions against using the data to infer precise item/country transport cost or lead-time causality; this project reports descriptive patterns only.",
]
ENERGY_LIMITS = [
    "UCI observations come from a steel facility in South Korea and represent real 2018 electricity-use measurements.",
    "The source contains 35,040 sequential 15-minute observations; observed demand is approximated as interval kWh ÷ 0.25 hours, not a utility-meter billing maximum.",
    "Energy cost outputs are parameterized RMB scenarios using editable peak/shoulder/off-peak tariffs and demand charges; the plant's actual tariff, currency denomination, production volume and meter billing rules are unavailable.",
    "Load shifting and peak shaving are assumptions for sensitivity analysis, not validated operating changes or realized savings.",
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
        "logistics_lane_performance": {"rows": _records(tables["shipment_cost_delivery_matrix"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [
            {"label": "三维发运成本与交付分析", "definition": "按运输方式、目的国、制造地点汇总发运行数、货值、延期、数值运费和运费数值覆盖率；仅数值运费计入已知运费合计。", "componentIds": ["shipment-cost-delivery-matrix"]}
        ], USAID_LIMITS)},
        "shipment_risk_queue": {"rows": _records(tables["shipment_review_queue"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [
            {"label": "逐条复核队列", "definition": "通过原始ID回指发运记录；按货值P95、延期≥30天、可数值运费P95和运费缺失/文本状态触发。阈值用于复核筛查，不构成异常定性。", "componentIds": ["shipment-review-queue"]}
        ], USAID_LIMITS)},
        "freight_status_summary": {"rows": _records(tables["freight_status_summary"]), "source": _source("USAID Supply Chain Shipment Pricing Data", ["usaid_supply_chain_shipments.csv"], [
            {"label": "运费状态分类", "definition": "按 numeric_amount、blank、included_in_commodity_cost、invoiced_separately、reference_to_other_document 和 other_text_status 分组；仅数值金额参与运费求和。", "componentIds": ["freight-status-summary"]}
        ], USAID_LIMITS)},
        "energy_monthly": {"rows": _records(tables["energy_monthly"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_hourly": {"rows": _records(tables["energy_hourly"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_by_load_type": {"rows": _records(tables["energy_by_load_type"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_by_week_status": {"rows": _records(tables["energy_by_week_status"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_peak_days": {"rows": _records(tables["energy_peak_days"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [], ENERGY_LIMITS)},
        "energy_period_profile": {"rows": _records(tables["energy_period_profile"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [
            {"label": "分时能耗结构", "definition": "按工作日/周末、假设峰平谷时段和原始负荷类型分组，汇总15分钟用电量、区间最大kWh和按 kWh÷0.25 估算的kW。", "componentIds": ["energy-period-profile"]}
        ], ENERGY_LIMITS)},
        "energy_monthly_demand": {"rows": _records(tables["energy_monthly_demand"]), "source": _source("UCI Steel Industry Energy Consumption", ["Steel_industry_data.csv"], [
            {"label": "月度峰平谷用电及需量近似", "definition": "峰平谷电量依照参数化小时段划分；observed_peak_kw 为月内最大15分钟 Usage_kWh÷0.25 小时。", "componentIds": ["energy-monthly-demand"]}
        ], ENERGY_LIMITS)},
        "energy_scenario_summary": {"rows": _records(tables["energy_cost_scenarios"]), "source": _source("UCI 实测用电 + 用户可编辑电价假设", ["Steel_industry_data.csv", "src/real_data_pipeline.py"], [], ENERGY_LIMITS, "scenario_estimate_from_public_observations")},
        "energy_sensitivity": {"rows": _records(tables["energy_cost_sensitivity"]), "source": _source("UCI 实测用电 + 参数化敏感性情景", ["Steel_industry_data.csv", "src/real_data_pipeline.py"], [], ENERGY_LIMITS, "scenario_estimate_from_public_observations")},
        "energy_scenario_assumptions": {"rows": _records(tables["energy_scenario_parameters"]), "source": _source("项目情景参数与数据粒度说明", ["src/real_data_pipeline.py"], [], ENERGY_LIMITS)},
        "data_quality": {"rows": _records(tables["data_quality"]), "source": _source("本地数据质量检查", ["src/real_data_pipeline.py"], [], USAID_LIMITS + ENERGY_LIMITS)},
    }
    snapshot = {
        "surface": "dashboard",
        "title": "制造供应链成本管控与经营分析",
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
