# Model

## At a glance

This model currently corresponds to the BITrewards whitepaper V4 (docs/whitepaper_v4.md), with some simplifying assumptions.

- Agents: creators, investors, users
- Structure: contribution DAG with edge splits for royalties and funding
- Economics: fees from usage, funding principal transfers, treasury cut, reputation gates, lockups, payout lags, token supply tracking
- Objectives: evaluate sustainability, fairness, investor ROI, and failure modes

## Architecture

- Domain (`src/bitrewards_abm/domain`): entities, parameters
- Infrastructure (`src/bitrewards_abm/infrastructure`): graph store and royalty traversal
- Simulation (`src/bitrewards_abm/simulation`): agents, model step loop, payout engine
- Experiment harness (`experiments/run_batch.py`): builds parameters, runs sweeps, writes CSVs
- Visuals (`visuals/`): read CSVs only

## Core dynamics

- Usage and fees: usage events mint `total_fee = gross_value * gas_fee_share_rate * base_share(type)`; treasury takes `treasury_fee_rate * total_fee`; remaining pool flows through the DAG via edge splits.
- Funding: investors pay `funding_contribution_cost`; creator receives `(1 - treasury_funding_rate)` share, treasury receives the rest; funding edges add fixed splits on targets.
- Reputation and identity: payouts scale by `max(0, reputation / min_reputation_for_full_rewards)`; gains on payout, decay per step, penalty on churn; optional `identity_creation_cost` credited to treasury.
- Satisfaction and churn: agents track ROI from cumulative income and cost; creators and investors churn when ROI is below threshold and low-satisfaction streak exceeds window; users use aspiration-based satisfaction with noise.
- Arrivals and usage volume: Poisson arrivals per role with ROI-sensitive rates; users activate with `user_usage_probability`, then draw `Poisson(user_mean_usage_rate)` events with optional log-normal shock.
- Capital frictions: funding lockups reroute locked funding shares to treasury; payout lag buffers DAG payouts and flushes every `payout_lag_steps`.
- Token layer: fee minting increases supply; inflation adds `token_inflation_rate * total_supply`; buybacks burn `token_buyback_burn_rate * treasury_balance`; holding times tracked via balance-change EMAs.

## Parameter highlights

Common fields from `SimulationParameters`:
- Population and horizon: `creator_count`, `investor_count`, `user_count`, `max_steps`
- Behavior and usage: `creator_base_contribution_probability`, `quality_noise_scale`, `user_usage_probability`, `user_mean_usage_rate`, `base_gross_value`, `usage_shock_std`, `tracing_accuracy`
- Royalty structure: `gas_fee_share_rate`, `core_research_base_royalty_share`, `supporting_base_royalty_share`, `funding_base_royalty_share`, `default_derivative_split`, `supporting_derivative_split`, `funding_split_fraction`, `funding_contribution_cost`
- Funding behavior: `investor_max_funding_per_step`, `investor_min_target_quality`
- Treasury: `treasury_fee_rate`, `treasury_funding_rate`
- Satisfaction and churn: `aspiration_income_per_step`, `satisfaction_logistic_k`, `satisfaction_churn_threshold`, `satisfaction_churn_window`, `creator_roi_exit_threshold`, `investor_roi_exit_threshold`, `user_roi_exit_threshold`, `roi_churn_window`, `satisfaction_noise_std`
- Arrivals: `creator_arrival_rate`, `investor_arrival_rate`, `user_arrival_rate`, ROI sensitivities per role
- Frictions: `funding_lockup_period_steps`, `payout_lag_steps`, `creator_contribution_cost`
- Token: `token_initial_supply`, `token_inflation_rate`, `token_buyback_burn_rate`
- Reputation and identity: `min_reputation_for_full_rewards`, `reputation_gain_per_usage`, `reputation_decay_per_step`, `reputation_penalty_for_churn`, `identity_creation_cost`

## Instrumentation

- Rewards: `model.reward_events` tracks per-payout entries with `step`, `payout_type`, `channel`, `amount`, `recipient_id`, `recipient_role`, `source_contribution_id`.
- Usage: `model.usage_events` captures `step`, `contribution_id`, `user_id`, and realized `gross_value` for every usage event.
- Tracing quality: `model.tracing_metrics` reports `true_links`, `detected_true_links`, `false_positive_links`, and `missed_true_links`.
- Graph export: `ContributionGraph.to_networkx()` returns a `networkx.DiGraph` with contribution ids as nodes and edges carrying royalty split attributes for visualization.
