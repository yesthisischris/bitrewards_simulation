# Usage

## Run simulations

Single run:
```bash
poetry run python -m bitrewards_abm.run_simulation --config configs/baseline.toml --steps 200 --seed 42
```
- `--config` is optional; without it the defaults in `SimulationParameters` are used.
- `--steps` overrides `max_steps` from the config.
- `--seed` defaults to `experiment.random_seed_base` when present in the config.

Batch run:
```bash
poetry run python experiments/run_batch.py --config configs/baseline.toml --out-dir data/baseline
```
- `[simulation]` values build `SimulationParameters`; `[experiment.sweeps]` is expanded as a Cartesian product; each point runs `runs_per_config` reps.
- Seeds come from `random_seed_base + run_id` when `random_seed_base` is set.
- Outputs are written to `--out-dir` as `timeseries.csv` and `run_summary.csv`.

## Config schema (TOML)

`[simulation]` maps directly to `SimulationParameters`. Common groups:
- Population and roles: `creator_count`, `investor_count`, `user_count`, `supporting_creator_fraction`, `min_creator_skill`, `max_creator_skill`, `max_steps`
- Behavior and usage: `creator_base_contribution_probability`, `quality_noise_scale`, `user_usage_probability`, `user_mean_usage_rate`, `base_gross_value`, `usage_shock_std`
- Graph and tracing: `gas_fee_share_rate`, `tracing_accuracy`, `tracing_false_positive_rate`, `default_derivative_split`, `supporting_derivative_split`, `core_research_base_royalty_share`, `funding_base_royalty_share`, `supporting_base_royalty_share`, `royalty_accrual_per_usage`, `royalty_batch_interval`
- Funding: `initial_investor_budget`, `funding_min_amount`, `funding_max_amount`, `funding_royalty_min`, `funding_royalty_max`, `funding_split_fraction`, `investor_max_funding_per_step`, `investor_min_target_quality`, `funding_lockup_period_steps`
- Satisfaction and churn: `initial_agent_satisfaction`, `aspiration_income_per_step`, `satisfaction_logistic_k`, `satisfaction_churn_threshold`, `satisfaction_churn_window`, `creator_roi_exit_threshold`, `investor_roi_exit_threshold`, `user_roi_exit_threshold`, `roi_churn_window`, `satisfaction_noise_std`, `creator_contribution_cost`, `disable_churn`
- Arrivals and identity: `creator_arrival_rate`, `investor_arrival_rate`, `user_arrival_rate`, ROI sensitivities per role, `identity_creation_cost`
- Reputation and treasury: `min_reputation_for_full_rewards`, `reputation_gain_per_usage`, `reputation_decay_per_step`, `reputation_penalty_for_churn`, `treasury_fee_rate`, `treasury_funding_rate`, `payout_lag_steps`
- Honor Seal: `honor_seal_enabled`, `honor_seal_initial_adoption_rate`, `honor_seal_mint_cost_btc`, `honor_seal_demand_multiplier`, `honor_seal_unsealed_penalty_multiplier`, `honor_seal_fake_rate`, `honor_seal_fake_detection_prob_per_step`, `honor_seal_enforcement_ramp_steps`, `honor_seal_dishonored_penalty_multiplier`

Contributions map to Bitcoin ordinal NFTs; rewards and fees are tracked in BTC terms without a native fungible token supply.

`[experiment]` controls batching:
- `name` defaults to the filename stem.
- `runs_per_config` defaults to `4`.
- `steps_per_run` overrides `max_steps` if set.
- `random_seed_base` seeds runs when provided.
- `[experiment.sweeps]` contains parameter names mapped to lists (singletons are allowed); values are merged into the base parameters and recorded in the outputs.

## Data outputs

Per batch:
- `timeseries.csv`: one row per step per run with counts, fees, ROI, satisfaction, churn, contribution-type counts, cumulative rewards by type and role, treasury balances, new agent counts, lockup counts, role income shares, `run_id`, `rep`, `scenario_name`, and logged parameter columns (`creator_base_contribution_probability`, `user_usage_probability`, `gas_fee_share_rate`, `funding_split_fraction`, `tracing_accuracy`, `default_derivative_split`, `supporting_derivative_split`, `core_research_base_royalty_share`, `funding_base_royalty_share`, `supporting_base_royalty_share`, `aspiration_income_per_step`, `satisfaction_logistic_k`, `satisfaction_churn_threshold`, `satisfaction_churn_window`, plus any sweep overrides). An `index` column comes from resetting the DataFrame index.
- `run_summary.csv`: one row per run using the final step plus run-level means. Contains the same metrics at the final step, `mean_creator_satisfaction_over_run`, `mean_investor_satisfaction_over_run`, `mean_user_satisfaction_over_run`, tracing diagnostics (`tracing_true_links`, `tracing_detected_true_links`, `tracing_false_positive_links`, `tracing_missed_true_links`), `run_id`, `rep`, `scenario_name`, and the same parameter columns as `timeseries.csv`.

## Scenarios

Reference configs in `configs/` with matching output directories under `data/` once you run the batches:
- Baseline (`baseline.toml`)
- Low tracing accuracy (`low_tracing_accuracy.toml`)
- High funding share (`high_funding_share.toml`)
- High investor share (`high_investor_share.toml`)

## Analysis and visuals

Story pack (single run):
```bash
poetry run python visuals/story_pack.py \
  --timeseries data/baseline/timeseries.csv \
  --run-summary data/baseline/run_summary.csv \
  --run-id 0 \
  --output-dir visuals/output_baseline
```

Story pack with scenario comparison (timeseries/run-summary are still required for the single-run plots):
```bash
poetry run python visuals/story_pack.py \
  --timeseries data/baseline/timeseries.csv \
  --run-summary data/baseline/run_summary.csv \
  --scenario-dir data/baseline \
  --scenario-dir data/low_tracing_accuracy \
  --scenario-dir data/high_funding_share \
  --output-dir visuals/output_comparison
```

Additional dashboards:
```bash
poetry run python visuals/abm_visuals.py \
  --timeseries data/baseline/timeseries.csv \
  --run-summary data/baseline/run_summary.csv \
  --run-id 0 \
  --output-dir visuals/output_abm
```

Full in-memory generation with frames and panels:
```bash
poetry run python scripts/generate_visualizations.py
```
Outputs land in `visuals/generated/`.
