"""Ad Campaign Analyzer: a Streamlit dashboard for campaign performance."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

REQUIRED_COLUMNS = [
    "date", "campaign", "platform", "impressions", "clicks", "spend", "conversions", "revenue",
]
# Categorical palette slots 1-4 (fixed order); color follows the platform, not its rank.
PLATFORM_COLORS = {
    "Facebook": "#2a78d6",
    "Instagram": "#eb6834",
    "Pinterest": "#1baf7a",
    "Twitter": "#eda100",
}
FALLBACK_COLOR = "#898781"
INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"

st.set_page_config(page_title="Ad Campaign Analyzer", page_icon="📊", layout="wide")


@st.cache_data
def make_sample_data() -> pd.DataFrame:
    """Generate a reproducible demo dataset (synthetic, no real data)."""
    rng = np.random.default_rng(11)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=90)
    campaigns = [
        ("First Box 50% Off", "Facebook", 1.0, 0.035),
        ("Fresh Eats Brand Story", "Instagram", 1.4, 0.012),
        ("Unfinished Order Reminder", "Facebook", 0.6, 0.050),
        ("Office Lunch Catering", "Twitter", 0.5, 0.022),
        ("Student Meal Plan Launch", "Instagram", 1.1, 0.018),
        ("Weeknight Recipe Ideas", "Pinterest", 0.8, 0.028),
    ]
    rows = []
    for name, platform, scale, ctr in campaigns:
        for d in dates:
            impressions = int(rng.normal(4000, 800) * scale * (1.15 if d.dayofweek < 5 else 0.85))
            clicks = int(impressions * max(ctr + rng.normal(0, 0.004), 0.002))
            spend = round(clicks * rng.uniform(0.25, 0.9), 2)
            conversions = int(clicks * max(rng.normal(0.03, 0.01), 0.005))
            revenue = round(conversions * rng.uniform(12, 30), 2)
            rows.append((d, name, platform, impressions, clicks, spend, conversions, revenue))
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def load_uploaded(file) -> pd.DataFrame:
    """Read a CSV/XLSX upload and validate the expected columns."""
    df = pd.read_excel(file) if file.name.lower().endswith((".xlsx", ".xls")) else pd.read_csv(file)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")
    df["date"] = pd.to_datetime(df["date"])
    return df[REQUIRED_COLUMNS]


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived metrics to an already-aggregated frame (ratios of sums, never mean of ratios)."""
    out = df.copy()
    out["CTR"] = out["clicks"] / out["impressions"].replace(0, np.nan)
    out["CPC"] = out["spend"] / out["clicks"].replace(0, np.nan)
    out["CVR"] = out["conversions"] / out["clicks"].replace(0, np.nan)
    out["CPA"] = out["spend"] / out["conversions"].replace(0, np.nan)
    out["ROAS"] = out["revenue"] / out["spend"].replace(0, np.nan)
    return out


def aggregate(df: pd.DataFrame, by) -> pd.DataFrame:
    sums = df.groupby(by, as_index=False)[
        ["impressions", "clicks", "spend", "conversions", "revenue"]
    ].sum()
    return add_metrics(sums)


