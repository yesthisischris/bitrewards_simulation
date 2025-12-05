# Story pack for the current BITrewards ABM

Use these visuals to narrate the present model: role mix, funding economics, gas vs royalties, tracing quality, ROI and churn, token and treasury.

## System and roles

**Protocol map** — Creators (core and supporting), investors, users feeding usage into the observed DAG; treasury cut and token supply bubble; payout lags and funding lockups.

**Role mix over time** — Stacked area of active creators split by core/supporting, plus investors and users; overlay contribution counts by type/kind.

## Capital and rewards

**Gas vs royalties** — Per-step lines for gas rewards and batched royalties; cumulative bars by role and contribution type.

**Funding economics** — Histograms of funding amounts and royalty percents; time series of funding contributions outstanding and locked positions; investor ROI trajectory.

## Behavior and outcomes

**ROI, satisfaction, churn** — Lines for ROI and satisfaction by role with churn markers; note lockup and payout windows.

**Usage and demand** — Bars for usage events per step; line for expected usage (users × probability × mean rate); optional shock band when usage_shock_std > 0.

## Tracing quality

**Tracing diagnostics** — Bars for true_links, detected_true_links, false_positive_links, missed_true_links; optional payout leakage to wrong ancestors.

**Observed vs true DAG snippet** — A sampled contribution showing true_parents vs observed parent and splits.

## Token and treasury

**Token supply and holding** — Stacked area of circulating vs burned; line for total supply and mean_token_holding_time_steps.

**Treasury flows** — Bars for cumulative inflows/outflows; line for balance; optional split by fee vs identity/funding cuts.

## Delivery checklist

- Generate charts with `visuals/abm_visuals.py` from `data/timeseries.csv` and `data/run_summary.csv`.
- Replace legacy PNGs in `visuals/output/` with the refreshed set.
- Ensure tracing metrics (tracing_true_links, tracing_detected_true_links, tracing_false_positive_links, tracing_missed_true_links) are present in `run_summary.csv` so tracing visuals render.***
