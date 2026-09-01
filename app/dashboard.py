"""
Streamlit dashboard for the Customer Retention & Uplift Modeling project.
Loads pre-computed results — no live model training happens here.
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.graph_objects as go

st.set_page_config(page_title="Retention Uplift Dashboard", layout="wide")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

try:
    results = pd.read_csv(DATA_DIR / "dashboard_uplift_results.csv")
    with open(DATA_DIR / "dashboard_summary.json") as f:
        summary = json.load(f)
except FileNotFoundError as e:
    st.error(f"Could not find data files: {e}")
    st.stop()

# ---- Load data ----

# ---- Header ----
st.title("Customer Retention: Who Should Get the Discount?")
st.markdown(
    "Predicting which first-time buyers are most likely to make a second "
    "purchase **if given a retention discount** — not just who's likely to "
    "return anyway."
)

# ---- Headline metrics ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Customers Evaluated", f"{summary['n_customers_evaluated']:,}")
col2.metric("Qini Coefficient", f"{summary['qini_coefficient']:.1f}", help="Higher = better ranking vs. random targeting")
col3.metric("Benefit Captured @ 20%", f"{summary['benefit_captured_at_20pct']:.1%}", help="Targeting top 20% by predicted uplift")
col4.metric("Baseline ROC-AUC", f"{summary['baseline_roc_auc']:.3f}", help="Direct outcome prediction — intentionally weak, see notes")

st.divider()

# ---- Targeting efficiency chart ----
st.subheader("Targeting Efficiency: Uplift Model vs. Random")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=results["population_pct"], y=results["pct_benefit_captured"],
    mode="lines", name="Targeting by predicted uplift", line=dict(width=3)
))
fig.add_trace(go.Scatter(
    x=[0, 1], y=[0, 1],
    mode="lines", name="Random targeting", line=dict(dash="dash", color="gray")
))
fig.update_layout(
    xaxis_title="Proportion of customers targeted",
    yaxis_title="Proportion of total benefit captured",
    height=450,
)
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    f"**Targeting the top 20% of customers by predicted uplift captures "
    f"{summary['benefit_captured_at_20pct']:.1%} of total campaign benefit** "
    f"— nearly double what random targeting would achieve at the same cost."
)

st.divider()

# ---- Interactive targeting slider ----
st.subheader("Explore: What if we target the top X%?")

pct_target = st.slider("Percent of customers targeted", 5, 100, 20, step=5)
idx = int(len(results) * pct_target / 100) - 1
idx = max(0, min(idx, len(results) - 1))
benefit_at_pct = results.iloc[idx]["pct_benefit_captured"]

col1, col2 = st.columns(2)
col1.metric("Customers Targeted", f"{pct_target}%")
col2.metric("Benefit Captured", f"{benefit_at_pct:.1%}")

efficiency_gain = benefit_at_pct / (pct_target / 100)
st.info(f"At this threshold, targeting is **{efficiency_gain:.1f}x more efficient** than random discounting.")

st.divider()

# ---- Honest findings section ----
st.subheader("Key Findings")

st.markdown(f"""
- **Predicting outcomes directly is hard**: a baseline model predicting "will this 
  customer return" achieved only {summary['baseline_roc_auc']:.3f} ROC-AUC — barely 
  above random. First-order transaction data has limited signal for this.
- **Predicting response to treatment is much more tractable**: the uplift model 
  achieved a Qini coefficient of {summary['qini_coefficient']:.1f}, showing strong 
  ability to rank customers by how much a discount would actually help.
- **This is the core insight**: even when you can't predict *what* a customer will 
  do, you can often predict *how much a specific action will change* what they do — 
  and that's the more useful question for deciding who to target.
- Adding NLP-based review sentiment did not improve prediction beyond the existing 
  numeric review score — a tested and reported negative result.
""")

st.caption(
    "Note: the discount treatment used here is simulated, since no real experiment "
    "data exists in the source dataset. Effect sizes are designed to correlate with "
    "delivery delay and review score, based on plausible retention-marketing patterns."
)