def style(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    """Apply shared chart chrome: recessive grid, no chart junk, title names the measure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK), x=0),
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED),
        legend=dict(orientation="h", y=-0.2, title=None),
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, title=None)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=None)
    return fig


def color_for(platform: str) -> str:
    return PLATFORM_COLORS.get(platform, FALLBACK_COLOR)


# ---------- Data source ----------
st.title("📊 Ad Campaign Analyzer")

with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    st.caption("Columns: " + ", ".join(REQUIRED_COLUMNS))

if upload is not None:
    try:
        data = load_uploaded(upload)
    except Exception as exc:  # surface any parse/validation problem to the user
        st.error(f"Could not read file: {exc}")
        st.stop()
    # A toast fades on its own without blocking the page; show it once per uploaded file.
    upload_id = (upload.name, upload.size)
    if st.session_state.get("loaded_upload") != upload_id:
        st.session_state["loaded_upload"] = upload_id
        st.toast(
            f"Loaded {upload.name}: {len(data):,} rows, "
            f"{data['date'].min():%Y-%m-%d} to {data['date'].max():%Y-%m-%d}",
            icon="✅",
        )
else:
    data = make_sample_data()
    st.info("Showing synthetic sample data. Upload your own file in the sidebar.")

# ---------- Filters ----------
with st.sidebar:
    st.header("Filters")
    min_d, max_d = data["date"].min().date(), data["date"].max().date()
    date_range = st.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
    platforms = sorted(data["platform"].unique())
    sel_platforms = st.multiselect("Platform", platforms, default=platforms)
    campaigns = sorted(data.loc[data["platform"].isin(sel_platforms), "campaign"].unique())
    sel_campaigns = st.multiselect("Campaign", campaigns, default=campaigns)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
else:
    start = end = date_range[0] if isinstance(date_range, tuple) else date_range

df = data[
    data["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    & data["platform"].isin(sel_platforms)
    & data["campaign"].isin(sel_campaigns)
]
if df.empty:
    st.warning("No data for the selected filters.")
    st.stop()

SUM_COLS = ["impressions", "clicks", "spend", "conversions", "revenue"]
METRIC_LABELS = {
    "spend": "Spend ($)", "revenue": "Revenue ($)", "impressions": "Impressions",
    "clicks": "Clicks", "conversions": "Conversions", "CTR": "CTR", "CPC": "CPC ($)",
    "CVR": "Conversion rate", "CPA": "CPA ($)", "ROAS": "ROAS (x)",
}
RATE_METRICS = {"CTR", "CVR"}


def format_value(metric: str, value: float) -> str:
    """Format a metric value for display (no scientific notation)."""
    if metric in RATE_METRICS:
        return f"{value:.2%}"
    if metric in ("spend", "revenue"):
        return f"${value:,.0f}"
    if metric in ("CPC", "CPA"):
        return f"${value:,.2f}"
    if metric == "ROAS":
        return f"{value:.2f}x"
    return f"{value:,.0f}"
TABLE_CONFIG = {
    "spend": st.column_config.NumberColumn("Spend", format="$%.0f"),
    "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f"),
    "CTR": st.column_config.NumberColumn(format="%.2f%%"),
    "CVR": st.column_config.NumberColumn(format="%.2f%%"),
    "CPC": st.column_config.NumberColumn(format="$%.2f"),
    "CPA": st.column_config.NumberColumn(format="$%.2f"),
    "ROAS": st.column_config.NumberColumn(format="%.2fx"),
}

tab_over, tab_plat, tab_camp, tab_time = st.tabs(
    ["Overview", "Platform Comparison", "Campaign Details", "Time Series"]
)

# ---------- Overview ----------
with tab_over:
    total = add_metrics(df[SUM_COLS].sum().to_frame().T).iloc[0]
    k = st.columns(6)
    k[0].metric("Spend", f"${total.spend:,.0f}")
    k[1].metric("Revenue", f"${total.revenue:,.0f}")
    k[2].metric("Conversions", f"{total.conversions:,.0f}")
    k[3].metric("ROAS", f"{total.ROAS:.2f}x")
    k[4].metric("CTR", f"{total.CTR:.2%}")
    k[5].metric("CPA", f"${total.CPA:.2f}")

    daily = aggregate(df, "date")
    # Different scales -> two stacked charts on a shared time axis, never a dual y-axis.
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                        subplot_titles=("Daily spend ($)", "Daily conversions"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["spend"], mode="lines", name="Spend",
                             line=dict(color="#2a78d6", width=2),
                             hovertemplate="%{x|%b %d}<br>Spend $%{y:,.0f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["conversions"], mode="lines", name="Conversions",
                             line=dict(color="#eb6834", width=2),
                             hovertemplate="%{x|%b %d}<br>%{y:,.0f} conversions<extra></extra>"), row=2, col=1)
    style(fig, "Spend vs. conversions over time", 480)
    fig.update_layout(showlegend=False, hovermode="x unified")
    fig.update_annotations(font=dict(size=12, color=MUTED), x=0, xanchor="left")
    st.plotly_chart(fig)

    left, right = st.columns(2)
    with left:
        spend_share = aggregate(df, "platform").sort_values("spend")
        fig = go.Figure(go.Bar(
            x=spend_share["spend"], y=spend_share["platform"], orientation="h",
            marker_color=[color_for(p) for p in spend_share["platform"]],
            hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>"))
        st.plotly_chart(style(fig, "Spend by platform ($)", 300))
    with right:
        top = aggregate(df, ["campaign", "platform"]).nlargest(5, "ROAS").sort_values("ROAS")
        fig = go.Figure(go.Bar(
            x=top["ROAS"], y=top["campaign"], orientation="h",
            marker_color=[color_for(p) for p in top["platform"]],
            hovertemplate="%{y}<br>ROAS %{x:.2f}x<extra></extra>"))
        st.plotly_chart(style(fig, "Top 5 campaigns by ROAS", 300))

# ---------- Platform Comparison ----------
with tab_plat:
    plat = aggregate(df, "platform")
    best = plat.sort_values("CTR", ascending=False).iloc[0]
    st.metric("Highest click-through rate", f"{best.platform}: {best.CTR:.2%}")

    def platform_bar(metric: str, fmt: str, title: str) -> go.Figure:
        p = plat.sort_values(metric, ascending=False)
        fig = go.Figure(go.Bar(
            x=p["platform"], y=p[metric],
            marker_color=[color_for(x) for x in p["platform"]],
            hovertemplate=f"%{{x}}<br>{fmt}<extra></extra>",
        ))
        fig.update_traces(marker_cornerradius=4)
        return style(fig, title, 320)

    r1 = st.columns(3)
    r1[0].plotly_chart(platform_bar("CTR", "%{y:.2%}", "CTR by platform"))
    r1[1].plotly_chart(platform_bar("CPC", "$%{y:.2f}", "CPC by platform ($)"))
    r1[2].plotly_chart(platform_bar("CVR", "%{y:.2%}", "Conversion rate by platform"))
    r2 = st.columns(3)
    r2[0].plotly_chart(platform_bar("ROAS", "%{y:.2f}x", "ROAS by platform"))
    r2[1].plotly_chart(platform_bar("CPA", "$%{y:.2f}", "CPA by platform ($)"))
    r2[2].plotly_chart(platform_bar("spend", "$%{y:,.0f}", "Spend by platform ($)"))

    st.subheader("Summary")
    st.dataframe(plat.sort_values("ROAS", ascending=False), width="stretch", hide_index=True,
                 column_config=TABLE_CONFIG)

# ---------- Campaign Details ----------
with tab_camp:
    table = aggregate(df, ["campaign", "platform"])
    # Sorting only means something with more than one row.
    if len(table) > 1:
        sort_by = st.selectbox("Sort by", ["ROAS", "spend", "revenue", "conversions", "CTR", "CPA", "CPC"])
        table = table.sort_values(sort_by, ascending=sort_by in ("CPA", "CPC"))
    st.caption(f"{len(table)} campaign(s)")
    st.dataframe(table, width="stretch", hide_index=True, column_config=TABLE_CONFIG)
    st.download_button("Download CSV", table.to_csv(index=False), "campaign_details.csv", "text/csv")

# ---------- Time Series ----------
with tab_time:
    c1, c2, c3 = st.columns(3)
    metric = c1.selectbox("Metric", list(METRIC_LABELS), format_func=METRIC_LABELS.get, index=2)
    grain = c2.radio("Granularity", ["Daily", "Weekly", "Monthly"], horizontal=True)
    split = c3.radio("Split by", ["Total", "Platform", "Campaign"], horizontal=True)

    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[grain]
    ts_df = df.assign(period=df["date"].dt.to_period(freq).dt.start_time)
    group = ["period"] if split == "Total" else ["period", split.lower()]
    ts = aggregate(ts_df, group)

    if split == "Platform":
        fig = px.line(ts, x="period", y=metric, color="platform", color_discrete_map=PLATFORM_COLORS,
                      category_orders={"platform": list(PLATFORM_COLORS)})
    elif split == "Campaign":
        fig = px.line(ts, x="period", y=metric, color="campaign")
    else:
        fig = px.line(ts, x="period", y=metric)
        fig.update_traces(line_color="#2a78d6")
    fig.update_traces(line=dict(width=2))
    if metric in RATE_METRICS:
        fig.update_yaxes(tickformat=".1%")
    style(fig, f"{METRIC_LABELS[metric]} - {grain.lower()}", 420)
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig)

    total_ts = aggregate(ts_df, "period").sort_values("period")
    if len(total_ts) >= 2:
        first, last = total_ts[metric].iloc[0], total_ts[metric].iloc[-1]
        peak = total_ts.loc[total_ts[metric].idxmax()]
        change = (last - first) / first if first else float("nan")
        s = st.columns(3)
        s[0].metric("Latest period", format_value(metric, last), f"{change:+.1%} vs first period")
        s[1].metric("Peak", format_value(metric, peak[metric]), f"{peak['period']:%b %d, %Y}", delta_color="off")
        s[2].metric("Average", format_value(metric, total_ts[metric].mean()))
