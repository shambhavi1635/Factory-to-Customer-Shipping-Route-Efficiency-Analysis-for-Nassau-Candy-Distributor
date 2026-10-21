
from pathlib import Path
import pandas as pd

data_dir = Path("data/processed")

df = pd.read_csv(data_dir / "orders_prepared.csv")
saved_routes = pd.read_csv(data_dir / "route_level_summary.csv")

route_parts = [
    "Factory",
    "Country/Region",
    "Region",
    "State/Province",
]

df["Generated_Route"] = (
    df[route_parts]
    .fillna("Unknown")
    .astype(str)
    .agg(" → ".join, axis=1)
)

generated_routes = set(df["Generated_Route"].unique())
saved_route_names = set(saved_routes["Route"].unique())

print("Routes generated from main dataset:", len(generated_routes))
print("Routes in saved route summary:", len(saved_route_names))
print("Routes common to both:", len(generated_routes & saved_route_names))
print("Generated-only routes:", len(generated_routes - saved_route_names))
print("Summary-only routes:", len(saved_route_names - generated_routes))

print("\nColumns in saved route summary:")
print(saved_routes.columns.tolist())
