# BITrewards ABM Design

This document describes the current BITrewards agent based model: entities, parameters, capital flows, churn logic, token supply, and reputation/identity rules. It is the single design contract for the model; if implementation diverges, update this document.

---

## 1. High level goals

1. Use the ABM to evaluate the protocol, not the model artifact

   - Capital should never vanish "by accident".
   - Churn and entry should respond to realized ROI and satisfaction, not a hard coded timer.
   - Major mechanisms in the whitepaper (funding NFTs, gas fee sharing, royalties) should have a faithful representation.

2. Make real platform failure modes possible to study

   Examples:

   - Investors churn because their ROI is negative
   - A cold start regime with low arrivals and low usage
   - A reflexive regime where token supply and expectations feed back into participation
   - Effects of lockups and payout delays on liquidity and churn

3. Keep the model explainable and testable

   - Every mechanism has explicit state and parameters.
   - There are invariants that can be unit tested (for example capital is conserved in a closed system).
   - Defaults keep behavior stable so experiments are comparable.

---

## 2. Domain model

The domain model lives in `src/bitrewards_abm/domain/entities.py`. It introduces three main ideas:

- Enriched `Contribution` objects that can carry funding, royalties, and verification metadata
- Global economic state via a treasury and a token economy
- Types for DAG edges so graph logic can distinguish funding, derivative, and supporting flows

### 2.1 Contribution types

Contribution types are:

```python
class ContributionType(str, Enum):
    CORE_RESEARCH = "core_research"
    FUNDING = "funding"
    SUPPORTING = "supporting"
```

Semantics:

- CORE_RESEARCH - research, code, datasets, or other primary work that can be used directly
- FUNDING - contributions that represent funding NFTs (non fungible tokens) or other investor positions
- SUPPORTING - documentation, evaluation, community work, or other supporting modules

The contribution graph is a DAG (directed acyclic graph) where nodes are contributions and edges describe derivations or funding links.

### 2.2 Contribution

The baseline Contribution carries minimal information:

- Identity and project
- Owner (agent id)
- Type
- Quality
- Parent ids

The model extends this with protocol aligned fields. All new fields have defaults so existing code can keep calling the dataclass constructor with the old signature.

```python
@dataclass
class Contribution:
    # Core identifiers
    contribution_id: str
    project_id: Optional[str]
    owner_id: int
    contribution_type: ContributionType
    quality: float

    # Graph structure - contribution ids of direct parents in the DAG
    parents: List[str] = field(default_factory=list)

    # Economic fields

    # Total primary funding raised into this contribution (tokens transferred
    # from investors to creators plus treasury).
    funding_raised: float = 0.0

    # Optional royalty percentage (for example 0.02 for a 2 percent funding NFT).
    # This is a property of FUNDING contributions that controls how much
    # downstream usage sends back to the investor that funded this node.
    royalty_percent: Optional[float] = None

    # Count of usage events that directly reference this contribution as the
    # "starting" node in the DAG. This is useful for performance gating and
    # simple popularity metrics.
    usage_count: int = 0

    # Remaining steps before this contribution's funding leg unlocks.
    # For FUNDING contributions this is the lockup frictions parameter.
    # When > 0, investors do not receive royalties yet.
    lockup_remaining_steps: int = 0

    # Whether this contribution has passed a performance or quality filter
    # (for example enough usage, review, or external verification) so that
    # it can earn full rewards. If False, rewards can be gated or slashed.
    is_performance_verified: bool = False

    # Optional string that tags the contribution more finely than type:
    # for example "software", "dataset", "discovery", "benchmark", etc.
    kind: Optional[str] = None
```

This structure is enough to support:

- Funding NFTs by setting contribution_type = FUNDING and royalty_percent on funding nodes
- Funding lockups via lockup_remaining_steps
- Basic performance gating via usage_count and is_performance_verified

### 2.3 Usage events

UsageEvent remains simple:

```python
@dataclass
class UsageEvent:
    contribution_id: str
    gross_value: float
    fee_amount: float
```

Later PRs will use gross_value and fee_amount as the base for:

- Gas fee sharing to contributors and treasury
- Stochastic usage shocks
- ROI computation for agents

