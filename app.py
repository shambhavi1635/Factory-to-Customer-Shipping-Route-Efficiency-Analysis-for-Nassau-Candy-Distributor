from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Nassau Candy | Shipping Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).resolve().parent / "data" / "processed" / "orders_prepared.csv"

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.7rem; padding-bottom: 2.5rem; max-width: 1450px;}
      h1 {letter-spacing: -0.035em;}
      div[data-testid="stMetric"] {
        background: #f7f9fc; border: 1px solid #e8edf4;
        padding: 16px 18px; border-radius: 12px;
      }
      div[data-testid="stMetricLabel"] {font-size: 0.88rem;}
      div[data-testid="stMetricValue"] {font-size: 1.8rem;}
      .data-note {
        padding: 13px 16px; border-radius: 10px;
        background: #eef5ff; border-left: 4px solid #4d86d9;
        color: #263b58; margin: 12px 0 22px 0;
      }
      .section-note {color: #697386; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Data loading and preparation
# ---------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    for col in ["Order Date", "Ship Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["Shipping Lead Time", "Sales", "Units", "Gross Profit", "Cost"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required = ["Order Key", "Factory", "Country/Region", "Region", "State/Province"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Required columns are missing: " + ", ".join(missing))

    # One shipment is defined as one unique order handled by one factory.
    df["Shipment_ID"] = (
        df["Order Key"].fillna("Unknown").astype(str)
        + " | "
        + df["Factory"].fillna("Unknown").astype(str)
    )

    # Build route consistently; the source file does not contain a Route column.
    route_cols = ["Factory", "Country/Region", "Region", "State/Province"]
    df["Route"] = df[route_cols].fillna("Unknown").astype(str).agg(" → ".join, axis=1)

    if "Shipping Lead Time" not in df.columns:
        if {"Order Date", "Ship Date"}.issubset(df.columns):
            df["Shipping Lead Time"] = (df["Ship Date"] - df["Order Date"]).dt.days
        else:
            df["Shipping Lead Time"] = np.nan

    return df


if not DATA_PATH.exists():
    st.error(f"Could not find the data file: `{DATA_PATH}`")
    st.info(
        "Keep `app.py` in the project root and place `orders_prepared.csv` "
        "inside `data/processed/`."
    )
    st.stop()

try:
    raw_df = load_data(str(DATA_PATH))
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.stop()

if raw_df.empty:
    st.warning("The dataset contains no rows.")
    st.stop()


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------
st.sidebar.title("Filters")
st.sidebar.caption("Narrow the analysis; all sections update together.")

date_col_exists = "Order Date" in raw_df.columns and raw_df["Order Date"].notna().any()
if date_col_exists:
    min_date = raw_df["Order Date"].min().date()
    max_date = raw_df["Order Date"].max().date()
    date_range = st.sidebar.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    date_range = None

def multiselect_filter(label: str, column: str):
    values = sorted(raw_df[column].dropna().astype(str).unique().tolist())
    return st.sidebar.multiselect(label, values, default=values)

selected_regions = multiselect_filter("Region", "Region")
selected_states = multiselect_filter("State / Province", "State/Province")
selected_modes = (
    multiselect_filter("Ship mode", "Ship Mode")
    if "Ship Mode" in raw_df.columns
    else []
)

threshold_max = int(max(30, min(2000, np.nanpercentile(
    raw_df["Shipping Lead Time"].dropna(), 95
)))) if raw_df["Shipping Lead Time"].notna().any() else 365
threshold = st.sidebar.slider(
    "Lead-time threshold (days)",
    min_value=1,
    max_value=max(365, threshold_max),
    value=min(365, max(365, threshold_max)),
    help="Used to calculate the share of unique shipments above this recorded lead time.",
)

filtered = raw_df.copy()

if date_col_exists and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["Order Date"].dt.date.between(start_date, end_date)
    ]

filtered = filtered[
    filtered["Region"].fillna("").astype(str).isin(selected_regions)
    & filtered["State/Province"].fillna("").astype(str).isin(selected_states)
]

if "Ship Mode" in filtered.columns and selected_modes:
    filtered = filtered[filtered["Ship Mode"].fillna("").astype(str).isin(selected_modes)]
