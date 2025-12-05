# Usage

## Run simulations

Single run:
```bash
poetry run python -m bitrewards_abm.run_simulation --config configs/baseline.toml --steps 200 --seed 42
```

Batch run:
```bash
poetry run python experiments/run_batch.py --config configs/baseline.toml --out-dir data/baseline
```
The batch harness builds parameters from `[simulation]`, sweeps `[experiment.sweeps]`, runs `runs_per_config` reps, and writes `timeseries.csv` and `run_summary.csv` to `--out-dir`.

## Config schema (TOML)

`[simulation]`: defaults for one run; fields map to `SimulationParameters`.
- Population and horizon: counts per role, `max_steps`
- Behavior: contribution probability, quality noise, usage probability and mean rate, base gross value, usage shock, tracing accuracy
- Splits and funding: gas fee share, derivative splits, base royalty shares, funding split and cost, investor targeting settings
- Satisfaction/churn: aspiration income, logistic slope, churn threshold/window, ROI thresholds and window, satisfaction noise
- Treasury and token: treasury fee/funding rates, token supply/inflation/burn
- Arrivals and frictions: arrival rates and sensitivities, lockup period, payout lag, creator contribution cost
- Reputation and identity: min reputation for full rewards, gain/decay/penalty settings, identity creation cost

`[experiment]`: batch controls.
- `name`, `runs_per_config`, `steps_per_run`, `random_seed_base`
- `[experiment.sweeps]`: parameter names to lists; Cartesian product is run

## Data outputs

Per batch:
- `timeseries.csv`: one row per step per run with activity, population, fees, ROI, satisfaction/churn, contribution-type counts and rewards, role income shares, and repeated parameter columns plus `scenario_name`.
- `run_summary.csv`: one row per run with final-step values, run-level satisfaction averages, role income shares, and parameter columns.

Key columns to expect: `run_id`, `rep`, `step`, `scenario_name`, `contribution_count`, `usage_event_count`, `active_creator_count`, `active_investor_count`, `active_user_count`, `total_fee_distributed`, `cumulative_fee_distributed`, `creator_wealth_gini`, `investor_mean_roi`, satisfaction means, churn counts, contribution-type counts and rewards, role income shares, and the main parameters (gas fee share, funding split, tracing accuracy, derivative splits, base royalty shares, aspiration and churn settings).

## Scenarios

Reference configs in `configs/` with matching output directories under `data/`:
- Baseline: balanced parameters; expect some churn, modest investor ROI.
- Low tracing accuracy: reduced `tracing_accuracy`; expect upstream rewards and ROI to drop.
- High funding share: higher `funding_split_fraction`; investor ROI rises, creator share may fall.
- High investor share: higher fee share plus higher funding split; total rewards grow, investor capture rises.

Document new scenarios with intent, key parameter changes, and output path.

## Analysis and visuals

Story pack:
```bash
poetry run python visuals/story_pack.py \
  --timeseries data/baseline/timeseries.csv \
  --run-summary data/baseline/run_summary.csv \
  --run-id 0 \
  --output-dir visuals/output_baseline
```

Scenario comparison:
```bash
poetry run python visuals/story_pack.py \
  --scenario-dir data/baseline \
  --scenario-dir data/low_tracing_accuracy \
  --scenario-dir data/high_funding_share \
  --output-dir visuals/output_comparison
```

Quick dashboard:
```bash
poetry run python visuals/kosmos_reference.py \
  --timeseries data/baseline/timeseries.csv \
  --run-summary data/baseline/run_summary.csv \
  --output-dir visuals/output_baseline
```

Common analyses: sustainability vs churn and ROI, role income fairness, tracing robustness, and phase transitions over fee and funding splits. Use `run_summary.csv` for comparisons and `timeseries.csv` for dynamics.

Generate fresh visuals from a single in-memory run:
```bash
poetry run python scripts/generate_visualizations.py
```
Artifacts land in `visuals/generated/`:
- `dag_frames/dag_step_<####>.png` (per-step DAG snapshots for animation or post-processing)
- `system_map.png`
- `role_income_dashboard.png`
- `dag_snapshot.png`
- `ai_tracing_panel.png`
- `life_of_contribution_<id>.png`