If we need more detail (for example user id, scenario id) we can extend this dataclass in a follow up PR.

### 2.4 Edge types for the contribution graph

The graph implementation in `src/bitrewards_abm/infrastructure/graph_store.py` already stores split fractions on edges.

The graph distinguishes edge types (for example a derivative edge vs a funding edge). This type is defined for future policies even if not all branches use it yet.

```python
class EdgeType(str, Enum):
    DERIVATIVE = "derivative"
    FUNDING = "funding"
    SUPPORTING = "supporting"
    OTHER = "other"
```

Follow up PRs will:

- Add an edge_type metadata field to the graph edges
- Use EdgeType.FUNDING and ContributionType.FUNDING together to compute funding royalties

### 2.5 Treasury state

The treasury is a simple account that can:

- Receive fractions of funding flows and fees
- Pay subsidies or buybacks
- Report balance and flow metrics

```python
@dataclass
class TreasuryState:
    balance: float = 0.0
    cumulative_inflows: float = 0.0
    cumulative_outflows: float = 0.0
```

This state will be updated in PR2 when we fix capital flows and introduce the treasury as the sink for fee shares.

### 2.6 Token economy state

The model tracks token supply and holding times so analysts can study reflexive regimes. Token supply is tracked at a high level by TokenEconomyState:

```python
@dataclass
class TokenEconomyState:
    total_supply: float = 0.0
    circulating_supply: float = 0.0
    staked_supply: float = 0.0
    burned_supply: float = 0.0
    mean_holding_time_steps: float = 0.0
```

### 2.7 Capital flows and treasury invariants

All major capital movements are explicit and trackable.

**Funding**

- An investor pays `funding_contribution_cost` from their budget when creating a FUNDING contribution.
- The same amount is reallocated into:
  - Creator wealth: `(1 − treasury_funding_rate) * funding_contribution_cost`
  - Treasury balance: `treasury_funding_rate * funding_contribution_cost`
- The model tracks `total_funding_invested` as the sum of all funding principal deployed.
- Total capital in the system (sum of all agent wealth + budgets + treasury balance) is invariant to funding, so there is no capital sink.

**Usage fees**

- For each usage event with gross value `V`:
  - `total_fee = V * gas_fee_share_rate * base_share`
  - Treasury receives `treasury_fee_rate * total_fee`
  - Contributors receive the remaining `royalty_pool = total_fee − treasury_fee_rate * total_fee` via the DAG
- The model tracks:
  - `cumulative_fee_distributed` (total fees minted)
  - `cumulative_external_inflows` (sum of all minted fees)
- Total capital evolves as:

> total_wealth_t = initial_total_wealth + cumulative_external_inflows_t

in the absence of any additional minting or burning rules (which are added in a later PR).

These invariants allow us to run source–sink audits and ensure that future changes do not silently destroy or create capital outside explicit mechanisms.

---

## 3. Parameter model

The parameter surface remains a single dataclass in `src/bitrewards_abm/domain/parameters.py`:

```python
@dataclass
class SimulationParameters:
    ...
```

SimulationParameters covers:

- Core population and simulation length (already present)
- Economic flows and treasury
- ROI and satisfaction
- Arrivals and usage
- Capital frictions
- Token supply and holding
- Reputation, identity, and Sybil resistance
- Costs

### 3.1 Core parameters (summary)

These already exist and remain unchanged:

- Agent counts:
  - creator_count, investor_count, user_count
- Horizon:
  - max_steps
- Fee, tracing, and contribution behavior:
  - gas_fee_share_rate, tracing_accuracy
  - creator_base_contribution_probability, quality_noise_scale
  - user_usage_probability, base_gross_value
- Skill and aspiration distributions:
  - min_creator_skill, max_creator_skill
  - creator_min_aspiration_income, creator_max_aspiration_income
  - investor_min_aspiration_income, investor_max_aspiration_income
- Satisfaction and churn:
  - aspiration_income_per_step
  - satisfaction_logistic_k
  - satisfaction_churn_threshold
  - satisfaction_churn_window