elif "Ship Mode" in filtered.columns and not selected_modes:
    filtered = filtered.iloc[0:0]

if filtered.empty:
    st.title("📦 Factory-to-Customer Shipping Analytics")
    st.warning("No records match the selected filters. Adjust the filters in the sidebar.")
    st.stop()


# ---------------------------------------------------------
# Shipment-level table: avoid counting product lines as shipments
# ---------------------------------------------------------
shipment_columns = [
    "Shipment_ID", "Order Key", "Factory", "Country/Region", "Region",
    "State/Province", "Route", "Shipping Lead Time",
]
for optional_col in ["Ship Mode", "Order Date", "Ship Date"]:
    if optional_col in filtered.columns:
        shipment_columns.append(optional_col)

shipments = (
    filtered[shipment_columns]
    .sort_values("Shipping Lead Time")
    .drop_duplicates(subset=["Shipment_ID"], keep="first")
    .copy()
)

shipments["Shipping Lead Time"] = pd.to_numeric(
    shipments["Shipping Lead Time"], errors="coerce"
)
valid_lt = shipments["Shipping Lead Time"].dropna()
unique_orders = filtered["Order Key"].nunique()
shipment_count = shipments["Shipment_ID"].nunique()
route_count = shipments["Route"].nunique()
mean_lt = valid_lt.mean() if not valid_lt.empty else np.nan
median_lt = valid_lt.median() if not valid_lt.empty else np.nan
delay_frequency = (
    (valid_lt > threshold).mean() * 100 if not valid_lt.empty else np.nan
)


# ---------------------------------------------------------
# Header and compact KPI overview
# ---------------------------------------------------------
st.title("📦 Factory-to-Customer Shipping Analytics")
st.caption("Nassau Candy Distributor · Route patterns, geography and shipping-mode comparison")

