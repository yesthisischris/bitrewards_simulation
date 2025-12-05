# Kosmos Brief: BITrewards Simulation

This document is a focused handoff for Kosmos (AI scientist). It describes:

- The goal of the BITrewards simulation project
- The agent based model (ABM) used in code
- The data artifacts (CSV files, configs, scenarios)
- Concrete questions to investigate
- Pointer to the full design spec: `docs/abm_design.md`

ABM stands for agent based model. CSV stands for comma separated values. ROI stands for return on investment. DAG stands for directed acyclic graph. Gini stands for Gini coefficient, a standard inequality measure from 0 (equal) to 1 (very unequal).

---

## 1. Project Objective

High level question:

> Under what parameter regimes does the BITrewards protocol yield sustainable, fair reward distributions across roles and contribution types, and where are the “phase transitions” where the ecosystem collapses or becomes skewed?

More concrete objectives:

- Characterize **sustainability**: do we get a healthy number of active contributors, investors, and users over time, or do creators churn out quickly.
- Characterize **fairness**:
  - How total income is split between creators, investors, and users/supporters.
  - How inequality is distributed within each role (for example Gini for creator wealth).
- Characterize **robustness**:
  - Effects of gas fee sharing rate, funding split, and tracing accuracy on outcomes.
  - Conditions where investors get decent ROI without collapsing creator participation.

BITrewards should roughly align with the whitepaper V4 story:

- Gas fee sharing from usage events enters a royalty pool.
- Contributions are tokenized and connected in a DAG representing derivations.
- AI tracing accuracy determines how well the DAG captures ancestry.
- Royalties propagate along the DAG according to type specific split rules (path multiplicative splits with the remaining share kept locally).
- Funding NFTs give investors a small, persistent share on funded modules.
- Funding principal is reallocated (creator + treasury), not destroyed.
- Treasury receives a configurable cut of fees plus slashed rewards and identity costs.
- Token supply and holding times are tracked (fees mint supply; optional inflation/burn).
- Rewards are reputation-gated; identity creation can have an upfront cost to deter Sybil swarms.
- Churn for creators/investors is ROI-driven with noise; users use a simpler income ratio with noise.

---

## 2. Model Overview

### 2.1 Agents and roles

The simulation has three explicit agent classes:

1. **CreatorAgent**
   - Represents initiators and contributors from the whitepaper.
   - Makes contributions (for example software modules, scientific results, datasets).
   - Has attributes:
     - `wealth`: cumulative income from royalties.
     - `skill`: controls expected quality of work.
     - `satisfaction`: updated each step from realized income vs aspiration.
     - `is_active`: becomes `False` when the agent churns.
   - Decision rule:
     - With probability `creator_base_contribution_probability` per step, attempts to create a new contribution.
     - The new contribution targets an existing contribution as parent with some probability, creating edges in the DAG.

2. **InvestorAgent**
   - Represents financial investors who buy “funding NFTs”.
   - Attributes:
     - `budget`: capital remaining to invest.
     - `total_invested`: cumulative invested amount.
     - `funding_contribution_identifiers`: identifiers of funding contributions they own.
   - Decision rule:
     - Up to `investor_max_funding_per_step` times per step, picks a target contribution to fund if:
       - Budget is above `funding_contribution_cost`.
       - Target quality exceeds `investor_min_target_quality`.
     - Creates a `funding` contribution that attaches to the target and receives a small royalty share of its downstream usage.

3. **UserAgent**
   - Represents end users and community.
   - Decision rule:
     - With probability `user_usage_probability` per step, triggers a usage event on a randomly chosen contribution.
     - Each usage event generates a gross value (proxy for revenue) and a protocol fee.

Mapping to whitepaper roles:

- **Initiators** + **Contributors** → Creator agents.
- **Investors** → Investor agents.
- **Users/Community** → User agents.

### 2.2 Contribution graph and types

Each contribution is represented as:

- `Contribution(contribution_id, project_id, owner_id, contribution_type, quality, parents)`

Contribution types group the whitepaper taxonomy into a compact set:

- `core_research`
  - Software code, scientific discoveries, datasets, hardware designs.
- `funding`
  - Financial investments, funding NFTs that purchase a small share on a target module.
- `supporting`
  - Reviews, educational materials, curation, moderation, events.

The contributions form a DAG:

- Nodes: contribution identifiers.
- Edges: parent to child, with edge attribute `split_fraction` representing the royalty fraction passed upstream when the child earns.

The DAG is stored in `ContributionGraph`, a NetworkX wrapper. Tracing accuracy determines whether “intended” edges are actually included:

- With probability `tracing_accuracy`, an intended parent link is recorded.
- With probability `1 - tracing_accuracy`, the edge is missing and the reward path is truncated.

### 2.3 Usage events, fees, and propagation

Each usage event is:

- `UsageEvent(contribution_id, gross_value, fee_amount)`

Usage behavior:

- Each active user is gated by `user_usage_probability`. If active, draws `num_events ~ Poisson(user_mean_usage_rate)`.
- Each usage event draws a contribution, computes `gross_value_effective = base_gross_value * exp(N(0, usage_shock_std))`, and mints a fee:
  - `fee_amount = gross_value_effective * gas_fee_share_rate * base_royalty_share(type)`