- Reward and split parameters:
  - core_research_base_royalty_share
  - supporting_base_royalty_share
  - funding_base_royalty_share
  - default_derivative_split
  - supporting_derivative_split
  - funding_split_fraction
- Funding:
  - funding_contribution_cost

These parameters are documented in `docs/kosmos_brief.md`.

### 3.2 Additional parameters

#### 3.2.1 Economic flows and treasury

These parameters control where funding and fees go and support the treasury.

```python
# Fraction of usage fee that is routed to the treasury before royalties.
# 0.0 means all fee is shared among contributors.
treasury_fee_rate: float = 0.0

# Fraction of each funding contribution cost that is routed to the treasury.
# The remaining fraction goes to the creator being funded.
treasury_funding_rate: float = 0.0
```

#### 3.2.2 ROI and satisfaction

These parameters make satisfaction and churn depend on ROI over a sliding window rather than only on per step income.

Add:

```python
# ROI thresholds for churn by agent role.
# ROI is defined as cumulative_income / cumulative_cost - 1.0.
creator_roi_exit_threshold: float = -0.2
investor_roi_exit_threshold: float = -0.2
user_roi_exit_threshold: float = -0.2

# Number of consecutive low satisfaction steps required before churn,
# when using ROI aware churn logic.
roi_churn_window: int = 10

# Standard deviation of Gaussian noise added to satisfaction each step.
# 0.0 keeps deterministic satisfaction.
satisfaction_noise_std: float = 0.0
```

#### 3.2.3 Arrivals and usage

These parameters introduce Poisson arrivals and usage, and allow arrival rates to depend on ROI.

Add:

```python
# Baseline Poisson arrival rates per step for new agents.
# Defaults are 0 (closed population).
creator_arrival_rate: float = 0.0
investor_arrival_rate: float = 0.0
user_arrival_rate: float = 0.0

# Sensitivity of arrival rates to ROI by role.
# 0.0 means arrivals are independent of ROI.
creator_arrival_roi_sensitivity: float = 0.0
investor_arrival_roi_sensitivity: float = 0.0
user_arrival_roi_sensitivity: float = 0.0

# Mean number of usage events per user per step, for a Poisson model.
# user_usage_probability acts as a Bernoulli gate; user_mean_usage_rate is the Poisson lambda.
user_mean_usage_rate: float = 1.0

# Log normal shock on gross_value for usage events.
# Applied as gross_value *= exp(N(0, usage_shock_std)).
usage_shock_std: float = 0.0
```

#### 3.2.4 Capital frictions

Capital frictions govern lockups on funding positions and payout delays for royalties.

Add:

```python
# Lockup period applied to new funding contributions, in steps.
# While locked, the investor does not receive royalties.
funding_lockup_period_steps: int = 0

# Payout lag in steps for fee and royalty payments.
# 0 means pay out in the same step.
payout_lag_steps: int = 0
```

Usage:

- PR4 will implement lockups using Contribution.lockup_remaining_steps.
- PR4 will implement payout lags via a pending payouts buffer.

#### 3.2.5 Token supply and holding times

These parameters define how much token supply exists and how it evolves.

Add:

```python
# If nonzero, overrides deriving the initial token supply from agent wealth.
token_initial_supply: float = 0.0

# Simple per step inflation rate as a fraction of total_supply.
# For example 0.01 means 1 percent inflation per step.
token_inflation_rate: float = 0.0

# Fraction of treasury balance that is burned per step via buybacks.
# 0.0 means no burn.
token_buyback_burn_rate: float = 0.0
```

Usage:

- PR5 will initialize TokenEconomyState using either token_initial_supply or the sum of initial wealth.
- PR5 will apply token_inflation_rate each step and route minted tokens into the treasury.
- PR5 will apply token_buyback_burn_rate to reduce supply.

#### 3.2.6 Reputation, identity, and Sybil resistance

These parameters control a simple reputation model and the cost of creating new identities.

Sybil resistance means making it expensive or unprofitable to spin up many fake accounts to farm rewards.

Add:

