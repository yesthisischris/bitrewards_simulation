# Story Pack Additions for the BITrewards ABM

Use this checklist to expand the story pack with visuals. They can start as stylized diagrams and later be wired to real outputs.

## Section 1: Big picture

**Visual 1 – ABM system map**
- Diagram showing creators, investors, users feeding usage into the contribution DAG inside “BITrewards protocol”.
- Treasury box with fee cut, slashed rewards, and identity cost inflows; token supply bubble (total, circulating, burned) with inflation/burn arrows.
- Callouts: capital conserving flows, ROI-based churn, stochastic arrivals/lockups/payout lags, token supply + holding times. Note contrast with the legacy model that lacked a treasury and deleted funding principal.

## Section 2: Capital flows and invariants

**Visual 2 – Funding flows: legacy vs current**
- Side-by-side arrows or Sankey: legacy investor 100 → capital sink; creator stays at 0. Current: 75 to creator, 25 to treasury (funding_contribution_cost=100, treasury_funding_rate=0.25). Total capital conserved.

**Visual 3 – Total wealth invariant**
- Line chart of total wealth (flat until fees/inflation), cumulative fees minted, and total wealth minus cumulative fees (flat baseline). Note legacy wealth destruction vs current invariant.

## Section 3: Behavior and ROI

**Visual 4 – Churn timing: deterministic vs ROI-driven**
- Panel A (legacy): active agents drop in lockstep at churn window multiples. Panel B (current): staggered drops driven by ROI and noise; investors can churn before creators/users if ROI diverges.

**Visual 5 – ROI → satisfaction → churn pipeline**
- Flow: events (funding principal, royalties) → per-agent accounting (cumulative_income, cumulative_cost, current_roi) → satisfaction = logistic(1+ROI)+noise → churn test (ROI threshold + low_satisfaction_streak for creators/investors; satisfaction streak for users).

## Section 4: Dynamics, arrivals, frictions

**Visual 6 – Stochastic arrivals and usage**
- Top: agent counts over time with ROI-modulated Poisson arrivals. Bottom: usage events per step bars with expected value line (#users × usage_probability × mean_usage_rate).

**Visual 7 – Lockups and payout lags timeline**
- Timeline showing funding principal split at step 0, lockup_remaining_steps blocking funding royalties (routed to treasury) until expiry; payout_lag_steps batching royalties every N steps.

## Section 5: Tokenomics

**Visual 8 – Token supply decomposition**
- Stacked area of circulating + burned with total supply line. Mark fee mints (supply up), inflation adds, burn reduces supply from treasury-funded buybacks.

**Visual 9 – Token holding times**
- Option A: bar chart of fast/medium/long holders by holding_time_ema. Option B: mean_token_holding_time_steps line showing velocity shifts (drops = high turnover, rises = stickier holdings).

## Section 6: DAG royalties, reputation, Sybil friction

**Visual 10 – DAG royalty example**
- Nodes: discovery-01 → code-01 (0.5), funding-01 → code-01 (0.5), code-01 → derivative-01 (0.5). For pool=1000: derivative own 500; discovery 250; funding 250; code own 0. Show edge math.

**Visual 11 – Reputation gating**
- Two panels: rep=1.0 agent keeps full 100; rep=0.5 with min_rep=1.0 keeps 50 and 50 is slashed to treasury. Formula: paid = amount × min(1, rep/threshold); slashed = amount − paid. Note reputation gain on payouts, decay per step, penalty on churn.

**Visual 12 – Identity cost (Sybil friction)**
- Single agent pays identity cost C, starts at wealth W−C; Sybil swarm of 10 pays 10×C to treasury, showing negative/low ROI bars. Identity cost is charged via record_cost; total wealth unchanged but new identities start in debt.
