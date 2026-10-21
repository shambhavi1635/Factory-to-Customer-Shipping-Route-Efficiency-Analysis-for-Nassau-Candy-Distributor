# Factory-to-Customer Shipping Route Efficiency Analysis for Nassau Candy Distributor

An end-to-end data analytics project exploring shipping patterns from factory to customer for the Nassau Candy Distributor dataset. The project combines data cleaning, feature engineering, route-level aggregation, geographic analysis, shipping-mode comparison, and an interactive Streamlit dashboard.

The goal is to make the supplied shipping data easier to explore and compare: which routes and regions have different recorded lead-time patterns, how shipment volume varies by location, and how the recorded metrics differ across shipping modes.

> **Data limitation:** The supplied data contains unusually large recorded lead times. These values have not been independently validated, so the analysis describes patterns in the dataset rather than confirmed real-world delivery durations. The `Cost` field represents product cost, not freight cost; it is not used as a shipping-cost measure.

---

## Project Overview

The project follows a data analytics workflow:

1. **Data cleaning and validation** — inspect the source data, standardize fields, and check data quality.
2. **Feature engineering** — prepare analysis-ready fields, including order keys, lead-time fields, and route components.
3. **Routing and aggregation** — summarize shipment activity and recorded lead-time performance by route.
4. **Efficiency benchmarking** — compare routes using descriptive lead-time and volume metrics.
5. **Geographic analysis** — examine recorded lead-time patterns across regions and states/provinces.
6. **Shipping-mode analysis** — compare recorded lead time, shipment volume, and variability across shipping modes.
7. **Interactive dashboard** — explore the results using filters, charts, tables, route details, and CSV downloads.

## Dashboard

The Streamlit dashboard is designed to keep the main view uncluttered. Its sections are organized into tabs:

- **Overview:** core KPIs and routes with the lowest and highest mean recorded lead times.
- **Geography:** US state heatmap, state-level shipment volume, and regional comparison.
- **Ship modes:** comparison of mean recorded lead time and relative variability.
- **Route details:** select a route and inspect its shipment-level records.
- **Data:** metric definitions and filtered data downloads.

The sidebar filters the dashboard by order date, region, state/province, shipping mode, and a user-selected lead-time threshold.

### Dashboard KPIs

| Metric | Definition |
|---|---|
| Unique orders | Number of distinct `Order Key` values in the filtered records. |
| Order–factory shipments | Number of distinct combinations of `Order Key` and `Factory`. |
| Routes in selection | Number of distinct route labels represented by the filtered data. |
| Mean recorded lead time | Average recorded lead time across unique order–factory shipments. |
| Median recorded lead time | Median recorded lead time across unique order–factory shipments. |
| Delay frequency | Percentage of unique shipments whose recorded lead time exceeds the selected threshold. |

A route is represented as:

`Factory → Country/Region → Region → State/Province`

The dashboard creates this route label from the available columns because the prepared dataset does not contain a dedicated `Route` column.

## Repository Structure

The project is organized into data, analysis, and dashboard components. Some notebooks export intermediate CSV files used by later analysis steps.

```text
Factory-to-Customer-Shipping-Route-Efficiency-Analysis-for-Nassau-Candy-Distributor/
│
├── data/
│   ├── raw/
│   └── processed/
│       ├── orders_prepared.csv
│       ├── orders_validated.csv
│       ├── regional_bottleneck_summary.csv
│       ├── route_level_summary.csv
│       ├── ship_mode_performance_summary.csv
│       └── state_bottleneck_summary.csv
│
├── data cleaning & validation/
│   └── data cleaning and validation notebooks
│
├── feature engineering/
│   └── feature engineering notebooks
│
├── Routing & aggregation/
│   └── route aggregation and benchmarking notebooks
│
├── geographic_analysis/
│   └── bottleneck_analysis.ipynb
│
├── performance_analysis/
│   └── shipping-mode and performance analysis notebooks
│
├── app.py
├── requirements.txt
└── README.md
```

Notebook filenames may vary as the project evolves. The processed CSVs listed above are generated analysis outputs; regenerate them by running the relevant notebooks if the underlying source data changes.

## Data and Definitions

### Main fields used

The prepared dataset includes fields such as:

- **Order information:** `Order ID`, `Order Key`, `Order Date`, `Ship Date`
- **Shipping information:** `Ship Mode`, `Shipping Lead Time`
- **Geography:** `Country/Region`, `Region`, `State/Province`, `City`, `Postal Code`
- **Factory and route information:** `Factory`, `Factory Latitude`, `Factory Longitude`
- **Business measures:** `Sales`, `Units`, `Gross Profit`, `Cost`

Not every field is used in every analysis.

### Shipment definition

The project treats an **order–factory combination** as one shipment:

`Shipment_ID = Order Key + Factory`

This prevents multiple product lines belonging to the same order and factory from being counted as separate shipments in shipment-level KPIs.