```python
# Minimum reputation required to receive full rewards.
# If an agent's reputation_score is below this value, their rewards
# are linearly downscaled and the remainder is routed to the treasury.
min_reputation_for_full_rewards: float = 0.0

# One time cost charged when a new agent identity is created.
# Typically paid into the treasury.
identity_creation_cost: float = 0.0

# How much reputation increases when an agent's contribution
# successfully earns usage based rewards.
reputation_gain_per_usage: float = 0.0

# Reputation penalty applied when an agent churns early or behaves badly.
reputation_penalty_for_churn: float = 0.0

# Passive decay of reputation per step.
# 0.0 means reputation is sticky.
reputation_decay_per_step: float = 0.0
```

Usage:

- PR6 will implement a simple reputation update rule.
- PR6 will apply min_reputation_for_full_rewards when paying out royalties.
- PR6 will charge identity_creation_cost when spawning new agents.

#### 3.2.7 Costs

These parameters capture costs that should be included in ROI calculations.

Add:

```python
# Effort cost for a creator to produce a new contribution.
# Charged as a cost in ROI accounting.
creator_contribution_cost: float = 0.0
```

### 3.3 ROI-based satisfaction and churn

Summary:

- Each economic agent (creator, investor, user) maintains:
  - cumulative_income
  - cumulative_cost
  - current_roi = cumulative_income / (cumulative_cost + epsilon) - 1.0

- Creators and investors:
  - Satisfaction is driven by ROI, transformed to a non-negative signal:
    - signal = max(0, 1 + ROI)
    - satisfaction = 1 / (1 + exp(-k * (signal - 1)))
  - Satisfaction may include a small Gaussian noise term (satisfaction_noise_std).
  - low_satisfaction_streak counts consecutive steps where satisfaction is below satisfaction_churn_threshold.
  - Churn occurs when:
    - ROI < <role>_roi_exit_threshold, and
    - low_satisfaction_streak >= roi_churn_window.

- Users:
  - Satisfaction remains a function of per-step income relative to aspiration.
  - Churn is based on low-satisfaction streak and satisfaction_churn_window.
  - Optional noise prevents perfectly synchronized churn.

This makes collapse for creators and investors an emergent property of ROI paths rather than a direct function of a fixed satisfaction window.

### 3.4 Stochastic arrivals, usage, and capital frictions (PR 4)

**Arrivals**

- Each step, for each role (creator, investor, user), the model computes an effective Poisson rate:
  - Base rate: `creator_arrival_rate`, `investor_arrival_rate`, `user_arrival_rate`
  - Mean ROI per role: average `current_roi` over active agents of that role
  - Sensitivity: `<role>_arrival_roi_sensitivity`
- The effective rate is:

> λ_effective = base_rate × max(0, 1 + sensitivity × mean_roi)

- New agents per role are drawn as `Poisson(λ_effective)`.
- The model logs:
  - `new_creators_this_step`
  - `new_investors_this_step`
  - `new_users_this_step`

**Usage and shocks**

- Users have a two-stage decision each step:
  1. Become active with probability `user_usage_probability`.
  2. If active, draw `num_events ~ Poisson(user_mean_usage_rate)`.
- For each event, the user selects a random contribution and passes `base_gross_value` to `register_usage_event`.
- `register_usage_event` applies a log-normal shock when `usage_shock_std > 0`:

> gross_value_effective = base_gross_value × exp(N(0, usage_shock_std))

- Fees are computed from `gross_value_effective` via `gas_fee_share_rate` and the base role share.

**Capital frictions**

- Funding lockup
  - New FUNDING contributions are created with `lockup_remaining_steps = funding_lockup_period_steps`.
  - During DAG fee distribution:
    - If a FUNDING node has `lockup_remaining_steps > 0`, its own fee share is not paid to the investor.
    - This locked share is routed to the treasury.
  - Each step, `lockup_remaining_steps` is decremented by 1 until reaching 0.
  - The model logs the current number of locked funding positions as `locked_funding_positions`.
- Payout lag
  - Contributions’ fee shares are first placed into a pending payouts buffer keyed by contribution id.
  - If `payout_lag_steps == 0`, payouts are applied immediately.
  - If `payout_lag_steps > 0`, the buffer is only flushed every `payout_lag_steps` steps:
    - On flush, each `(contribution_id, amount)` is paid via `pay_contribution_owner`.
    - ROI accounting and reward metrics update at flush time, not at event time.

