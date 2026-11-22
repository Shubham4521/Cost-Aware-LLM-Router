import os
import altair as alt
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
st.set_page_config(page_title="Results", page_icon="📊", layout="wide")

st.title("📊 Evaluation results")
st.caption("165 prompts across math, factual, reasoning, code, writing and search. "
           "An answer passes if it scores at least 7/10.")

res = pd.read_csv(f"{ROOT}/results/phase4_cascade_results.csv")
best = res[res["router"] == "rules: search->cheap"].iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric("Quality vs always-premium", f"{best['quality_vs_premium_%']}%")
c2.metric("Cost vs always-premium", f"{best['cost_vs_premium_%']}%")
c3.metric("Avg response time", f"{best['avg_latency_s']} s")

st.subheader("Cost vs quality")
base = alt.Chart(res).encode(
    x=alt.X("cost_vs_premium_%:Q", title="Cost (% of always-premium)"),
    y=alt.Y("pass_rate:Q", title="Pass rate", scale=alt.Scale(zero=False)),
    tooltip=["router", "pass_rate", "total_cost_usd", "avg_latency_s"],
)
chart = base.mark_circle(size=140) + base.mark_text(align="left", dx=8, fontSize=11).encode(text="router:N")
st.altair_chart(chart, use_container_width=True)

st.subheader("All routers compared")
st.dataframe(res, use_container_width=True, hide_index=True)

st.subheader("Pass rate by category and tier")
s = pd.read_csv(f"{ROOT}/results/scored_results.csv", keep_default_na=False)
ev = pd.read_csv(f"{ROOT}/data/eval_set.csv", keep_default_na=False)
s = s.merge(ev[["id", "category"]], on="id")
s["passed"] = s["score"].astype(float) >= 7
pivot = s.pivot_table(index="category", columns="tier", values="passed", aggfunc="mean")
st.dataframe(pivot[["free", "cheap", "premium"]].round(2), use_container_width=True)

st.subheader("Key findings")
st.markdown("""
- A simple rule router (live questions → cheap model with search, everything else → free model)
  reached **99.3% of premium's quality at 5.2% of its cost**.
- The free model alone passed 89.7% of prompts; the tiers differed most on **search** questions.
- A perfect router would reach 95.8%, **above premium's 92.7%**, because models fail on different prompts.
- A cascade that checks answers and escalates matched the rules on quality but cost about 13× more:
  its checks flagged many correct answers as wrong.
""")
