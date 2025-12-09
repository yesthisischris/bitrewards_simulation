# Model

## At a glance

This model currently corresponds to the BITrewards whitepaper V4 (docs/whitepaper_v4.md), with some simplifying assumptions.

- Agents: creators, investors, users
- Structure: contribution DAG with edge splits for royalties and funding, traversed along a single preferred path
- Representation: contributions are Bitcoin ordinal NFTs; IDs map to inscribed metadata
- Economics: fees from usage, funding principal transfers, treasury cut, reputation gates, lockups, payout lags; value is tracked in BTC terms (no native token supply)
- Compliance: contributions can carry an Honor Seal status that influences demand and enforcement
- Objectives: evaluate sustainability, fairness, investor ROI, and failure modes

## Architecture

- Domain (`src/bitrewards_abm/domain`): entities, parameters
- Infrastructure (`src/bitrewards_abm/infrastructure`): graph store and royalty traversal
- Simulation (`src/bitrewards_abm/simulation`): agents, model step loop, payout engine
- Experiment harness (`experiments/run_batch.py`): builds parameters, runs sweeps, writes CSVs
- Visuals (`visuals/`): read CSVs only

## Core dynamics

- Usage and fees: usage events mint `total_fee = gross_value * gas_fee_share_rate`; treasury takes `treasury_fee_rate * total_fee`; remaining pool flows through the DAG via edge splits. Optional `royalty_accrual_per_usage` and `royalty_batch_interval` buffer payouts.
- Funding: investors pick a target above `investor_min_target_quality`, spend a uniform draw in `[funding_min_amount, funding_max_amount]` (capped by budget), and transfer it to the creator minus `treasury_funding_rate`. Funding contributions can lock rewards for `funding_lockup_period_steps` and attach funding edges using sampled `funding_royalty_min`/`funding_royalty_max` (fallback to `funding_split_fraction`).
- Tracing and graph edges: creator contributions attach to parents weighted by quality; `tracing_accuracy` and `tracing_false_positive_rate` decide whether the observed edge is correct or misattributed. Splits come from derivative or supporting defaults on the `ContributionGraph`; traversal follows a single path preferring funding edges, otherwise the highest split.
- Satisfaction and churn: satisfaction is a logistic transform of ROI (creators, investors) or income ratio (users) with optional noise. Creators and investors churn when ROI stays below thresholds for `roi_churn_window` steps; users churn when satisfaction stays below `satisfaction_churn_threshold` for `satisfaction_churn_window` steps. Set `disable_churn` to skip churn in protocol-only runs.
- Arrivals and usage volume: Poisson arrivals per role scaled by ROI sensitivity; active users trigger usage with `user_usage_probability`, emit `Poisson(user_mean_usage_rate)` events with optional log-normal shocks, and sample contributions weighted by quality.
- Reputation and identity: rewards are gated by `min_reputation_for_full_rewards`, with gains per payout, decay per step, and penalties on churn. `identity_creation_cost` is charged to new arrivals.
- Treasury and frictions: gas and royalty payouts flow as BTC; treasury cuts apply per step; payout lag buffers payments for `payout_lag_steps`; funding lockups escrow rewards until release.
- Simulation-only churn: exits can be disabled by raising ROI/satisfaction thresholds or windows or by setting `disable_churn` when strict whitepaper fidelity is desired.
- Honor Seal: roots can mint a seal with configurable adoption rate, mint cost, fake probability, and detection; derivatives inherit seal status; users bias selection toward sealed contributions with time-based ramp.
- Investor cap and tail: funding contributions track principal and cumulative rewards; investors receive full share until `investor_return_cap_multiple` times principal, then a reduced share `investor_post_cap_payout_fraction` with surplus routed to treasury when enabled.

## Parameter highlights

Common fields from `SimulationParameters`:
- Population and horizon: `creator_count`, `investor_count`, `user_count`, `supporting_creator_fraction`, `min_creator_skill`, `max_creator_skill`, `max_steps`
- Behavior and usage: `creator_base_contribution_probability`, `quality_noise_scale`, `user_usage_probability`, `user_mean_usage_rate`, `base_gross_value`, `usage_shock_std`
- Graph and tracing: `gas_fee_share_rate`, `tracing_accuracy`, `tracing_false_positive_rate`, `default_derivative_split`, `supporting_derivative_split`, `core_research_base_royalty_share`, `funding_base_royalty_share`, `supporting_base_royalty_share`, `royalty_accrual_per_usage`, `royalty_batch_interval`
- Funding: `initial_investor_budget`, `funding_min_amount`, `funding_max_amount`, `funding_royalty_min`, `funding_royalty_max`, `funding_split_fraction`, `investor_max_funding_per_step`, `investor_min_target_quality`, `funding_lockup_period_steps`
- Satisfaction and churn: `initial_agent_satisfaction`, `aspiration_income_per_step`, `satisfaction_logistic_k`, `satisfaction_churn_threshold`, `satisfaction_churn_window`, `creator_roi_exit_threshold`, `investor_roi_exit_threshold`, `user_roi_exit_threshold`, `roi_churn_window`, `satisfaction_noise_std`, `creator_contribution_cost`, `disable_churn`
- Arrivals and identity: `creator_arrival_rate`, `investor_arrival_rate`, `user_arrival_rate`, ROI sensitivities per role, `identity_creation_cost`
- Reputation: `min_reputation_for_full_rewards`, `reputation_gain_per_usage`, `reputation_decay_per_step`, `reputation_penalty_for_churn`
- Treasury and payouts: `treasury_fee_rate`, `treasury_funding_rate`, `payout_lag_steps`
- Honor Seal: `honor_seal_enabled`, `honor_seal_initial_adoption_rate`, `honor_seal_mint_cost_btc`, `honor_seal_demand_multiplier`, `honor_seal_unsealed_penalty_multiplier`, `honor_seal_fake_rate`, `honor_seal_fake_detection_prob_per_step`, `honor_seal_enforcement_ramp_steps`, `honor_seal_dishonored_penalty_multiplier`

## Instrumentation

- Rewards: `model.reward_events` tracks per-payout entries with `step`, `payout_type`, `channel`, `amount`, `recipient_id`, `recipient_role`, `source_contribution_id`.
- Usage: `model.usage_events` captures `step`, `contribution_id`, `user_id`, and realized `gross_value` for every usage event.
- Tracing quality: `model.tracing_metrics` reports `true_links`, `detected_true_links`, `false_positive_links`, and `missed_true_links`.
- Graph export: `ContributionGraph.to_networkx()` returns a `networkx.DiGraph` with contribution ids as nodes and edges carrying royalty split attributes for visualization.
