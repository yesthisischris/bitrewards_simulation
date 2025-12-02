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
- `src/bitrewards_abm/experiment/config.py`: loads TOML experiment configs into `SimulationParameters` and `ExperimentConfig`, including sweeps, steps per run, and seed bases.
- `src/bitrewards_abm/run_simulation.py`: CLI for single runs with optional TOML config, step override, and RNG seed override.
- `experiments/run_batch.py`: config-driven batch runner that sweeps `[experiment.sweeps]`, applies deterministic seeds from `random_seed_base`, logs key parameters and scenario names into `timeseries.csv` and `run_summary.csv`, and computes run-level satisfaction means.
- `docs/data_schema.md`: documents the stable schema for `timeseries.csv` and `run_summary.csv`, including units, interpretation, and `scenario_name`.
- `docs/running_experiments.md`: walkthrough for single runs, batch runs, outputs, and visuals.
- `visuals/story_pack.py`: adds sustainability and fairness views (active agents and satisfaction by role over time, role reward shares across runs, creator Gini vs creator reward share) and scenario comparison plots (investor ROI, creator satisfaction, creator churn) alongside the existing ROI and trajectory plots.
- `visuals/kosmos_reference.py`: compact dashboard for a reference scenario (active agents, satisfaction and churn, role reward shares).
- `configs/`: named scenarios (`baseline.toml`, `low_tracing_accuracy.toml`, `high_funding_share.toml`, `high_investor_share.toml`) for reproducible batches.
- `docs/running_experiments.md`: walkthrough for single runs, batch runs, outputs, and visuals.
- `docs/kosmos_brief.md`: concise handoff for Kosmos describing objectives, model, data schema, scenarios, and research questions.
- `data/reference/`: placeholder layout for per-scenario reference datasets (`timeseries.csv`, `run_summary.csv`).
- `tests/test_kosmos_reference.py`: smoke test to ensure scenario configs load and produce non-degenerate runs.

## Outputs
- Batch runs emit `timeseries.csv` (per-step metrics per run) and `run_summary.csv` (final-step metrics plus run-level satisfaction means) per scenario directory, using the documented schema in `docs/data_schema.md`.
- Time series columns cover contribution counts by type, cumulative vs per-step fee flow, total rewards by type, total income by role, income shares, churn, satisfaction, activity metrics, and scenario labels.
- Visual bundle includes trajectory, ROI views, creator satisfaction and churn, active population and satisfaction by role, role reward shares across runs, and creator inequality vs creator reward share.

## Tooling & Config
- Runtime deps: `mesa`, `networkx`, `numpy`, `pandas`; dev deps: `black`, `ruff`, `pytest`, `mypy`, `ipykernel`.
- In-project virtualenv via `poetry.toml`; packages published from `src` include `bitrewards_abm` (and legacy `bitrewards_simulation` remains). Config-driven experiments live under `configs/`.

## What’s Not Implemented Yet
- Per agent panel exports beyond aggregate role and type metrics.
- Additional fairness metrics (for example role-specific Gini, tail concentration of income).
- Deeper empirical calibration of the four scenarios and publishing full reference datasets.

## Suggested Next Steps
- Add per-agent panel exports to complement scenario-level aggregates.
- Broaden fairness diagnostics with role-specific inequality and tail concentration measures.
- Publish reference scenario bundles and labels for downstream tools such as Kosmos.
