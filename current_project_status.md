# Current Project Status

## Overview
- Poetry-managed repo (Python 3.12) with new `bitrewards_abm` package structured into `domain/`, `infrastructure/`, and `simulation/`.
- PR2 implemented: activity generation plus fee sharing, royalty propagation, and investor funding edges; clean architecture, no inline comments.
- Batch runner emits time-series and run-summary CSVs for parameter sweeps.

## Implemented Components
- `src/bitrewards_abm/domain`
  - `entities.py`: `ContributionType` enum (`software_code`, `dataset`, `funding`), `Contribution`, `UsageEvent`.
  - `parameters.py`: `SimulationParameters` including gas fee rate, tracing accuracy, default splits, funding splits, investor budgets.
- `src/bitrewards_abm/infrastructure/graph_store.py`: NetworkX-backed DAG with split lookups for reward propagation.
- `src/bitrewards_abm/simulation`
  - `agents.py`: `CreatorAgent`, `InvestorAgent`, `UserAgent`, `EconomicAgent`; creators mint work with parents, investors buy funding contributions, users generate usage events.
  - `model.py`: `BitRewardsModel` builds the graph, distributes fee pools upstream, tracks wealth, Gini for creators, mean investor ROI, and now applies satisfaction/churn lifecycle updates each step.
- `src/bitrewards_abm/run_simulation.py`: one-off runner printing tail of model metrics.
- `experiments/run_batch.py`: sweeps core parameters (`creator_base_contribution_probability`, `user_usage_probability`, `gas_fee_share_rate`, `funding_split_fraction`) with repetitions; writes CSVs.
- `visuals/story_pack.py`: generates visuals from PR2/PR3 outputs (trajectory per run, creator wealth histogram, investor ROI vs split/fee, creator satisfaction vs churn).

## Outputs
- Latest batch: `data/timeseries.csv` columns include counts plus `total_fee_distributed`, `creator_wealth_gini`, `investor_mean_roi`, `mean_*_satisfaction`, and churn counts per role; 8 runs (2 reps × 4 combos) × 200 steps.
- `data/run_summary.csv`: final-step metrics per run (includes satisfaction and churn).
- Visual outputs from story pack: `visuals/output/run_0_trajectory.png`, `run_0_creator_satisfaction_churn.png`, `investor_roi_vs_split.png`, `investor_roi_vs_fee_rate.png` (creator wealth histogram generates when given an agent CSV).

## Tooling & Config
- Runtime deps: `mesa`, `networkx`, `numpy`, `pandas`; dev deps: `black`, `ruff`, `pytest`, `mypy`, `ipykernel`.
- In-project virtualenv via `poetry.toml`; packages published from `src` include `bitrewards_abm` (and legacy `bitrewards_simulation` remains).

## What’s Not Implemented Yet
- Richer contribution types beyond funding/work, project-level modeling, investor strategy beyond quality threshold, per-role aspiration tuning.

## Suggested Next Steps
- Extend contribution types and type-specific splits; richer investor heuristics using historical returns; expand metrics to per-type counts and ROI distributions; per-agent panel exports for deeper analysis.
