# Documentation

Use this condensed set of docs to get up to speed fast.

## Start here

- What this project is: agent based simulation of the BITrewards protocol to study sustainability, fairness, and investor ROI.
- Core outputs: `timeseries.csv` (per step) and `run_summary.csv` (per run) for each scenario.

## Quickstart

```bash
poetry install
poetry run python -m bitrewards_abm.run_simulation --config configs/baseline.toml --steps 100 --seed 42
```

Batch example:

```bash
poetry run python experiments/run_batch.py --config configs/baseline.toml --out-dir data/baseline
```

## Where to go next

- Model and parameters: `docs/model.md`
- Running experiments, configs, data schema, scenarios, and analysis: `docs/usage.md`
