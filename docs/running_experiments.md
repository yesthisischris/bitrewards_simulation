# Running Experiments

This document explains how to run the BitRewards ABM and batch experiments. The full model design is in `docs/abm_design.md`.

ABM stands for agent based model. It is a simulation where many agent objects interact according to local rules.

CLI stands for command line interface.

CSV stands for comma separated values. These CSV files are the main data outputs of the simulation.

RNG stands for random number generator. Reproducible experiments use fixed RNG seeds.

## 1. Prerequisites

- Python 3.12
- Poetry

Install dependencies from the project root:

```bash
poetry install
```

## 2. Single simulation runs

You can run a single BitRewardsModel simulation using the module entrypoint:

```bash
poetry run python -m bitrewards_abm.run_simulation
```

This uses the default SimulationParameters and prints the final few rows of the model time series.

To use a configuration file:

```bash
poetry run python -m bitrewards_abm.run_simulation --config configs/baseline.toml
```

You can override the number of steps:

```bash
poetry run python -m bitrewards_abm.run_simulation \
  --config configs/baseline.toml \
  --steps 100
```

You can also provide an explicit RNG seed:

```bash
poetry run python -m bitrewards_abm.run_simulation \
  --config configs/baseline.toml \
  --seed 42
```

If `--seed` is omitted and the config has `random_seed_base`, that value is used.

## 3. Batch experiments

Batch experiments are driven by TOML configuration files under `configs/`.

Each config has two sections:
- `[simulation]` holds values for `SimulationParameters`
- `[experiment]` controls the experiment harness

An example is `configs/baseline.toml`.

Run a batch for the baseline scenario:

```bash
poetry run python experiments/run_batch.py \
  --config configs/baseline.toml \
  --out-dir data/baseline
```

This will:
- Build a base `SimulationParameters` from `[simulation]`
- Sweep over parameter combinations in `[experiment.sweeps]`
- Run `runs_per_config` repetitions per parameter combination
- Use deterministic RNG seeds if `random_seed_base` is set
- Write `timeseries.csv` and `run_summary.csv` into `data/baseline/`

Other scenarios:

```bash
poetry run python experiments/run_batch.py \
  --config configs/low_tracing_accuracy.toml \
  --out-dir data/low_tracing_accuracy
```

```bash
poetry run python experiments/run_batch.py \
  --config configs/high_funding_share.toml \
  --out-dir data/high_funding_share
```

## 4. Output layout

Each batch run writes two CSV files to the chosen output directory:
- `timeseries.csv`  
  One row per step per run. Includes indexing columns `run_id` and `step`, plus metrics for activity, satisfaction, churn, fairness, and parameters such as `gas_fee_share_rate` and `funding_split_fraction`.
- `run_summary.csv`  
  One row per run. Each row is the final step metrics for that run, plus the experiment parameters and `scenario_name`.

These files follow the documented schema in `docs/data_schema.md`.

## 5. Visualizations

The `visuals/story_pack.py` script produces plots from the CSV outputs.

### 5.1 Single scenario story

After running a batch into `data/baseline`, you can generate a story for run 0:

```bash
poetry run python visuals/story_pack.py \
  --timeseries data/baseline/timeseries.csv \
  --run-summary data/baseline/run_summary.csv \
  --run-id 0 \
  --output-dir visuals/output_baseline
```

This generates:
- A trajectory plot for contributions, usage, and fees
- An optional creator wealth histogram (if an agent CSV is provided)
- Investor ROI vs funding split and vs gas fee rate
- Creator satisfaction and churn over time
- Fairness plots for income by role and creator inequality vs reward share

### 5.2 Scenario comparison

If you run multiple configs into separate directories:
- `data/baseline`
- `data/low_tracing_accuracy`
- `data/high_funding_share`

you can generate scenario comparison plots:

```bash
poetry run python visuals/story_pack.py \
  --scenario-dir data/baseline \
  --scenario-dir data/low_tracing_accuracy \
  --scenario-dir data/high_funding_share \
  --output-dir visuals/output_comparison
```

This reads each `run_summary.csv`, attaches a scenario label, and produces bar charts that compare:
- Average investor ROI by scenario
- Average creator satisfaction by scenario
- Average creator churn count by scenario

These plots give quick answers to how outcomes differ across configs.
