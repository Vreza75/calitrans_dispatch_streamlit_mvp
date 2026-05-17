from __future__ import annotations

from pathlib import Path
import pandas as pd


PROFITTOOLS_COLUMNS = [
    "Load #",
    "Customer",
    "Pickup",
    "Delivery",
    "Driver",
    "Truck",
    "Trailer",
]


def export_ready_loads(df: pd.DataFrame, output_path: str = "exports/profittools_ready_loads.csv") -> str:
    ready = df[df.get("Ready for ProfitTools") == True].copy()

    available_columns = [col for col in PROFITTOOLS_COLUMNS if col in ready.columns]
    export_df = ready[available_columns]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(path, index=False)

    return str(path)
