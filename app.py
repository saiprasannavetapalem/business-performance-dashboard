import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Business Performance Dashboard",
    page_icon="📈",
    layout="wide"
)

DEFAULT_FILE = "data/Business_Performance_Synthetic_Dataset.xlsx"

REQUIRED_COLS = [
    "Month",
    "Product",
    "Leads",
    "New_Customers",
    "Churned_Customers",
    "Active_Customers",
    "Revenue",
]

# =========================
# HELPERS
# =========================
def validate_columns(df):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

def parse_month(df):
    df = df.copy()
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce", format="%b-%Y")
    if df["Month"].isna().any():
        df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    if df["Month"].isna().any():
        raise ValueError("Month column could not be parsed")
    return df

def compute_kpis(df):
    df = df.copy()
    df["conversion_rate"] = df["New_Customers"] / df["Leads"]
    df["churn_rate"] = df["Churned_Customers"] / df["Active_Customers"]
    df["arpu"] = df["Revenue"] / df["Active_Customers"]
    df = df.sort_values(["Product", "Month"])
    df["rev_mom_growth"] = df.groupby("Product")["Revenue"].pct_change()
    return df

def money(x):
    return f"${x:,.0f}" if pd.notna(x) else "—"

def pct(x):
    return f"{x*100:.1f}%" if pd.notna(x) else "—"

@st.cache_data
def load_data(source):
    df = pd.read_excel(source)
    validate_columns(df)
    df = parse_month(df)
    return compute_kpis(df)

# =========================
# APP UI
# =========================
st.title("📈 Business Performance Dashboard")
st.caption(
    "Built by Sai Prasanna V | Business Analytics Portfolio "
    "— Synthetic data only (no real customer data)"
)

with st.sidebar:
    st.header("Data Source")
    uploaded = st.file_uploader("Upload Excel file", type=["xlsx"])
    use_default = st.checkbox("Use default sample dataset", value=uploaded is None)

try:
    if uploaded:
        df = load_data(uploaded)
        source = "Uploaded file"
    else:
        if not use_default:
            st.stop()
        df = load_data(DEFAULT_FILE)
        source = DEFAULT_FILE
except Exception as e:
    st.error(str(e))
    st.stop()

st.markdown(f"**Using:** `{source}`")

# =========================
# FILTERS
# =========================
with st.sidebar:
    st.header("Filters")
    product = st.selectbox(
        "Product",
        ["All"] + sorted(df["Product"].unique())
    )

    min_m, max_m = df["Month"].min(), df["Month"].max()
    date_range = st.slider(
        "Month range",
        min_value=min_m.to_pydatetime(),
        max_value=max_m.to_pydatetime(),
        value=(min_m.to_pydatetime(), max_m.to_pydatetime()),
        format="MMM YYYY"
    )

start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

f = df[(df["Month"] >= start) & (df["Month"] <= end)]
if product != "All":
    f = f[f["Product"] == product]

# =========================
# KPI CARDS
# =========================
total_revenue = f["Revenue"].sum()
avg_conv = f["conversion_rate"].mean()
avg_churn = f["churn_rate"].mean()
avg_arpu = f["arpu"].mean()

latest_month = f["Month"].max()
prev_months = sorted(f["Month"].unique())
mom_growth = None
if len(prev_months) >= 2:
    prev = prev_months[-2]
    rev_latest = f[f["Month"] == latest_month]["Revenue"].sum()
    rev_prev = f[f["Month"] == prev]["Revenue"].sum()
    mom_growth = (rev_latest - rev_prev) / rev_prev if rev_prev else None

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Revenue", money(total_revenue))
c2.metric("MoM Growth", pct(mom_growth))
c3.metric("Avg Conversion", pct(avg_conv))
c4.metric("Avg Churn", pct(avg_churn))
c5.metric("Avg ARPU", money(avg_arpu))

st.divider()

# =========================
# CHARTS
# =========================
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Revenue Trend")
    fig = px.line(
        f.groupby(["Month", "Product"], as_index=False)["Revenue"].sum(),
        x="Month",
        y="Revenue",
        color="Product",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Funnel Snapshot")
    funnel = f.groupby("Product", as_index=False)[
        ["Leads", "New_Customers"]
    ].sum()

    fig2 = px.bar(
        funnel.melt(id_vars="Product", var_name="Stage", value_name="Count"),
        x="Stage",
        y="Count",
        color="Product",
        barmode="group"
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

col3, col4, col5 = st.columns(3)

with col3:
    st.subheader("Conversion Rate")
    fig3 = px.line(
        f,
        x="Month",
        y="conversion_rate",
        color="Product",
        markers=True
    )
    fig3.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Churn Rate")
    fig4 = px.line(
        f,
        x="Month",
        y="churn_rate",
        color="Product",
        markers=True
    )
    fig4.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig4, use_container_width=True)

with col5:
    st.subheader("ARPU")
    fig5 = px.line(
        f,
        x="Month",
        y="arpu",
        color="Product",
        markers=True
    )
    st.plotly_chart(fig5, use_container_width=True)

st.divider()

# =========================
# INSIGHTS
# =========================
st.subheader("Executive Insights")

by_product = (
    f.groupby("Product", as_index=False)
     .agg(
         revenue=("Revenue", "sum"),
         arpu=("arpu", "mean"),
         churn=("churn_rate", "mean"),
         conversion=("conversion_rate", "mean"),
     )
)

top_rev = by_product.sort_values("revenue", ascending=False).iloc[0]["Product"]
top_arpu = by_product.sort_values("arpu", ascending=False).iloc[0]["Product"]
low_churn = by_product.sort_values("churn").iloc[0]["Product"]

st.markdown(f"""
- **Top revenue driver:** {top_rev}  
- **Highest customer value (ARPU):** {top_arpu}  
- **Lowest churn risk:** {low_churn}  
- **Decision cue:** Invest in retention and upsell where ARPU is high and churn is low.
""")

st.info(
    "Governance note: This dashboard uses **synthetic data only**. "
    "No real customer or financial data was used."
)