Reward propagation logic:

1. Start with the chosen contribution and the fee pool reserved for contributors (after treasury cut).
2. Use the graph’s `compute_royalty_shares(start_id, pool)` to route value upstream:
   - At each node: allocate `pool * split` to parents based on edge splits; remaining amount is the node’s own share.
3. Apply frictions:
   - Funding lockups: funding nodes with `lockup_remaining_steps > 0` route their share to the treasury until unlocked.
   - Payout lag: payouts can be buffered and flushed every `payout_lag_steps`.
4. Treasury also receives its configured fee cut and any slashed rewards (from low reputation or unverified contributions).

Funding behavior:

- Funding contributions attach to a target module with an edge from funding to target.
- The edge carries `funding_split_fraction` (for example 2 percent).
- Funding principal is split between creator and treasury (`treasury_funding_rate`), conserving total capital.
- When the target receives royalties, a fixed fraction flows to the funder via this edge (subject to lockup, payout lag, and reputation gating).

### 2.4 Satisfaction, ROI, and churn

- Creators and investors track `cumulative_income`, `cumulative_cost`, and `current_roi = income / (cost + epsilon) - 1`.
- Satisfaction is logistic on `1 + ROI` with optional Gaussian noise (`satisfaction_noise_std`).
- Churn:
  - Creators/investors churn when `ROI < role_threshold` AND `low_satisfaction_streak >= roi_churn_window`.
  - Users use a simpler income ratio satisfaction with noise; churn is based on low satisfaction streak and `satisfaction_churn_window`.
- Reputation and identity:
  - Rewards are reputation-gated: `paid = amount * max(0, reputation / min_reputation_for_full_rewards)`, remainder to treasury.
  - Reputation increases on payouts, decays per step, and drops on churn (`reputation_gain_per_usage`, `reputation_decay_per_step`, `reputation_penalty_for_churn`).
  - Optional identity cost (`identity_creation_cost`) is charged via `record_cost` when new agents spawn; the same amount is credited to the treasury.

---

## 3. Data Overview

Data is written as CSV files by the batch harness.

### 3.1 Files

For each scenario you run, the harness writes:

- `data/<scenario_name>/timeseries.csv`
  - One row per step per run.
- `data/<scenario_name>/run_summary.csv`
  - One row per run (final step metrics plus run averages).

There is also a shared `configs/` directory that holds scenario definitions in TOML format.

### 3.2 Indexing

Every row in both CSV files is indexed by:

- `run_id`: integer identifier for a single run of the model.
- `rep`: repetition index (if there are repeated runs for the same parameter combination).
- `scenario_name` or `scenario`: a short string label such as `baseline`, `low_tracing`, `high_funding_share`, `high_investor_share`.

`timeseries.csv` also has:

- `step`: 1 based time step for the ABM.

### 3.3 Key metrics

Metrics are designed to capture sustainability, fairness, and type behavior.

Per step metrics (in `timeseries.csv`):

- Activity and population:
  - `contribution_count` – total contributions in DAG.
  - `usage_event_count` – usage events this step.
  - `active_creator_count`, `active_investor_count`, `active_user_count`.
- Fees:
  - `total_fee_distributed` – protocol fees distributed this step.
  - `cumulative_fee_distributed` – sum of fees distributed up to this step.
- Inequality and ROI:
  - `creator_wealth_gini` – Gini for creator wealth.
  - `investor_mean_roi` – mean investor ROI.
- Satisfaction and churn:
  - `mean_creator_satisfaction`, `mean_investor_satisfaction`, `mean_user_satisfaction`.
  - `creator_churned_count`, `investor_churned_count`, `user_churned_count`.
- Type level:
  - `core_research_contribution_count`, `funding_contribution_count`, `supporting_contribution_count`.
  - `total_reward_core_research`, `total_reward_funding`, `total_reward_supporting`.
- Role level:
  - `total_income_creators`, `total_income_investors`, `total_income_users`.
  - `role_income_share_creators`, `role_income_share_investors`, `role_income_share_users`.

Per run metrics (in `run_summary.csv`):

- Final step values for all metrics above.
- Run level averages:
  - `mean_creator_satisfaction_over_run`.
  - `mean_investor_satisfaction_over_run`.
  - `mean_user_satisfaction_over_run`.
- Parameter columns (constant within each run):
  - Examples: `gas_fee_share_rate`, `funding_split_fraction`, `tracing_accuracy`,
    `default_derivative_split`, `supporting_derivative_split`, `aspiration_income_per_step`,
    `satisfaction_logistic_k`, `satisfaction_churn_threshold`, `satisfaction_churn_window`.

The full schema is documented in `docs/data_schema.md`.

---

## 4. Scenarios and Reference Datasets

We provide four named scenarios.

Each scenario has:

- A config file under `configs/`.
- A reference dataset under `data/reference/<scenario_name>/` with:
  - `run_summary.csv`.
  - `timeseries.csv`.

Scenarios:

1. **Baseline**
   - Name: `baseline`.
   - Intention:
     - “Reasonable” behavior, non trivial churn, mixed outcomes.
   - Parameters (illustrative):
     - `gas_fee_share_rate ≈ 0.005`.
     - `funding_split_fraction ≈ 0.02`.
     - `tracing_accuracy ≈ 0.8`.
     - `default_derivative_split ≈ 0.5`.
     - Satisfaction parameters tuned so that:
       - Some creators churn.
       - Many remain active for most of the run.

2. **LowTracing**
   - Name: `low_tracing_accuracy`.
   - Intention:
     - Explore effect of poor AI tracing quality.
   - Parameters:
     - Same as baseline except:
       - `tracing_accuracy` much lower (for example 0.3 to 0.4).
   - Hypothesis:
     - Rewards become more “local”.
     - Investors and upstream contributors see lower ROI and income.

3. **HighFundingShare**
   - Name: `high_funding_share`.
   - Intention:
     - Test an aggressive investor share regime.
   - Parameters:
     - Similar to baseline but with:
       - `funding_split_fraction` increased (for example 0.05).
   - Hypothesis:
     - Investor ROI improves.
     - Creator income share and satisfaction may decrease.
     - Creator churn may rise if aspiration is not adjusted.

4. **HighInvestorShare**
   - Name: `high_investor_share`.
   - Intention:
     - Combine higher funding splits with higher gas fee share.
   - Parameters:
     - `gas_fee_share_rate` higher (for example 0.008 to 0.01).
     - `funding_split_fraction` moderately high.
   - Hypothesis:
     - Everyone earns more, but investors capture a disproportionate share.
     - Must check whether creators still have acceptable satisfaction and churn.

Reference dataset generation (example):

```bash
# Baseline
poetry run python experiments/run_batch.py \
  --config configs/baseline.toml \
  --out-dir data/reference/baseline

# Low tracing
poetry run python experiments/run_batch.py \
  --config configs/low_tracing_accuracy.toml \
  --out-dir data/reference/low_tracing_accuracy

# High funding share
poetry run python experiments/run_batch.py \
  --config configs/high_funding_share.toml \
  --out-dir data/reference/high_funding_share

# High investor share
poetry run python experiments/run_batch.py \
  --config configs/high_investor_share.toml \
  --out-dir data/reference/high_investor_share
```

These paths and scenario names appear in tests and visuals.

---

## 5. What We Want Kosmos To Investigate

Examples of analysis tasks for Kosmos:

1. Sustainability under varying investor share
   - For each scenario, estimate:
     - Fraction of creators still active at final step.
     - Mean creator satisfaction over run.
     - Creator churn trajectory over time.
   - Identify parameter regimes where:
     - Investors achieve a target ROI (for example above 5 or 10 percent).
     - Creator churn remains below a target level.
2. Fairness across roles
   - Compute role reward shares:
     - `role_income_share_creators`, `role_income_share_investors`, `role_income_share_users`.
   - Analyze tradeoffs:
     - Regions where creators capture roughly half of total income.
     - Regions where investors dominate.
   - Report how these shares depend on:
     - `gas_fee_share_rate`.
     - `funding_split_fraction`.
     - `tracing_accuracy`.
3. Inequality inside the creator role
   - Use `creator_wealth_gini` to understand inequality among creators:
     - Are there “winner takes most” regimes.
     - How does inequality correlate with overall creator share of income.
   - Map how `creator_wealth_gini` changes across scenarios and parameter sweeps.
4. Tracing accuracy and robustness
   - Quantify how lower `tracing_accuracy` affects:
     - Total fee distributed.
     - Total income to upstream contributors.
     - Investor ROI.
   - Identify whether there is a critical range of `tracing_accuracy` below which the protocol fails to reward deep ancestry.
5. Phase transitions
   - Look for parameter boundaries where:
     - Creator churn increases sharply.
     - Investor ROI collapses.
     - Role income shares shift dramatically.
   - Characterize these “phase transitions” as a function of:
     - `gas_fee_share_rate`.
     - `funding_split_fraction`.
     - `tracing_accuracy`.
6. Calibration suggestions
   - Propose improved baseline parameter sets that:
     - Avoid trivial collapse (everyone churns quickly).
     - Avoid trivial explosion (everyone is happy and rich, no meaningful churn).
     - Keep creator and investor outcomes within reasonable ranges.

---

## 6. How To Use This Package

High level workflow for Kosmos:

1. Study the schema using `docs/data_schema.md`.
2. Inspect configs under `configs/` for the four scenarios.
3. Load reference datasets under `data/reference/<scenario_name>/`.
4. Run additional batches via the CLI if needed.
5. Use metrics in `run_summary.csv` and `timeseries.csv` to analyze:
   - Sustainability (active counts, churn).
   - Fairness (role shares, Gini).
   - Investor outcomes (ROI).
6. Summarize findings:
   - Give recommended parameter ranges and scenario rankings.
   - Flag unstable regimes and phase transitions.

Kosmos does not need to understand Python internals in detail, but the model and data are documented enough to support deep analysis and parameter search.
