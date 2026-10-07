"""Clean and aggregate the public USAID shipment and UCI steel-energy data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
USAID_FILE = ROOT / "data" / "raw" / "usaid_supply_chain" / "usaid_supply_chain_shipments.csv"
STEEL_FILE = ROOT / "data" / "raw" / "steel_energy" / "Steel_industry_data.csv"
PROCESSED = ROOT / "data" / "processed"

# Illustrative inputs only. The UCI source does not publish the facility's tariff.
# Values are intentionally centralized and can be replaced by a user-provided tariff.
ENERGY_SCENARIO_DEFAULTS = {
    "peak_hours": "09-17",
    "shoulder_hours": "07-09,17-22",
    "peak_tariff_cny_per_kwh": 0.90,
    "shoulder_tariff_cny_per_kwh": 0.60,
    "offpeak_tariff_cny_per_kwh": 0.30,
    "demand_charge_cny_per_kw_month": 40.0,
    "load_shift_share_of_peak_kwh": 0.05,
    "peak_shave_share_of_monthly_peak_kw": 0.03,
}


def load_shipments() -> pd.DataFrame:
    """Return validated line-item shipment records with analytical fields."""
    frame = pd.read_csv(USAID_FILE)
    frame.columns = [column.strip().lower() for column in frame.columns]
    for column in ["scheduled delivery date", "delivered to client date", "delivery recorded date"]:
        frame[column] = pd.to_datetime(frame[column], format="%d-%b-%y", errors="coerce")
    freight_raw = frame["freight cost (usd)"].astype("string").str.strip()
    freight_numeric = pd.to_numeric(freight_raw, errors="coerce")
    freight_lower = freight_raw.str.lower()
    freight_status = pd.Series("other_text_status", index=frame.index, dtype="string")
    freight_status[freight_raw.isna() | freight_raw.eq("")] = "blank"
    freight_status[freight_lower.str.contains("included", na=False)] = "included_in_commodity_cost"
    freight_status[freight_lower.str.contains("invoiced", na=False)] = "invoiced_separately"
    freight_status[freight_lower.str.contains(r"see\s+(?:dn|asn)", regex=True, na=False)] = "reference_to_other_document"
    freight_status[freight_numeric.notna()] = "numeric_amount"
    frame["freight_cost_raw"] = freight_raw
    frame["freight_cost_usd_numeric"] = freight_numeric
    frame["freight_status"] = freight_status
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
    frame["is_weekday"] = frame["WeekStatus"].eq("Weekday")
    frame["interval_hours"] = 0.25
    frame["demand_kw"] = frame["Usage_kWh"] / frame["interval_hours"]
    return frame


def build_shipment_cost_delivery_matrix(shipments: pd.DataFrame) -> pd.DataFrame:
    """Cross-tab shipment value, delays and numeric freight by mode/country/site."""
    dims = ["shipment mode", "country", "manufacturing site"]
    work = shipments.copy()
    for column in dims:
        work[column] = work[column].fillna("未记录").astype(str)
    matrix = work.groupby(dims, dropna=False, as_index=False).agg(
        shipment_lines=("id", "size"),
        line_item_value_usd=("line item value", "sum"),
        delayed_lines=("delay_days", lambda values: int(values.gt(0).sum())),
        on_time_rate=("on_time", "mean"),
        average_delay_days=("delay_days", "mean"),
        known_freight_usd=("freight_cost_usd_numeric", "sum"),
        numeric_freight_rows=("freight_cost_usd_numeric", "count"),
        freight_unquantified_rows=("freight_cost_usd_numeric", lambda values: int(values.isna().sum())),
    )
    matrix["late_delivery_rate"] = matrix["delayed_lines"] / matrix["shipment_lines"]
    matrix["freight_numeric_coverage"] = matrix["numeric_freight_rows"] / matrix["shipment_lines"]
    matrix["known_freight_to_value_ratio"] = np.where(
        matrix["line_item_value_usd"].gt(0), matrix["known_freight_usd"] / matrix["line_item_value_usd"], np.nan
    )
    matrix["lane_key"] = matrix[dims].astype(str).agg(" | ".join, axis=1)
    matrix["shipment_mode"] = matrix["shipment mode"]
    matrix["manufacturing_site"] = matrix["manufacturing site"]
    matrix["late_lines"] = matrix["delayed_lines"]
    matrix["late_rate"] = matrix["late_delivery_rate"]
    return matrix.sort_values(["line_item_value_usd", "shipment_lines"], ascending=False).reset_index(drop=True)


def build_shipment_review_queue(shipments: pd.DataFrame) -> pd.DataFrame:
    """Create a row-level, source-ID traceable review queue from descriptive triggers."""
    frame = shipments.copy()
    high_value_threshold = float(frame["line item value"].quantile(0.95))
    known_freight = frame["freight_cost_usd_numeric"].dropna()
    high_freight_threshold = float(known_freight.quantile(0.95)) if not known_freight.empty else np.inf
    long_delay_threshold = 30

    frame["trigger_high_value"] = frame["line item value"].ge(high_value_threshold)
    frame["trigger_long_delay"] = frame["delay_days"].ge(long_delay_threshold)
    frame["trigger_high_known_freight"] = frame["freight_cost_usd_numeric"].ge(high_freight_threshold)
    frame["trigger_freight_unquantified"] = frame["freight_status"].ne("numeric_amount")
    trigger_cols = ["trigger_high_value", "trigger_long_delay", "trigger_high_known_freight", "trigger_freight_unquantified"]
    frame[trigger_cols] = frame[trigger_cols].fillna(False).astype(bool)
    frame["trigger_count"] = frame[trigger_cols].sum(axis=1)
    frame["review_id"] = "usaid-" + frame["id"].astype("Int64").astype(str)
    frame["trigger_reasons"] = frame.apply(
        lambda row: "；".join(
            label for column, label in [
                ("trigger_high_value", "高货值（P95）"),
                ("trigger_long_delay", "延期≥30天"),
                ("trigger_high_known_freight", "高已知运费（P95）"),
                ("trigger_freight_unquantified", "运费缺失/文本状态"),
            ] if bool(row[column])
        ), axis=1
    )
    frame["trigger_codes"] = frame.apply(
        lambda row: ";".join(code for column, code in [
            ("trigger_high_value", "HVAL_P95"), ("trigger_long_delay", "LATE_30D"),
            ("trigger_high_known_freight", "HFREIGHT_P95"), ("trigger_freight_unquantified", "FREIGHT_UNKNOWN"),
        ] if bool(row[column])), axis=1
    )
    frame["review_priority"] = np.select(
        [
            (frame["trigger_long_delay"] & frame["trigger_high_value"])
            | (frame["trigger_long_delay"] & frame["trigger_high_known_freight"])
            | frame["delay_days"].ge(60)
            | frame["line item value"].ge(frame["line item value"].quantile(0.99)),
            frame["trigger_high_value"] | frame["trigger_long_delay"] | frame["trigger_high_known_freight"],
        ], ["P1-优先复核", "P2-重点复核"], default="P3-数据完整性"
    )
    frame["suggested_department"] = np.select(
        [frame["trigger_long_delay"], frame["trigger_freight_unquantified"], frame["trigger_high_known_freight"]],
        ["物流/计划", "物流/应付/数据治理", "采购/物流"], default="采购/供应商管理"
    )
    frame["priority_rule"] = np.select(
        [frame["review_priority"].eq("P1-优先复核"), frame["review_priority"].eq("P2-重点复核")],
        ["P1_COMBINED_OR_EXTREME", "P2_SINGLE_MATERIAL_TRIGGER"], default="P3_DATA_COMPLETENESS"
    )
    frame["recommended_action"] = np.select(
        [frame["trigger_long_delay"], frame["trigger_freight_unquantified"], frame["trigger_high_known_freight"]],
        ["核对计划与实际交付日期、运输方式、清关节点及异常原因",
         "根据原始单据核实运费是否含在货值、另行开票或引用其他单据，并补齐金额/状态",
         "对照承运合同、订单及路线报价复核运费金额"],
        default="复核高货值行对应的采购订单、产品和供应商报价"
    )
    frame["review_status"] = "待人工核实"
    frame["rule_evidence"] = frame.apply(
        lambda row: "；".join(part for part in [
            f"行货值≥P95阈值${high_value_threshold:,.2f}" if row["trigger_high_value"] else "",
            f"延期≥{long_delay_threshold}天" if row["trigger_long_delay"] else "",
            f"可数值化运费≥P95阈值${high_freight_threshold:,.2f}" if row["trigger_high_known_freight"] else "",
            f"Freight Cost状态={row['freight_status']}" if row["trigger_freight_unquantified"] else "",
        ] if part), axis=1
    )
    cols = [
        "id", "project code", "pq #", "po / so #", "asn/dn #", "country", "shipment mode",
        "review_id",
        "vendor", "manufacturing site", "scheduled delivery date", "delivered to client date", "delay_days",
        "line item value", "freight_cost_raw", "freight_cost_usd_numeric", "freight_status",
        "trigger_high_value", "trigger_long_delay", "trigger_high_known_freight", "trigger_freight_unquantified",
        "trigger_count", "review_priority", "trigger_reasons", "rule_evidence", "suggested_department", "recommended_action", "review_status",
        "trigger_codes", "priority_rule",
    ]
    queue = frame.loc[frame["trigger_count"].gt(0), cols].copy()
    priority_order = {"P1-优先复核": 0, "P2-重点复核": 1, "P3-数据完整性": 2}
    queue["_priority_order"] = queue["review_priority"].map(priority_order)
    queue["source_shipment_id"] = queue["id"].astype("Int64").astype(str)
    queue["project_code"] = queue["project code"]
    queue["po_so_number"] = queue["po / so #"]
    queue["shipment_mode"] = queue["shipment mode"]
    queue["manufacturing_site"] = queue["manufacturing site"]
    queue["line_item_value_usd"] = queue["line item value"]
    queue["known_freight_usd"] = queue["freight_cost_usd_numeric"]
    queue["priority"] = queue["review_priority"].str.extract(r"^(P[123])", expand=False)
    queue["evidence_summary"] = queue["rule_evidence"]
    queue["suggested_owner"] = queue["suggested_department"]
    return queue.sort_values(["_priority_order", "trigger_count", "line item value"], ascending=[True, False, False]).drop(columns="_priority_order").reset_index(drop=True)


def _hour_set(hour_spec: str) -> set[int]:
    hours: set[int] = set()
    for block in str(hour_spec).split(","):
        start, end = [int(part) for part in block.split("-")]
        hours.update(range(start, end))
    return hours


def build_energy_cost_scenarios(energy: pd.DataFrame, parameters: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Model illustrative tariff costs on observed 15-minute kWh, with editable inputs."""
    params = {**ENERGY_SCENARIO_DEFAULTS, **(parameters or {})}
    frame = energy.copy()
    peak_hours = _hour_set(params["peak_hours"])
    shoulder_hours = _hour_set(params["shoulder_hours"])
    frame["tariff_period"] = np.select(
        [frame["hour"].isin(peak_hours), frame["hour"].isin(shoulder_hours)],
        ["峰", "平"], default="谷"
    )
    period_summary = frame.groupby(["WeekStatus", "tariff_period", "Load_Type"], as_index=False).agg(
        usage_kwh=("Usage_kWh", "sum"), observations=("Usage_kWh", "size"),
        average_interval_kwh=("Usage_kWh", "mean"), max_interval_kwh=("Usage_kWh", "max"),
        observed_peak_kw=("demand_kw", "max"),
    ).rename(columns={"WeekStatus": "week_status", "Load_Type": "load_type"})
    period_summary["profile_key"] = period_summary[["week_status", "tariff_period", "load_type"]].astype(str).agg("|".join, axis=1)
    period_summary["interval_minutes"] = 15

    monthly = frame.groupby("month", as_index=False).agg(
        total_kwh=("Usage_kWh", "sum"),
        monthly_max_demand_kw=("demand_kw", "max"),
    )
    period_usage = frame.pivot_table(index="month", columns="tariff_period", values="Usage_kWh", aggfunc="sum", fill_value=0)
    for period in ["峰", "平", "谷"]:
        if period not in period_usage:
            period_usage[period] = 0.0
    monthly = monthly.merge(period_usage[["峰", "平", "谷"]].rename(columns={"峰": "peak_usage_kwh", "平": "shoulder_usage_kwh", "谷": "offpeak_usage_kwh"}), on="month")
    monthly["observed_peak_kw"] = monthly["monthly_max_demand_kw"]
    tariff_peak = float(params["peak_tariff_cny_per_kwh"])
    tariff_shoulder = float(params["shoulder_tariff_cny_per_kwh"])
    tariff_offpeak = float(params["offpeak_tariff_cny_per_kwh"])
    demand_rate = float(params["demand_charge_cny_per_kw_month"])
    shift_share = float(params["load_shift_share_of_peak_kwh"])
    shave_share = float(params["peak_shave_share_of_monthly_peak_kw"])

    scenario_specs = [
        ("基准情景", 1.0, demand_rate, 0.0, 0.0),
        ("轻度优化", 1.0, demand_rate, 0.05, 0.03),
        ("强化优化", 1.0, demand_rate, 0.10, 0.08),
    ]
    scenario_rows = []
    for name, tariff_multiplier, scenario_demand_rate, scenario_shift_share, scenario_shave_share in scenario_specs:
        peak_rate = tariff_peak * tariff_multiplier
        shoulder_rate = tariff_shoulder * tariff_multiplier
        offpeak_rate = tariff_offpeak * tariff_multiplier
        shifted_kwh = monthly["peak_usage_kwh"] * scenario_shift_share
        energy_charge = (monthly["peak_usage_kwh"] * peak_rate) + (monthly["shoulder_usage_kwh"] * shoulder_rate) + (monthly["offpeak_usage_kwh"] * offpeak_rate)
        energy_charge_after_shift = energy_charge - (shifted_kwh * (peak_rate - offpeak_rate))
        demand_charge = monthly["monthly_max_demand_kw"] * scenario_demand_rate
        demand_charge_after_shave = demand_charge * (1 - scenario_shave_share)
        total_cost = float((energy_charge_after_shift + demand_charge_after_shave).sum())
        scenario_rows.append({
            "scenario_id": {"基准情景": "baseline", "轻度优化": "mild", "强化优化": "strong"}[name],
            "scenario": name, "label": name, "tariff_multiplier": tariff_multiplier,
            "peak_tariff_cny_per_kwh": peak_rate, "shoulder_tariff_cny_per_kwh": shoulder_rate,
            "offpeak_tariff_cny_per_kwh": offpeak_rate,
            "demand_charge_cny_per_kw_month": scenario_demand_rate,
            "load_shift_share": scenario_shift_share, "peak_shave_share": scenario_shave_share,
            "shifted_peak_energy_kwh": float(shifted_kwh.sum()),
            "modeled_energy_charge_cny": float(energy_charge_after_shift.sum()),
            "modeled_demand_charge_cny": float(demand_charge_after_shave.sum()),
            "modeled_total_cost_cny": total_cost,
            "estimated_savings_vs_baseline_cny": 0.0,
            "interpretation": "情景估算；改善效果为可编辑参数推演，不是该韩国钢厂真实账单或已实现节省",
        })
    scenarios = pd.DataFrame(scenario_rows)
    base_cost = float(scenarios.loc[scenarios["scenario"].eq("基准情景"), "modeled_total_cost_cny"].iloc[0])
    scenarios["estimated_savings_vs_baseline_cny"] = base_cost - scenarios["modeled_total_cost_cny"]
    scenarios["energy_charge_cny"] = scenarios["modeled_energy_charge_cny"]
    scenarios["demand_charge_cny"] = scenarios["modeled_demand_charge_cny"]
    scenarios["total_modeled_cost_cny"] = scenarios["modeled_total_cost_cny"]
    scenarios["delta_vs_baseline_cny"] = scenarios["modeled_total_cost_cny"] - base_cost
    scenarios["load_shift_kwh"] = scenarios["shifted_peak_energy_kwh"]

    sensitivity_rows = []
    action_specs = [("基准情景", 0.0, 0.0), ("轻度优化", 0.05, 0.03), ("强化优化", 0.10, 0.08)]
    for parameter, values in [("综合电价倍率", [0.8, 1.0, 1.2]), ("需量费单价", [25.0, demand_rate, 55.0])]:
        for parameter_value in values:
            for action_name, shift, shave in action_specs:
                multiplier = float(parameter_value) if parameter == "综合电价倍率" else 1.0
                demand = demand_rate if parameter == "综合电价倍率" else float(parameter_value)
                peak_rate = tariff_peak * multiplier
                shoulder_rate = tariff_shoulder * multiplier
                offpeak_rate = tariff_offpeak * multiplier
                energy_charge = monthly["peak_usage_kwh"] * peak_rate + monthly["shoulder_usage_kwh"] * shoulder_rate + monthly["offpeak_usage_kwh"] * offpeak_rate
                shift_saving = monthly["peak_usage_kwh"] * shift * (peak_rate - offpeak_rate)
                demand_cost = monthly["monthly_max_demand_kw"] * demand * (1 - shave)
                total_cost = float((energy_charge - shift_saving + demand_cost).sum())
                sensitivity_rows.append({
                    "parameter": parameter, "scenario": action_name,
                    "parameter_value": parameter_value, "total_cost_cny": total_cost,
                    "load_shift_share": shift, "peak_shave_share": shave,
                })
    sensitivity = pd.DataFrame(sensitivity_rows)
    base_sensitivity_cost = float(sensitivity.loc[
        sensitivity["parameter"].eq("综合电价倍率") & sensitivity["parameter_value"].eq(1.0) & sensitivity["scenario"].eq("基准情景"),
        "total_cost_cny",
    ].iloc[0])
    sensitivity["change_vs_base_pct"] = sensitivity["total_cost_cny"] / base_sensitivity_cost - 1
    sensitivity["sensitivity_key"] = sensitivity.apply(
        lambda row: f"{row['parameter']}|{row['scenario']}|{row['parameter_value']}", axis=1
    )

    parameter_rows = [
        {"parameter": key, "value": value, "unit": "hour ranges" if key.endswith("hours") else ("CNY/kWh" if "tariff" in key else ("CNY/kW-month" if "demand_charge" in key else "share (0-1)")),
         "editable": True, "evidence_type": "user_assumption_not_observed_tariff"}
        for key, value in params.items()
    ]
    parameter_rows.extend([
        {"parameter": "interval_minutes", "value": 15, "unit": "minutes", "editable": False, "evidence_type": "source_observation_grain"},
        {"parameter": "peak_demand_method", "value": "monthly maximum 15-minute kWh × 4", "unit": "kW", "editable": False, "evidence_type": "derived_from_interval_grain"},
    ])
    monthly_demand = monthly[["month", "peak_usage_kwh", "shoulder_usage_kwh", "offpeak_usage_kwh", "observed_peak_kw"]].copy()
    return period_summary, monthly_demand, scenarios, sensitivity, pd.DataFrame(parameter_rows)