st.markdown(
    '<div class="data-note"><strong>Data interpretation note:</strong> '
    'The supplied dataset contains unusually large recorded lead times that have not '
    'been independently validated. Results describe recorded patterns, not confirmed '
    'real-world delivery durations or proven causes of congestion.</div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Unique orders", f"{unique_orders:,}")
k2.metric("Order–factory shipments", f"{shipment_count:,}")
k3.metric("Routes in selection", f"{route_count:,}")
k4.metric("Mean recorded lead time", f"{mean_lt:,.1f} days" if pd.notna(mean_lt) else "N/A")

st.caption(
    f"Median recorded lead time: {median_lt:,.1f} days · "
    f"Shipments above {threshold:,} days: "
    f"{delay_frequency:.1f}%" if pd.notna(delay_frequency)
    else "No valid recorded lead times are available for the current selection."
)

tab_overview, tab_geo, tab_modes, tab_routes, tab_data = st.tabs(
    ["Overview", "Geography", "Ship modes", "Route details", "Data"]
)


# ---------------------------------------------------------
# Overview: two uncluttered charts
# ---------------------------------------------------------
with tab_overview:
    st.subheader("Route performance")
    st.caption("Routes are ranked by mean recorded lead time. Full route names remain available on hover.")

    route_summary = (
        shipments.dropna(subset=["Shipping Lead Time"])
        .groupby("Route", as_index=False)
        .agg(
            Shipments=("Shipment_ID", "nunique"),
            Mean_Lead_Time=("Shipping Lead Time", "mean"),
            Median_Lead_Time=("Shipping Lead Time", "median"),
        )
    )

    if not route_summary.empty:
        left, right = st.columns(2, gap="large")

        fastest = route_summary.nsmallest(10, "Mean_Lead_Time").sort_values(
            "Mean_Lead_Time", ascending=True
        )
        with left:
            st.markdown("**10 lowest mean recorded lead times**")
            fig_fast = px.bar(
                fastest,
                x="Mean_Lead_Time",
                y="Route",
                orientation="h",
                color="Mean_Lead_Time",
                color_continuous_scale="Blues",
                hover_data={"Shipments": True, "Median_Lead_Time": ":.1f", "Mean_Lead_Time": ":.1f"},
                labels={"Mean_Lead_Time": "Mean lead time (days)", "Route": ""},
            )
            fig_fast.update_layout(
                height=440, showlegend=False, coloraxis_showscale=False,
                margin=dict(l=8, r=10, t=15, b=10), yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig_fast, use_container_width=True)

        slowest = route_summary.nlargest(10, "Mean_Lead_Time").sort_values(
            "Mean_Lead_Time", ascending=True
        )
        with right:
            st.markdown("**10 highest mean recorded lead times**")
            fig_slow = px.bar(
                slowest,
                x="Mean_Lead_Time",
                y="Route",
                orientation="h",
                color="Mean_Lead_Time",
                color_continuous_scale="OrRd",
                hover_data={"Shipments": True, "Median_Lead_Time": ":.1f", "Mean_Lead_Time": ":.1f"},
                labels={"Mean_Lead_Time": "Mean lead time (days)", "Route": ""},
            )
            fig_slow.update_layout(
                height=440, showlegend=False, coloraxis_showscale=False,
                margin=dict(l=8, r=10, t=15, b=10), yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig_slow, use_container_width=True)

        st.markdown("**Route summary**")
        display_summary = route_summary.sort_values("Shipments", ascending=False).copy()
        display_summary["Mean_Lead_Time"] = display_summary["Mean_Lead_Time"].round(1)
        display_summary["Median_Lead_Time"] = display_summary["Median_Lead_Time"].round(1)
        st.dataframe(display_summary, use_container_width=True, hide_index=True, height=300)
    else:
        st.info("No valid lead-time values are available for route comparison.")


# ---------------------------------------------------------
# Geography: US map and compact state table
# ---------------------------------------------------------
with tab_geo:
    st.subheader("Geographic shipping patterns")
    st.caption("US state map only. Canadian provinces and other non-US locations are excluded from the map.")

    us_state_codes = {
        "Alabama":"AL", "Alaska":"AK", "Arizona":"AZ", "Arkansas":"AR",
        "California":"CA", "Colorado":"CO", "Connecticut":"CT", "Delaware":"DE",
        "Florida":"FL", "Georgia":"GA", "Hawaii":"HI", "Idaho":"ID",
        "Illinois":"IL", "Indiana":"IN", "Iowa":"IA", "Kansas":"KS",
        "Kentucky":"KY", "Louisiana":"LA", "Maine":"ME", "Maryland":"MD",
        "Massachusetts":"MA", "Michigan":"MI", "Minnesota":"MN", "Mississippi":"MS",
        "Missouri":"MO", "Montana":"MT", "Nebraska":"NE", "Nevada":"NV",
        "New Hampshire":"NH", "New Jersey":"NJ", "New Mexico":"NM", "New York":"NY",
        "North Carolina":"NC", "North Dakota":"ND", "Ohio":"OH", "Oklahoma":"OK",
        "Oregon":"OR", "Pennsylvania":"PA", "Rhode Island":"RI", "South Carolina":"SC",
        "South Dakota":"SD", "Tennessee":"TN", "Texas":"TX", "Utah":"UT",
        "Vermont":"VT", "Virginia":"VA", "Washington":"WA", "West Virginia":"WV",
        "Wisconsin":"WI", "Wyoming":"WY", "District of Columbia":"DC",
    }

    geo = (
        shipments.dropna(subset=["Shipping Lead Time"])
        .groupby("State/Province", as_index=False)
        .agg(
            Total_Shipments=("Shipment_ID", "nunique"),
            Mean_Lead_Time=("Shipping Lead Time", "mean"),
            Median_Lead_Time=("Shipping Lead Time", "median"),
        )
    )
    geo["State_Code"] = geo["State/Province"].map(us_state_codes)
    us_geo = geo.dropna(subset=["State_Code"]).copy()

    if not us_geo.empty:
        left, right = st.columns([1.2, 1], gap="large")
        with left:
            fig_map = px.choropleth(
                us_geo,
                locations="State_Code",
                locationmode="USA-states",
                scope="usa",
                color="Mean_Lead_Time",
                color_continuous_scale="YlOrRd",
                hover_name="State/Province",
                hover_data={
                    "Total_Shipments": True,
                    "Mean_Lead_Time": ":.1f",
                    "Median_Lead_Time": ":.1f",
                    "State_Code": False,
                },
                labels={
                    "Mean_Lead_Time": "Mean recorded lead time (days)",
                    "Total_Shipments": "Shipments",
                    "Median_Lead_Time": "Median lead time (days)",
                },
            )
            fig_map.update_layout(
                height=470, margin=dict(l=0, r=0, t=10, b=0),
                coloraxis_colorbar=dict(title="Days"),
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with right:
            st.markdown("**States with the most shipments**")
            state_volume = geo[geo["State_Code"].notna()].sort_values(
                "Total_Shipments", ascending=False
            ).head(12)
            fig_volume = px.bar(
                state_volume.sort_values("Total_Shipments"),
                x="Total_Shipments",
                y="State/Province",
                orientation="h",
                color="Total_Shipments",
                color_continuous_scale="Blues",
                labels={"Total_Shipments": "Unique shipments", "State/Province": ""},
            )
            fig_volume.update_layout(
                height=470, showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=5, t=10, b=0),
            )
            st.plotly_chart(fig_volume, use_container_width=True)

        st.markdown("**State-level summary**")
        state_table = us_geo[
            ["State/Province", "Total_Shipments", "Mean_Lead_Time", "Median_Lead_Time"]
        ].sort_values("Total_Shipments", ascending=False).copy()
        state_table[["Mean_Lead_Time", "Median_Lead_Time"]] = state_table[
            ["Mean_Lead_Time", "Median_Lead_Time"]
        ].round(1)
        st.dataframe(state_table, use_container_width=True, hide_index=True, height=260)
    else:
        st.info("No recognized US states are present in the current filtered selection.")

    region_summary = (
        shipments.dropna(subset=["Shipping Lead Time"])
        .groupby("Region", as_index=False)
        .agg(
            Shipments=("Shipment_ID", "nunique"),
            Mean_Lead_Time=("Shipping Lead Time", "mean"),
        )
        .sort_values("Mean_Lead_Time")
    )
    if not region_summary.empty:
        st.markdown("**Recorded lead time by region**")
        fig_region = px.bar(
            region_summary,
            x="Region",
            y="Mean_Lead_Time",
            color="Mean_Lead_Time",
            color_continuous_scale="Blues",
            hover_data={"Shipments": True, "Mean_Lead_Time": ":.1f"},
            labels={"Mean_Lead_Time": "Mean recorded lead time (days)"},
        )
        fig_region.update_layout(
            height=330, showlegend=False, coloraxis_showscale=False,
            margin=dict(l=5, r=5, t=10, b=5),
        )
        st.plotly_chart(fig_region, use_container_width=True)


# ---------------------------------------------------------
# Shipping modes: two charts, no duplicate table by default
# ---------------------------------------------------------
with tab_modes:
    st.subheader("Shipping-mode comparison")
    st.caption("Comparisons use one record per order–factory shipment, not one row per product line.")

    if "Ship Mode" not in shipments.columns:
        st.info("The dataset does not contain a Ship Mode column.")
    else:
        mode_summary = (
            shipments.dropna(subset=["Shipping Lead Time"])
            .groupby("Ship Mode", as_index=False)
            .agg(
                Shipments=("Shipment_ID", "nunique"),
                Mean_Lead_Time=("Shipping Lead Time", "mean"),
                Median_Lead_Time=("Shipping Lead Time", "median"),
                Std_Lead_Time=("Shipping Lead Time", "std"),
            )
        )
        mode_summary["Lead_Time_CV_Percent"] = (
            mode_summary["Std_Lead_Time"] / mode_summary["Mean_Lead_Time"] * 100
        )
        left, right = st.columns(2, gap="large")

        with left:
            fig_mode_mean = px.bar(
                mode_summary.sort_values("Mean_Lead_Time"),
                x="Ship Mode",
                y="Mean_Lead_Time",
                color="Mean_Lead_Time",
                color_continuous_scale="Blues",
                hover_data={"Shipments": True, "Median_Lead_Time": ":.1f"},
                labels={"Mean_Lead_Time": "Mean recorded lead time (days)"},
            )
            fig_mode_mean.update_layout(
                height=390, showlegend=False, coloraxis_showscale=False,
                margin=dict(l=5, r=5, t=10, b=5),
            )
            st.plotly_chart(fig_mode_mean, use_container_width=True)

        with right:
            fig_mode_cv = px.bar(
                mode_summary.sort_values("Lead_Time_CV_Percent"),
                x="Ship Mode",
                y="Lead_Time_CV_Percent",
                color="Lead_Time_CV_Percent",
                color_continuous_scale="Oranges",
                hover_data={"Shipments": True, "Std_Lead_Time": ":.1f"},
                labels={"Lead_Time_CV_Percent": "Lead-time variability (CV, %)"},
            )
            fig_mode_cv.update_layout(
                height=390, showlegend=False, coloraxis_showscale=False,
                margin=dict(l=5, r=5, t=10, b=5),
            )
            st.plotly_chart(fig_mode_cv, use_container_width=True)

        show_mode_table = st.toggle("Show shipping-mode summary table", value=False)
        if show_mode_table:
            st.dataframe(
                mode_summary.round(2),
                use_container_width=True,
                hide_index=True,
            )

        st.info(
            "The Cost column represents product cost, not freight cost. "
            "The supplied data does not support direct shipping-cost comparisons."
        )


# ---------------------------------------------------------
# Route details: choose one route and inspect its shipments
# ---------------------------------------------------------
with tab_routes:
    st.subheader("Inspect an individual route")
    route_options = sorted(shipments["Route"].dropna().unique().tolist())
    if not route_options:
        st.info("No routes are available for the current filters.")
    else:
        chosen_route = st.selectbox("Select a route", route_options)
        route_df = shipments[shipments["Route"] == chosen_route].copy()
        route_lt = route_df["Shipping Lead Time"].dropna()

        a, b, c = st.columns(3)
        a.metric("Order–factory shipments", f"{route_df['Shipment_ID'].nunique():,}")
        b.metric(
            "Mean recorded lead time",
            f"{route_lt.mean():,.1f} days" if not route_lt.empty else "N/A",
        )
        c.metric(
            "Median recorded lead time",
            f"{route_lt.median():,.1f} days" if not route_lt.empty else "N/A",
        )

        visible_cols = [
            c for c in [
                "Order Key", "Order Date", "Ship Date", "Ship Mode", "Factory",
                "Country/Region", "Region", "State/Province", "Shipping Lead Time",
            ] if c in route_df.columns
        ]
        st.dataframe(
            route_df[visible_cols].sort_values(
                "Shipping Lead Time", ascending=False, na_position="last"
            ),
            use_container_width=True,
            hide_index=True,
            height=350,
        )

        st.download_button(
            "Download this route's shipment records",
            data=route_df.to_csv(index=False).encode("utf-8"),
            file_name="selected_route_shipments.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------
# Data: definitions and download
# ---------------------------------------------------------
with tab_data:
    st.subheader("Data definitions")
    st.markdown(
        """
        - **Unique order:** distinct `Order Key`.
        - **Order–factory shipment:** distinct combination of `Order Key` and `Factory`.
        - **Route:** `Factory → Country/Region → Region → State/Province`.
        - **Mean recorded lead time:** average `Shipping Lead Time` across unique order–factory shipments.
        - **Delay frequency:** percentage of unique shipments whose recorded lead time exceeds the selected threshold.
        - **Lead-time variability (CV):** standard deviation divided by mean recorded lead time, multiplied by 100.
        """
    )
    st.caption(
        "The route efficiency score is intentionally not shown in this compact version: "
        "a relative score can change with the filtered comparison set and may be misread as an absolute performance measure."
    )

    st.markdown("**Current filtered data**")
    st.write(f"{len(filtered):,} product-level rows · {shipment_count:,} unique order–factory shipments")
    st.download_button(
        "Download filtered product-level records",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_shipping_data.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download filtered shipment-level records",
        data=shipments.to_csv(index=False).encode("utf-8"),
        file_name="filtered_shipment_data.csv",
        mime="text/csv",
    )

st.divider()
st.caption("Nassau Candy Distributor · Exploratory analysis of supplied data")
