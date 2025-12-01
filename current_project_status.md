# Current Project Status

## Overview
- Repository scaffolded with Poetry (Python 3.12), src layout at `src/bitrewards_simulation`.
- PR1 implemented as an activity-only Mesa ABM skeleton: creators mint “work” contributions, users generate usage events; no economic flows yet.
- Batch runner produces time-series CSVs for quick inspection and parameter sweeps.

## Implemented Components
- `src/bitrewards_simulation/model/agents.py`
  - `EconomicAgent`: baseline state (wealth, income placeholders, satisfaction placeholder), no churn logic.
  - `CreatorAgent`: decides to mint contributions based on intrinsic/monetary utility; adds contributions to the model.
  - `UserAgent`: generates usage events with constant gross_value and deterministic fee_amount; records events in the model.
- `src/bitrewards_simulation/model/bitrewards_model.py`
  - Holds agent collections, contribution registry, and usage events.
  - No edges/splits or reward distribution; contributions are standalone nodes.
  - DataCollector logs per-step counts: `step`, `contribution_count`, `usage_event_count`, `active_creator_count`, `active_user_count`.
- `experiments/run_batch.py`
  - Simple sweep over `max_usage_events_per_user`, `contribution_threshold`, `fee_share_rate`.
  - Runs multiple repetitions, writing `data/timeseries.csv` and `data/run_summary.csv`.

## Outputs
- Latest batch run: `data/timeseries.csv` with columns `step`, contribution and usage counts, active agent counts, run metadata; 4,800 rows (24 runs × 200 steps).
- `data/run_summary.csv` aggregates final-step metrics per run.

## Tooling & Config
- Poetry-managed deps: `mesa`, `networkx`, `numpy`, `pandas` plus dev tools (`black`, `ruff`, `pytest`, `mypy`, `ipykernel`).
- In-project virtualenv via `poetry.toml`.

## What’s Not Implemented (by design for PR1)
- No reward/royalty distribution, no wealth/ROI, no funding contributions, no contribution types beyond “work,” no parent edges/splits, no satisfaction-based churn, no project-level logic.

## Suggested Next Steps
- PR2: add royalty flow (fee pool distribution), graph edges for parent relations, and basic churn metrics.
- PR3: introduce funding contributions/investor agent, contribution types, and richer metrics (wealth, Gini, ROI).
