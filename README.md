# Ad Campaign Analyzer

A Streamlit dashboard for exploring ad campaign performance. Upload a CSV or Excel file and view metrics across platforms, campaigns and time. Built with Streamlit, pandas and Plotly.

## Views

- **Overview** - headline metrics (spend, revenue, conversions, ROAS, CTR, CPA), spend vs. conversions over time, spend by platform and the top 5 campaigns by ROAS.
- **Platform Comparison** - CTR, CPC, conversion rate, ROAS, CPA and spend per platform, with the highest-CTR platform called out.
- **Campaign Details** - a campaign-level table with sorting and CSV download.
- **Time Series** - any metric by day, week or month, split by total, platform or campaign.

Sidebar filters for date range, platform and campaign apply to every view.

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```
uv run streamlit run app.py
```

Then open http://localhost:8501 and upload your file in the sidebar. With no upload, the app shows built-in synthetic demo data. Uploads are not saved, so reloading the page returns to the demo data.

A ready-made example is included: `sample_campaign_data.csv`.

## CSV format

One row per campaign per day, with these columns:

| Column | Description |
|---|---|
| `date` | Day of the data (e.g. 2026-07-01) |
| `campaign` | Campaign name |
| `platform` | Facebook, Instagram, Pinterest or Twitter |
| `impressions` | Times the ad was shown |
| `clicks` | Clicks on the ad |
| `spend` | Amount spent ($) |
| `conversions` | Purchases or sign-ups |
| `revenue` | Revenue from conversions ($) |

Other platform names still load but are drawn in gray.

## Metrics

- **ROAS** (return on ad spend) = revenue / spend
- **CTR** (click-through rate) = clicks / impressions
- **CPC** (cost per click) = spend / clicks
- **CPA** (cost per acquisition) = spend / conversions
- **CVR** (conversion rate) = conversions / clicks

Ratios are computed from summed totals, not by averaging daily ratios.

All data in this repository is synthetic.
