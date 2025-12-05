# BITrewards Simulation

Mesa ABM of the BITrewards protocol focused on economic and behavioral dynamics (contributors, investors, users) rather than blockchain internals.

- Understand sustainability, fairness, and investor ROI across parameter regimes
- Generate reproducible datasets for downstream analysis
- Compare reference scenarios and stress-test protocol assumptions

Docs live in `docs/README.md`, with details in `docs/model.md` and `docs/usage.md`.

## Quickstart

- Install: `poetry install`
- Check the suite: `poetry run pytest`
- Single run: `poetry run python -m bitrewards_abm.run_simulation --config configs/baseline.toml --steps 200 --seed 42`
- Batch runs: `poetry run python experiments/run_batch.py --config configs/baseline.toml --out-dir data/baseline`

Batch outputs land in the chosen `--out-dir` as `timeseries.csv` and `run_summary.csv`.

## Visuals and analysis

- Story pack for one run: `poetry run python visuals/story_pack.py --timeseries data/baseline/timeseries.csv --run-summary data/baseline/run_summary.csv --run-id 0 --output-dir visuals/output_baseline`
- Story pack with scenario comparison: add `--scenario-dir data/baseline --scenario-dir data/low_tracing_accuracy --scenario-dir data/high_funding_share` (timeseries/run-summary args are still required for the single-run plots).
- Additional dashboards: `poetry run python visuals/abm_visuals.py --timeseries data/baseline/timeseries.csv --run-summary data/baseline/run_summary.csv --run-id 0 --output-dir visuals/output_abm`
- Full in-memory visual set: `poetry run python scripts/generate_visualizations.py` (writes to `visuals/generated/`)

## Reference scenarios

Config files live in `configs/`:
- `baseline.toml`
- `low_tracing_accuracy.toml`
- `high_funding_share.toml`
- `high_investor_share.toml`

Run them with `experiments/run_batch.py` to populate `data/<scenario>/` and drive the visuals.
