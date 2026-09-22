"""Clean and aggregate the public USAID shipment and UCI steel-energy data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
USAID_FILE = ROOT / "data" / "raw" / "usaid_supply_chain" / "usaid_supply_chain_shipments.csv"
STEEL_FILE = ROOT / "data" / "raw" / "steel_energy" / "Steel_industry_data.csv"
PROCESSED = ROOT / "data" / "processed"


def load_shipments() -> pd.DataFrame:
    """Return validated line-item shipment records with analytical fields."""
    frame = pd.read_csv(USAID_FILE)
    frame.columns = [column.strip().lower() for column in frame.columns]
    for column in ["scheduled delivery date", "delivered to client date", "delivery recorded date"]:
        frame[column] = pd.to_datetime(frame[column], format="%d-%b-%y", errors="coerce")
    frame["freight_cost_usd_numeric"] = pd.to_numeric(frame["freight cost (usd)"], errors="coerce")
    frame["weight_kg_numeric"] = pd.to_numeric(frame["weight (kilograms)"], errors="coerce")
    frame["delay_days"] = (frame["delivered to client date"] - frame["scheduled delivery date"]).dt.days
    frame["on_time"] = frame["delay_days"].le(0)
    frame["delivery_year"] = frame["delivered to client date"].dt.year.astype("Int64")
    return frame


def load_energy() -> pd.DataFrame:
    """Return validated 15-minute steel-factory energy observations."""
    frame = pd.read_csv(STEEL_FILE)
    frame["timestamp"] = pd.to_datetime(frame["date"], format="%d/%m/%Y %H:%M", errors="coerce")
    frame["month"] = frame["timestamp"].dt.to_period("M").astype(str)
    frame["hour"] = frame["timestamp"].dt.hour
    frame["day"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    return frame


def build_analysis_tables() -> dict[str, pd.DataFrame]:
    shipments = load_shipments()
    energy = load_energy()

    numeric_freight = shipments["freight_cost_usd_numeric"].notna()
    total_value = shipments["line item value"].sum()
    known_freight = shipments["freight_cost_usd_numeric"].sum()
    freight_subset_value = shipments.loc[numeric_freight, "line item value"].sum()
    peak_month = energy.groupby("month", as_index=False)["Usage_kWh"].sum().sort_values("Usage_kWh", ascending=False).iloc[0]
    max_load_usage = energy.loc[energy["Load_Type"].eq("Maximum_Load"), "Usage_kWh"].sum()

    summary = pd.DataFrame([{
        "shipment_lines": int(len(shipments)),
        "destination_countries": int(shipments["country"].nunique()),
        "line_item_value_usd": float(total_value),
        "on_time_rate": float(shipments["on_time"].mean()),
        "late_shipment_rate": float(shipments["delay_days"].gt(0).mean()),
        "known_freight_usd": float(known_freight),
        "freight_numeric_coverage": float(numeric_freight.mean()),
        "known_freight_to_value_ratio": float(known_freight / freight_subset_value),
        "energy_observations": int(len(energy)),
        "energy_usage_kwh": float(energy["Usage_kWh"].sum()),
        "co2_tonnes": float(energy["CO2(tCO2)"].sum()),
        "average_lagging_power_factor": float(energy["Lagging_Current_Power_Factor"].mean()),
        "maximum_load_energy_share": float(max_load_usage / energy["Usage_kWh"].sum()),
        "peak_energy_month": str(peak_month["month"]),
        "peak_energy_month_kwh": float(peak_month["Usage_kWh"]),
    }])

    shipment_year = shipments.groupby("delivery_year", as_index=False).agg(
        shipment_lines=("id", "size"), line_item_value_usd=("line item value", "sum"),
        on_time_rate=("on_time", "mean"), average_delay_days=("delay_days", "mean"),
        known_freight_usd=("freight_cost_usd_numeric", "sum"), freight_rows=("freight_cost_usd_numeric", "count"),
    )
    shipment_year["freight_numeric_coverage"] = shipment_year["freight_rows"] / shipment_year["shipment_lines"]
    shipment_year["delivery_year"] = shipment_year["delivery_year"].astype(int).astype(str)

    shipment_mode = shipments.groupby("shipment mode", dropna=False, as_index=False).agg(
        shipment_lines=("id", "size"), line_item_value_usd=("line item value", "sum"),
        on_time_rate=("on_time", "mean"), average_delay_days=("delay_days", "mean"),
        known_freight_usd=("freight_cost_usd_numeric", "sum"), freight_rows=("freight_cost_usd_numeric", "count"),
    )
    shipment_mode["shipment mode"] = shipment_mode["shipment mode"].fillna("未记录")
    shipment_mode["freight_numeric_coverage"] = shipment_mode["freight_rows"] / shipment_mode["shipment_lines"]
    shipment_mode = shipment_mode.sort_values("line_item_value_usd", ascending=False)

    country = shipments.groupby("country", as_index=False).agg(
        shipment_lines=("id", "size"), line_item_value_usd=("line item value", "sum"),
        on_time_rate=("on_time", "mean"), average_delay_days=("delay_days", "mean"),
    ).sort_values("line_item_value_usd", ascending=False).head(12)

    sites = shipments.groupby("manufacturing site", as_index=False).agg(
        shipment_lines=("id", "size"), line_item_value_usd=("line item value", "sum"), on_time_rate=("on_time", "mean"),
    ).sort_values("line_item_value_usd", ascending=False).head(12)

    energy_month = energy.groupby("month", as_index=False).agg(
        usage_kwh=("Usage_kWh", "sum"), average_interval_kwh=("Usage_kWh", "mean"),
        co2_tonnes=("CO2(tCO2)", "sum"), lagging_power_factor=("Lagging_Current_Power_Factor", "mean"),
    )
    energy_hour = energy.groupby("hour", as_index=False).agg(
        average_interval_kwh=("Usage_kWh", "mean"), total_usage_kwh=("Usage_kWh", "sum"), observations=("Usage_kWh", "size"),
    )
    energy_hour["hour_label"] = energy_hour["hour"].map(lambda value: f"{int(value):02d}:00")
    energy_load = energy.groupby("Load_Type", as_index=False).agg(
        usage_kwh=("Usage_kWh", "sum"), average_interval_kwh=("Usage_kWh", "mean"),
        observations=("Usage_kWh", "size"), co2_tonnes=("CO2(tCO2)", "sum"),
    )
    energy_load["energy_share"] = energy_load["usage_kwh"] / energy_load["usage_kwh"].sum()
    energy_week = energy.groupby("WeekStatus", as_index=False).agg(
        usage_kwh=("Usage_kWh", "sum"), average_interval_kwh=("Usage_kWh", "mean"), observations=("Usage_kWh", "size"),
    )
    energy_days = energy.groupby("day", as_index=False).agg(
        usage_kwh=("Usage_kWh", "sum"), co2_tonnes=("CO2(tCO2)", "sum")
    ).sort_values("usage_kwh", ascending=False).head(10)

    quality = pd.DataFrame([
        {"dataset": "USAID 发运明细", "check": "行数", "result": str(len(shipments)), "status": "pass"},
        {"dataset": "USAID 发运明细", "check": "完全重复行", "result": str(int(shipments.duplicated().sum())), "status": "pass"},
        {"dataset": "USAID 发运明细", "check": "交付日期可解析率", "result": f"{shipments['delivered to client date'].notna().mean():.1%}", "status": "pass"},
        {"dataset": "USAID 发运明细", "check": "运费可数值化率", "result": f"{numeric_freight.mean():.1%}", "status": "caution"},
        {"dataset": "USAID 发运明细", "check": "重量可数值化率", "result": f"{shipments['weight_kg_numeric'].notna().mean():.1%}", "status": "caution"},
        {"dataset": "UCI 钢厂能耗", "check": "行数", "result": str(len(energy)), "status": "pass"},
        {"dataset": "UCI 钢厂能耗", "check": "时间戳重复", "result": str(int(energy.duplicated(subset=["date"]).sum())), "status": "pass"},
        {"dataset": "UCI 钢厂能耗", "check": "时间戳可解析率", "result": f"{energy['timestamp'].notna().mean():.1%}", "status": "pass"},
    ])

    return {
        "executive_summary": summary, "shipment_by_year": shipment_year, "shipment_by_mode": shipment_mode,
        "country_performance": country, "manufacturing_sites": sites, "energy_monthly": energy_month,
        "energy_hourly": energy_hour, "energy_by_load_type": energy_load, "energy_by_week_status": energy_week,
        "energy_peak_days": energy_days, "data_quality": quality,
    }


def write_processed_tables(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.replace([np.inf, -np.inf], np.nan).to_csv(PROCESSED / f"{name}.csv", index=False)