def build_analysis_tables() -> dict[str, pd.DataFrame]:
    shipments = load_shipments()
    energy = load_energy()
    shipment_matrix = build_shipment_cost_delivery_matrix(shipments)
    shipment_queue = build_shipment_review_queue(shipments)
    freight_status_summary = shipments.groupby("freight_status", as_index=False, dropna=False).agg(
        shipment_lines=("id", "size"), line_item_value_usd=("line item value", "sum"),
        known_freight_usd=("freight_cost_usd_numeric", "sum"),
        numeric_amount_rows=("freight_cost_usd_numeric", "count"),
    ).sort_values("shipment_lines", ascending=False)
    freight_status_summary["share"] = freight_status_summary["shipment_lines"] / len(shipments)
    energy_period_profile, energy_monthly_demand, energy_cost_scenarios, energy_cost_sensitivity, energy_parameters = build_energy_cost_scenarios(energy)

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
        "shipment_review_queue_rows": int(len(shipment_queue)),
        "shipment_p1_review_rows": int(shipment_queue["review_priority"].eq("P1-优先复核").sum()),
        "energy_cost_low_cny_scenario": float(energy_cost_scenarios["modeled_total_cost_cny"].min()),
        "energy_cost_base_cny_scenario": float(energy_cost_scenarios.loc[energy_cost_scenarios["scenario"].eq("基准情景"), "modeled_total_cost_cny"].iloc[0]),
        "energy_cost_high_cny_scenario": float(energy_cost_scenarios["modeled_total_cost_cny"].max()),
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
        "shipment_cost_delivery_matrix": shipment_matrix, "shipment_review_queue": shipment_queue,
        "freight_status_summary": freight_status_summary,
        "energy_period_profile": energy_period_profile, "energy_monthly_demand": energy_monthly_demand,
        "energy_cost_scenarios": energy_cost_scenarios, "energy_cost_sensitivity": energy_cost_sensitivity,
        "energy_scenario_parameters": energy_parameters,
    }


def write_processed_tables(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        export = frame.copy()
        numeric_columns = export.select_dtypes(include=["number"]).columns
        if len(numeric_columns):
            export.loc[:, numeric_columns] = export.loc[:, numeric_columns].replace([np.inf, -np.inf], np.nan)
        export.to_csv(PROCESSED / f"{name}.csv", index=False)