### 3.5 Token supply and holding times

The model adds an explicit token layer on top of real-economy capital.

**State**

- `TokenEconomyState`:
  - `total_supply`: total issued tokens
  - `circulating_supply`: tokens held by agents or the treasury
  - `staked_supply`: reserved for future staking mechanics (0 currently)
  - `burned_supply`: cumulative burned tokens
  - `mean_holding_time_steps`: approximate mean holding time across agents

**Initialization**

- Let `W0` be `initial_total_wealth` (sum of agent wealth, budgets, and treasury at t=0).
- If `token_initial_supply > 0`, then:

> total_supply_0 = token_initial_supply

- Otherwise:

> total_supply_0 = W0

- `circulating_supply_0` is set equal to `total_supply_0`.

**Fee minting**

For each usage event with gross value `V`:

- The model computes

> total_fee = V × gas_fee_share_rate × base_share

- `total_fee` is treated as newly minted capital and tokens:
  - `cumulative_external_inflows` increases by `total_fee`
  - `token_total_supply` and `token_circulating_supply` increase by `total_fee`
  - `treasury_fee_rate × total_fee` goes to the treasury; the remainder is allocated via the DAG as royalties

**Inflation and burn**

At the start of each step t:

- Inflation:

> minted_t = token_inflation_rate × total_supply_{t-1}

  - `total_supply_t = total_supply_{t-1} + minted_t`
  - `circulating_supply_t = circulating_supply_{t-1} + minted_t`
  - Minted tokens are credited to the treasury and counted as external inflows.

- Buyback and burn:

> burn_t = token_buyback_burn_rate × treasury_balance_t

  - `treasury_balance_t` decreases by `burn_t`
  - `total_supply_t` decreases by `burn_t`
  - `circulating_supply_t` decreases by `burn_t` (clamped at zero)
  - `burned_supply` increases by `burn_t`

With `token_inflation_rate = 0` and `token_buyback_burn_rate = 0`, token supply is only affected by fees.

**Holding times**

Each `EconomicAgent` tracks:

- `holding_time_ema`: an exponential moving average of time between balance changes
- `last_holding_update_step`: last step when holding_time_ema was updated
- `had_balance_change_this_step`: set to `True` whenever `record_income` or `record_cost` is called

At the end of each step:

- For each agent with `had_balance_change_this_step`:

> delta = current_step - last_holding_update_step  
> holding_time_ema = (1 - alpha) × holding_time_ema + alpha × delta

- `TokenEconomyState.mean_holding_time_steps` is the simple mean of `holding_time_ema` over agents with positive wealth.

This provides a low-cost summary of token velocity without modeling every individual transfer.

### 3.6 DAG royalty engine and reputation-gated rewards

**DAG royalty engine**

- The contribution graph stores parent -> child edges with a `split` fraction meaning "fraction of the child's pool that routes to this parent".
- For a usage event at contribution `S` with royalty pool `F`, `compute_royalty_shares(S, F)`:
  - Starts at `(S, F)`
  - At each node with pool `P`, allocates `P * split` to each parent, keeps the remainder as the node's own share, and propagates to parents
  - Terminates at roots and returns a mapping of contribution id to share where the shares sum to `F`

**Performance and reputation gating**

- Each economic agent tracks `reputation_score ∈ [0, 1]`.
- When a contribution owned by agent `a` is owed amount `A`:
  - If `min_reputation_for_full_rewards <= 0`, `a` receives `A`.
  - Otherwise, `a` receives `A * max(0, reputation_score / min_reputation_for_full_rewards)` and the remainder is routed to the treasury.
- After a nonzero payout, `reputation_score` increases by `reputation_gain_per_usage` (clipped to 1.0).
- Each step, reputation decays by `reputation_decay_per_step`. When an agent churns, `reputation_score` is reduced by `reputation_penalty_for_churn`.

**Identity cost (Sybil friction)**

- When new agents are spawned, if `identity_creation_cost > 0` the agent is charged that amount as an upfront cost (added to cumulative_cost and removed from wealth), and the same amount is credited to the treasury. Total wealth stays constant while new identities start in debt.

---
