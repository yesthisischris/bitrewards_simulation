# Data Schema

This document defines the stable schema for the simulation outputs under `data/`.

The goal is that an analyst can work from this schema without reading Python code.

## Files

There are two primary CSV files:

- `data/timeseries.csv`  
  One row per step per run. Indexed by `run_id` and `step`.

- `data/run_summary.csv`  
  One row per run. Derived from the final step of each run, with a few run-level aggregates.

All columns use `snake_case`. Monetary quantities are unitless protocol tokens.

## `timeseries.csv`

Each row is a single step `step` in a single run `run_id`.

### Indexing

| Column | Type | Description |
| --- | --- | --- |
| `index` | int | Row index from `reset_index()`. Useful for debugging. |
| `run_id` | int | Unique run identifier within a batch. |
| `rep` | int | Repetition index within a parameter setting. |
| `step` | int | 1 based Mesa step counter. |

### Activity and usage

| Column | Type | Description |
| --- | --- | --- |
| `contribution_count` | int | Total contributions present in the graph at this step. |
| `usage_event_count` | int | Number of usage events processed during this step. |

### Population

| Column | Type | Description |
| --- | --- | --- |
| `active_creator_count` | int | Number of creators with `is_active = True`. |
| `active_investor_count` | int | Number of investors with `is_active = True`. |
| `active_user_count` | int | Number of users/supporters with `is_active = True`. |

### Fees and rewards

| Column | Type | Description |
| --- | --- | --- |
| `total_fee_distributed` | float | Total protocol fees distributed in this step. |
| `cumulative_fee_distributed` | float | Cumulative sum of `total_fee_distributed` from step 1 through this step. |

### Inequality and ROI

| Column | Type | Description |
| --- | --- | --- |
| `creator_wealth_gini` | float | Gini coefficient of creator wealth (0 = equal, 1 = very unequal). |
| `investor_mean_roi` | float | Mean ROI across investors with `total_invested > 0`. |

### Satisfaction and churn

| Column | Type | Description |
| --- | --- | --- |
| `mean_creator_satisfaction` | float | Mean satisfaction across creators (0 to 1). |
| `mean_investor_satisfaction` | float | Mean satisfaction across investors. |
| `mean_user_satisfaction` | float | Mean satisfaction across users/supporters. |
| `creator_churned_count` | int | Number of creators that have become inactive by this step. |
| `investor_churned_count` | int | Number of investors that have become inactive by this step. |
| `user_churned_count` | int | Number of users/supporters that have become inactive by this step. |

### Contribution types

| Column | Type | Description |
| --- | --- | --- |
| `core_research_contribution_count` | int | Number of `core_research` contributions. |
| `funding_contribution_count` | int | Number of `funding` contributions. |
| `supporting_contribution_count` | int | Number of `supporting` contributions. |
| `total_reward_core_research` | float | Cumulative royalties paid to `core_research` contributions. |
| `total_reward_funding` | float | Cumulative royalties paid to `funding` contributions. |
| `total_reward_supporting` | float | Cumulative royalties paid to `supporting` contributions. |

### Roles and fairness

| Column | Type | Description |
| --- | --- | --- |
| `total_income_creators` | float | Cumulative income to creator agents. |
| `total_income_investors` | float | Cumulative income to investor agents. |
| `total_income_users` | float | Cumulative income to user/supporter agents. |
| `role_income_share_creators` | float | `total_income_creators / cumulative_fee_distributed` (0 to 1). |
| `role_income_share_investors` | float | `total_income_investors / cumulative_fee_distributed`. |
| `role_income_share_users` | float | `total_income_users / cumulative_fee_distributed`. |

Role income shares may sum to less than 1 if some fees are unallocated because owners churned or were unreachable.

### Parameters

These columns are constant within a run and repeated on each row for convenience.

| Column | Type | Description |
| --- | --- | --- |
| `creator_base_contribution_probability` | float | Per step probability that a creator attempts a contribution. |
| `user_usage_probability` | float | Per step probability that a user triggers a usage event. |
| `gas_fee_share_rate` | float | Fraction of gross usage value routed into the reward pool. |
| `funding_split_fraction` | float | Default royalty split allocated to funding contributions on their targets. |
| `tracing_accuracy` | float | Probability that an intended parent edge is recorded in the DAG. |
| `default_derivative_split` | float | Baseline upstream royalty fraction for core research children. |
| `supporting_derivative_split` | float | Upstream fraction for supporting contributions. |
| `core_research_base_royalty_share` | float | Base royalty multiplier for core research contributions. |
| `funding_base_royalty_share` | float | Base royalty multiplier for funding contributions. |
| `supporting_base_royalty_share` | float | Base royalty multiplier for supporting contributions. |
| `aspiration_income_per_step` | float | Target income per step for satisfaction updates. |
| `satisfaction_logistic_k` | float | Slope of the logistic satisfaction response to income. |
| `satisfaction_churn_threshold` | float | Satisfaction level below which an agent accumulates churn streak. |
| `satisfaction_churn_window` | int | Number of consecutive low satisfaction steps required to churn. |

## `run_summary.csv`

`run_summary.csv` has one row per run. Each row is derived from the final step of that run.

It includes:

- All the columns from `timeseries.csv`, interpreted at the final step.  
- The same parameter columns.  
- Run-level averages of satisfaction.

Additional run-level columns:

| Column | Type | Description |
| --- | --- | --- |
| `mean_creator_satisfaction_over_run` | float | Average of `mean_creator_satisfaction` over steps in this run. |
| `mean_investor_satisfaction_over_run` | float | Average of `mean_investor_satisfaction` over steps. |
| `mean_user_satisfaction_over_run` | float | Average of `mean_user_satisfaction` over steps. |

Downstream tools should treat `run_summary.csv` as the primary high-level view and consult `timeseries.csv` when temporal dynamics matter.