### Lead time

The project uses the dataset's recorded `Shipping Lead Time` field. In the data preparation workflow, lead time is associated with the interval between `Order Date` and `Ship Date`. Because the supplied dates and resulting intervals appear unusual, they should be validated before using them as operational service-level measures.

### Route volume

Route volume is counted as the number of unique order–factory shipments assigned to each route. This is distinct from the number of product-level rows.

### Lead-time variability

Where calculated, the coefficient of variation is:

`CV (%) = (Standard deviation of lead time / Mean lead time) × 100`

It describes relative variability in the recorded values. It does not by itself establish the cause of that variability.

### Geographic coverage

The US state heatmap includes recognized US states and the District of Columbia. Canadian provinces are not plotted on the US map. They may still appear in other filtered tables and route-level analysis when included in the source data.

---

## Technology Stack

- **Python** — analysis and data preparation
- **Pandas, NumPy** — data cleaning, transformation, and aggregation
- **Plotly Express** — interactive charts and geographic heatmap
- **Streamlit** — interactive dashboard
- **Jupyter Notebook** — exploratory analysis and workflow development
- **Git and GitHub** — version control

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/shambhavi1635/Factory-to-Customer-Shipping-Route-Efficiency-Analysis-for-Nassau-Candy-Distributor.git
cd Factory-to-Customer-Shipping-Route-Efficiency-Analysis-for-Nassau-Candy-Distributor
```

### 2. Create and activate a Python environment

Using `venv`:

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

If you use Conda, create and activate a separate environment with a Python version compatible with the installed packages.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If Streamlit or Plotly is not included in `requirements.txt`, install them with:

```bash
pip install streamlit plotly
```

### 4. Check the data location

The dashboard expects the prepared dataset at:

```text
data/processed/orders_prepared.csv
```

Keep `app.py` in the project root. If the file is missing, run the data preparation notebooks that produce `orders_prepared.csv`, or place the correctly prepared CSV at the expected path.

### 5. Launch the dashboard

From the project root, run:

```bash
streamlit run app.py
```

Streamlit will print a local address in the terminal, usually:

```text
http://localhost:8501
```

Open that address in your browser.

---

## How to Use the Dashboard

1. Start the app using `streamlit run app.py`.
2. Use the sidebar to filter by date, region, state/province, shipping mode, and lead-time threshold.
3. Review the KPI summary at the top.
4. Open **Overview** to compare route-level recorded lead times.
5. Open **Geography** to explore the US state heatmap and regional patterns.
6. Open **Ship modes** to compare recorded lead time and variability by shipping mode.
7. Open **Route details** to inspect one route and download its shipment records.
8. Open **Data** to review definitions and download filtered product-level or shipment-level CSV files.

All displayed sections respond to the active filters.

## Output Files

The processed data folder may contain the following outputs:

| File | Purpose |
|---|---|
| `orders_validated.csv` | Validated data produced by the cleaning workflow. |
| `orders_prepared.csv` | Prepared dataset used by the dashboard. |
| `route_level_summary.csv` | Route-level shipment counts and recorded lead-time statistics. |
| `regional_bottleneck_summary.csv` | Regional descriptive summary for geographic analysis. |
| `state_bottleneck_summary.csv` | State/province descriptive summary for geographic analysis. |
| `ship_mode_performance_summary.csv` | Recorded lead-time and variability summary by shipping mode. |

The precise row counts and summary values depend on the version of the source data and the filters or thresholds used during analysis.

## Interpretation and Limitations

- The lead-time values are unusually large and have not been independently validated. Treat them as **recorded lead-time values**, not verified delivery durations.
- The dataset does not establish that a route or region is congested. The project identifies descriptive patterns and potential areas for further investigation.
- `Cost` is product cost, not freight cost. The dataset therefore does not support a direct comparison of shipping costs by route or shipping mode.
- Geographic comparisons depend on the quality and consistency of state/province and country labels in the source data.
- A higher or lower recorded lead time alone does not explain why a route differs. Further operational data would be required to establish causes.
- The dashboard is intended for exploratory analysis and comparison, not as a validated transportation optimization or dispatch system.

## Future Improvements

Potential next steps include:

- Validate the date and lead-time fields against a trusted source.
- Add confirmed freight charges and service-level targets if reliable data becomes available.
- Compare route performance over time once the dates are validated.
- Add filters for factory and customer segments where the data supports them.
- Add automated data-quality checks and a repeatable pipeline for refreshing dashboard outputs.
- Deploy the Streamlit dashboard to a hosted environment if public or team access is needed.

## Author

**Shambhavi Singh**  
Integrated Dual Degree student, Metallurgical and Materials Engineering  
Indian Institute of Technology (IIT) Bhubaneswar

---

*This project was developed for data analysis and visualization practice using the supplied Nassau Candy Distributor dataset.*
