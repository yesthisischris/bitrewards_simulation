# Current Project Status

## Overview
- Poetry-managed repo (Python 3.12) with new `bitrewards_abm` package structured into `domain/`, `infrastructure/`, and `simulation/`.
- PR4 implemented: contribution type taxonomy, parameter-driven splits, reward tracking by type/role, satisfaction/churn lifecycle, and refreshed visuals; clean architecture, no inline comments.
- Batch runner emits time-series and run-summary CSVs for parameter sweeps.

## Implemented Components
- `src/bitrewards_abm/domain`
  - `entities.py`: `ContributionType` enum (`core_research`, `funding`, `supporting`), `Contribution`, `UsageEvent`.
  - `parameters.py`: `SimulationParameters` including gas fee rate, tracing accuracy, type-specific base shares, derivative splits, and funding splits with helper accessors.
- `src/bitrewards_abm/infrastructure/graph_store.py`: NetworkX-backed DAG with split lookups for reward propagation.
- `src/bitrewards_abm/simulation`
  - `agents.py`: `CreatorAgent`, `InvestorAgent`, `UserAgent`, `EconomicAgent`; creators mint work with parents, investors buy funding contributions, users generate usage events.
  - `model.py`: `BitRewardsModel` tracks cumulative rewards by contribution type and by role (`total_reward_paid_by_type`, `total_reward_paid_by_role`), exposes per type and per role metrics via the `DataCollector` (contribution counts, totals by type, incomes by role, income shares), and distinguishes per-step vs run-level fee flow with `cumulative_fee_distributed`.
- `src/bitrewards_abm/run_simulation.py`: one-off runner printing tail of model metrics.
- `experiments/run_batch.py`: generalized `run_experiments` to accept `out_dir`, `base_parameters`, and `variable_params`, logging key parameters into both `timeseries.csv` and `run_summary.csv` alongside run-level satisfaction averages.
- `docs/data_schema.md`: documents the stable schema for `timeseries.csv` and `run_summary.csv`, including units and interpretation of each column.
- `visuals/story_pack.py`: adds sustainability and fairness views (active agents and satisfaction by role over time, role reward shares across runs, creator Gini vs creator reward share) alongside the existing ROI and trajectory plots.

## Outputs
- Batch runs emit `data/timeseries.csv` (per-step metrics per run) and `data/run_summary.csv` (final-step metrics plus run-level satisfaction means), using the documented schema in `docs/data_schema.md`.
- Time series columns now cover contribution counts by type, cumulative vs per-step fee flow, total rewards by type, total income by role, and income shares alongside churn, satisfaction, and activity metrics.
- Visual bundle includes trajectory, ROI views, creator satisfaction and churn, active population and satisfaction by role, role reward shares across runs, and creator inequality vs creator reward share.

## Tooling & Config
- Runtime deps: `mesa`, `networkx`, `numpy`, `pandas`; dev deps: `black`, `ruff`, `pytest`, `mypy`, `ipykernel`.
- In-project virtualenv via `poetry.toml`; packages published from `src` include `bitrewards_abm` (and legacy `bitrewards_simulation` remains).

## What’s Not Implemented Yet
- Scenario labeling in outputs (for example explicit config names per run).
- Per agent panel exports beyond aggregate role and type metrics.
- Additional fairness metrics (for example role-specific Gini, tail concentration of income).

## Suggested Next Steps
- Add scenario labels and config metadata to outputs and visuals.
- Export per-agent panels to pair with aggregate role and type metrics.
- Broaden fairness diagnostics with role-specific inequality and tail concentration measures.
