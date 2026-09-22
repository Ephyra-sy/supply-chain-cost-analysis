"""Load the headerless, tab-delimited AdventureWorks sample extracts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SCHEMAS = {
    "Product.csv": [
        "product_id", "product_name", "product_number", "make_flag", "finished_goods_flag",
        "color", "safety_stock_level", "reorder_point", "standard_cost", "list_price", "size",
        "size_unit", "weight_unit", "weight", "days_to_manufacture", "product_line", "class",
        "style", "product_subcategory_id", "product_model_id", "sell_start_date", "sell_end_date",
        "discontinued_date", "rowguid", "modified_date",
    ],
    "ProductInventory.csv": [
        "product_id", "location_id", "shelf", "bin", "quantity", "rowguid", "modified_date",
    ],
    "WorkOrder.csv": [
        "work_order_id", "product_id", "order_quantity", "stocked_quantity", "scrap_quantity",
        "start_date", "end_date", "due_date", "scrap_reason_id", "modified_date",
    ],
    "WorkOrderRouting.csv": [
        "work_order_id", "product_id", "operation_sequence", "location_id", "scheduled_start_date",
        "scheduled_end_date", "actual_start_date", "actual_end_date", "actual_hours", "planned_cost",
        "actual_cost", "modified_date",
    ],
    "PurchaseOrderDetail.csv": [
        "purchase_order_detail_id", "purchase_order_id", "due_date", "order_quantity", "product_id",
        "unit_price", "line_total", "received_quantity", "rejected_quantity", "stocked_quantity",
        "modified_date",
    ],
}


def _read(path: Path, names: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, sep="\t", header=None, names=names, na_values=["", "NULL"])
    if len(frame.columns) != len(names):
        raise ValueError(f"Unexpected schema width for {path.name}")
    return frame


def load_core_tables(raw_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load normalized core inputs needed by the scenario and KPI model."""
    raw_dir = Path(raw_dir)
    missing = [name for name in SCHEMAS if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing AdventureWorks extracts: {', '.join(missing)}")
    tables = {name.removesuffix(".csv"): _read(raw_dir / name, columns) for name, columns in SCHEMAS.items()}
    products = tables["Product"]
    for col in ["standard_cost", "list_price"]:
        products[col] = pd.to_numeric(products[col], errors="coerce")
    for table, columns in {
        "ProductInventory": ["quantity"],
        "WorkOrder": ["order_quantity", "stocked_quantity", "scrap_quantity"],
        "WorkOrderRouting": ["actual_hours", "planned_cost", "actual_cost"],
        "PurchaseOrderDetail": ["order_quantity", "unit_price", "line_total", "received_quantity", "rejected_quantity"],
    }.items():
        for col in columns:
            tables[table][col] = pd.to_numeric(tables[table][col], errors="coerce")
    for frame in tables.values():
        frame["source_class"] = "observed_sample"
        frame["source_note"] = "Microsoft AdventureWorks public fictional sample"
    return {
        "products": tables["Product"],
        "inventory": tables["ProductInventory"],
        "work_orders": tables["WorkOrder"],
        "routing": tables["WorkOrderRouting"],
        "purchases": tables["PurchaseOrderDetail"],
    }
