# BITrewards Simulation

Mesa ABM of the BITrewards protocol focused on economic and behavioral dynamics (contributors, investors, users) rather than blockchain internals.

- Understand sustainability, fairness, and investor ROI across parameter regimes
- Generate reproducible datasets for downstream analysis
- Compare reference scenarios and stress-test protocol assumptions

## Documentation

Start with `docs/README.md` for navigation by role.

- Model details and parameters: `docs/model.md`
- Running, configs, data schema, scenarios, analysis: `docs/usage.md`

## Quick run

```bash
poetry install
poetry run python -m bitrewards_abm.run_simulation --config configs/baseline.toml --steps 100 --seed 42
```

Batch example:

```bash
poetry run python experiments/run_batch.py --config configs/baseline.toml --out-dir data/baseline
```

Outputs are `timeseries.csv` and `run_summary.csv` under the chosen `--out-dir`.

## Reference scenarios

- Baseline, low tracing accuracy, high funding share, high investor share configs live in `configs/`
- Expected behaviors and reference data locations are summarized in `docs/usage.md`

	3.	Create new contribution object
	•	Set quality:

quality = max(0, min(1, base_quality_mean + skill_quality_weight * skill + noise))


	•	Set base_royalty_percent:
	•	If type is “funding”: skip, since creators do not create funding.
	•	If type is in whitepaper list, use standard percent (can be parameters):
Examples from the whitepaper:  ￼
	•	review: 10 percent
	•	curation: 5 percent
	•	annotation: 3 percent
	•	bugfix: 5 percent
	•	introduction: 2 percent
	•	moderation: 2 percent
	•	event_organization: 3 percent
	•	recommendation: 3 percent
	•	test_case: 5 percent
	•	Add Contribution to model’s contribution dictionary.

	4.	Update contribution graph
For each parent in parents:
	•	With probability tracing_accuracy (global parameter), create an edge parent -> child in graph.
	•	Set split attribute according to:

if child.type == "funding":
    split = investor_royalty_percent   # 0.01–0.03
elif child.type in special_types:
    split = type_to_default_split[child.type]
else:
    split = default_derivative_split   # for example 0.5


This defines how value will flow upstream later.

⸻

3.3 InvestorAgent

Represents investors who create “funding” NFTs.

Attributes
	•	budget: float
	•	min_expected_roi: float
Required ROI threshold.
	•	risk_tolerance: float (0–1)
	•	fundings_owned: set[int]

Decision loop per step
	1.	If budget <= 0 or not active, skip.
	2.	Build a candidate list of contributions or projects to fund:
	•	For now: target only initiator contributions of type “software_code” or “bio_discovery” or other “core” types.
	3.	For each candidate, estimate expected ROI:
	•	Use recent average revenue per step for that project.
	•	Combine with base_royalty_percent for “funding” contributions (global range 1–3 percent).

estimated_roi = (expected_project_revenue * investor_royalty_percent) / funding_cost


	4.	Select candidates where estimated ROI exceeds min_expected_roi, sorted by expected ROI.
	5.	For each candidate in order:
	•	If budget >= funding_cost, create a new “funding” contribution:
	•	type = "funding"
	•	owner_agent_id = investor_id
	•	base_royalty_percent sampled within [investor_royalty_min, investor_royalty_max]
	•	parent is the target contribution.
	•	Add edge funding_contribution_id -> target_contribution_id with split = base_royalty_percent.
	•	Decrease budget by funding_cost.

Funding cost and default ranges are parameters.

⸻

3.4 UserAgent

Represents end users who drive usage and revenue.

Attributes
	•	preference_vector over domains or features (for example more interested in “software”, “bio”, etc.)
	•	price_sensitivity: float
	•	quality_sensitivity: float

Decision loop per step

Each step:
	1.	Choose a project to interact with:
	•	Probability proportional to:
	•	project demand score:

demand_score = intrinsic_demand * (1 + demand_reputation_weight * reputation)


	•	alignment with user preferences.

	2.	Given chosen project, choose one terminal contribution to use:
	•	Typically a “feature” or main module (initiator code or a stable derivative).
	3.	Generate usage event:
	•	Each event has:
	•	gross_value (for example fixed or drawn from distribution).
	•	fee_rate (global parameter, 0.1–1 percent).
	•	So fee_amount = gross_value * fee_rate.
	4.	Append usage event to a per-step list in the model:
	•	(contribution_id, gross_value, fee_amount).

The question of how many usage events per user per step is a parameter (for example Poisson with mean λ).

⸻

4. Protocol logic and reward distribution

This is the core economics.

4.1 Gas fee sharing and royalty pool

For each usage event (contribution C is used):
	1.	Gas fee pool:

fee_amount = gross_value * gas_fee_share_rate

gas_fee_share_rate is a parameter in [0.001, 0.01] corresponding to 0.1–1 percent.

	2.	Define a reward pool R = fee_amount. This is the quantity distributed along the contribution graph for this event.

4.2 Value flow along the contribution graph

We use the contribution DAG to distribute R backwards from the terminal node to its ancestors.

Definitions
	•	Graph: G = model.graph, edges parent -> child with edge attribute split in [0,1].
	•	For a given terminal contribution t with value R:
	•	We consider all ancestors reachable from t in the reversed graph.

Algorithm (pseudocode)

Implementation suggestion:

def distribute_reward(model, terminal_contribution_id, reward_pool):
    G = model.graph
    RG = G.reverse(copy=False)

    # Compute path-based shares for ancestors
    ancestor_shares = defaultdict(float)

    # Option 1: simple tree assumption, use shortest path
    for ancestor in nx.ancestors(RG, terminal_contribution_id):
        try:
            path = nx.shortest_path(RG, terminal_contribution_id, ancestor)
        except nx.NetworkXNoPath:
            continue

        share = reward_pool
        for i in range(len(path) - 1):
            parent = path[i+1]
            child = path[i]
            edge_data = G[parent][child]
            share *= edge_data["split"]   # multiplicative split

        ancestor_shares[ancestor] += share

    total_ancestor_share = sum(ancestor_shares.values())
    terminal_share = max(0.0, reward_pool - total_ancestor_share)

    # Pay terminal owner
    pay_contribution_owner(model, terminal_contribution_id, terminal_share)

    # Pay ancestors
    for cid, share in ancestor_shares.items():
        pay_contribution_owner(model, cid, share)

Notes:
	•	This algorithm assumes at most one dominant upstream path between terminal and each ancestor (shortest path). That keeps complexity lower.
	•	For contributions where type-specific percentages are defined (for example review, funding):
	•	Make sure the corresponding edges’ split values reflect those percentages.

Mapping types to splits

Proposed parameter map (all configurable):

type_to_default_split = {
    "funding": investor_royalty_percent,        # between 0.01 and 0.03
    "review": 0.10,
    "curation": 0.05,
    "annotation": 0.03,
    "bugfix": 0.05,
    "test_case": 0.05,
    "introduction": 0.02,
    "moderation": 0.02,
    "event_organization": 0.03,
    "recommendation": 0.03,
}
default_derivative_split = 0.50  # all other contributions

These defaults should be parameterized so that sweeps can adjust them.

AI tracing accuracy

We approximate AI tracing accuracy with a single parameter tracing_accuracy in [0,1]:
	•	When creating an edge parent -> child:
	•	Include it with probability tracing_accuracy.
	•	If no parents survive for a contribution, it behaves as an independent initiator for reward distribution.

This lets us study the effect of imperfect AI tracing on fairness and incentives.

⸻

5. Model scheduling and step order

We use RandomActivation scheduler from Mesa, but we will control step order manually in the model.

Each model step (one time tick) proceeds in this fixed sequence:
	1.	creator_phase:
	•	All active CreatorAgent instances act (in random order):
	•	Decide whether to contribute.
	•	Possibly create new contributions and update graph.
	2.	investor_phase:
	•	All active InvestorAgent instances act (in random order):
	•	Decide where to invest.
	•	Possibly create new funding contributions and edges.
	3.	user_phase:
	•	All active UserAgent instances act (in random order):
	•	Generate zero or more usage events and append to model usage_events list.
	4.	reward_phase:
	•	For each usage event (contribution_id, gross_value, fee_amount):
	•	Call distribute_reward.
	•	Reset agents’ current_income to 0 at start of next step.
	5.	update_phase:
	•	Each agent updates:
	•	wealth and current_income already updated in reward phase.
	•	satisfaction from income.
	•	churn status.
	6.	data_collection_phase:
	•	Use Mesa DataCollector to log model-level and agent-level metrics for this step.

⸻

6. Parameters

Define a structured parameter set that can be passed into Mesa’s BatchRunner or a custom experiment harness.

Important categories:

6.1 Population parameters
	•	N_creators
	•	N_investors
	•	N_users
	•	initial_projects
	•	initial_initiator_contributions_per_project

6.2 Behavioral parameters
	•	Creator:
	•	intrinsic_motivation_weight
	•	monetary_weight
	•	contribution_threshold
	•	beta (slope in contribution probability)
	•	p_new_initiator_base
	•	Investor:
	•	funding_cost
	•	min_expected_roi_mean
	•	min_expected_roi_std
	•	User:
	•	lambda_usage_per_step (mean usage events per user)
	•	demand_reputation_weight
	•	quality_sensitivity

6.3 Economic parameters
	•	gas_fee_share_rate (0.001–0.01)
	•	investor_royalty_min (for funding contributions)
	•	investor_royalty_max
	•	default_derivative_split (for example 0.5)
	•	type_to_default_split dict (override splits per contribution type)

6.4 Tracing and fairness parameters
	•	tracing_accuracy (0–1)
	•	max_graph_depth (optional cap on how far upstream royalty flows go)
	•	max_ancestors_per_event (for performance)

6.5 Satisfaction and churn
	•	aspiration_income_creators
	•	aspiration_income_investors
	•	aspiration_income_users (optional)
	•	satisfaction_k (slope)
	•	churn_threshold
	•	churn_steps

6.6 Run control
	•	max_steps (simulation length)
	•	random_seed
	•	experiment tags, etc.

⸻

7. Data collection and output schemas

We want three main tables per batch of runs:
	1.	Run summary (one row per run)
	2.	Time series (one row per run per step)
	3.	Agent outcomes (one row per agent per run)

These will be written as CSV or Parquet and will be the main input to external analysis.

7.1 Mesa DataCollector setup

Inside BitRewardsModel:

self.datacollector = DataCollector(
    model_reporters={
        "step": lambda m: m.schedule.time,
        "total_contributions": compute_total_contributions,
        "total_contributions_by_type": compute_contributions_by_type,
        "active_creators": compute_active_creators,
        "active_investors": compute_active_investors,
        "active_users": compute_active_users,
        "total_usage_events": lambda m: m.total_usage_events_this_step,
        "total_fee_distributed": lambda m: m.total_fee_distributed_this_step,
        "gini_creators_wealth": compute_gini_creators,
        "gini_all_wealth": compute_gini_all,
        "mean_creator_income": compute_mean_creator_income,
        "mean_investor_roi": compute_mean_investor_roi,
        "mean_tracing_depth": compute_mean_tracing_depth,
        # add more if needed
    },
    agent_reporters={
        "agent_type": lambda a: a.__class__.__name__,
        "wealth": "wealth",
        "satisfaction": "satisfaction",
        "active": "active",
        # other relevant attributes, depending on agent type
    }
)

7.1.1 Helper metrics
	•	compute_total_contributions
Count of model.contributions.
	•	compute_contributions_by_type
Return a dict or separate columns like contrib_type_software_code, etc.
	•	compute_gini_*
Standard Gini computation on wealth arrays.
	•	compute_mean_investor_roi
For each investor:
	•	roi = (wealth - initial_budget) / max(initial_budget, epsilon)
	•	Average over active investors.
	•	compute_mean_tracing_depth
Average length of paths used in reward distribution for events in that step (optional, but useful).

7.2 Run summary table schema

After each run, compute a summary row aggregating metrics over time. Example columns:
	•	Run identifiers:
	•	run_id
	•	random_seed
	•	Key parameters (copy from parameter set):
	•	gas_fee_share_rate
	•	tracing_accuracy
	•	investor_royalty_min
	•	investor_royalty_max
	•	etc.
	•	Aggregated outcomes:
	•	avg_total_contributions
	•	final_total_contributions
	•	avg_active_creators
	•	final_active_creators
	•	avg_active_investors
	•	final_active_investors
	•	avg_total_usage_events
	•	final_total_usage_events
	•	avg_gini_creators_wealth
	•	final_gini_creators_wealth
	•	avg_mean_investor_roi
	•	median_investor_roi
	•	fraction_creators_below_min_income
	•	fraction_investors_positive_roi
	•	collapse_indicator
Boolean: true if active creators fall below threshold.

This is the table you will give to Kosmos for sensitivity analysis and optimization.

7.3 Time series table schema

One row per run per step, columns:
	•	run_id
	•	step
	•	Same model metrics that DataCollector stores per step:
	•	total_contributions
	•	active_creators
	•	active_investors
	•	total_usage_events
	•	total_fee_distributed
	•	gini_creators_wealth
	•	etc.

7.4 Agent outcomes table schema

One row per agent per run:
	•	run_id
	•	agent_id
	•	agent_type (“CreatorAgent”, “InvestorAgent”, “UserAgent”)
	•	role (for creators)
	•	initial_state snapshot
	•	final_wealth
	•	final_satisfaction
	•	active_at_end (bool)
	•	For investors:
	•	total_invested
	•	final_roi
	•	For creators:
	•	contributions_count
	•	contributions_by_type (could be JSON or separate columns)

⸻

8. Implementation structure

Suggested repo layout:

bitrewards_abm/
    model/
        __init__.py
        bitrewards_model.py
        agents.py
        contributions.py
        reward.py
        metrics.py
        parameters.py
    experiments/
        run_single.py
        run_batch.py
        postprocess.py
    data/
        raw/
        processed/
    notebooks/  # optional
        exploratory_analysis.ipynb
    README.md

8.1 agents.py

Contains:
	•	CreatorAgent(Agent)
	•	InvestorAgent(Agent)
	•	UserAgent(Agent)

Each with:
	•	__init__
	•	step methods that delegate to phases or separate functions (for clarity, the model might call role-specific methods instead of the default scheduler step).

8.2 contributions.py

Define:
	•	Project dataclass or simple class
	•	Contribution dataclass
	•	Functions to:
	•	create projects
	•	create contributions
	•	update graph
	•	lookup contributions per project, per owner, etc.

8.3 reward.py

Central place for:
	•	distribute_reward(model, terminal_contribution_id, reward_pool)
	•	pay_contribution_owner(model, contribution_id, amount)
	•	Utility functions for graph-based calculations.

8.4 bitrewards_model.py

Contains BitRewardsModel(Model):
	•	Holds:
	•	self.schedule
	•	self.graph
	•	self.contributions
	•	self.projects
	•	self.datacollector
	•	parameter dict
	•	Implements:
	•	step() with phase sequence described in section 5.
	•	helper methods for each phase.

8.5 parameters.py
	•	Contains default parameter dictionary and helper for grid/Latin hypercube sampling to support batch experiments.

8.6 experiments/run_batch.py
	•	Accepts a parameter grid or a JSON specification.
	•	Runs many simulations with different seeds and parameter combinations.
	•	Writes out:
	•	summary table
	•	time series table
	•	agent outcomes table

⸻

9. Phased implementation plan

To keep the engineering scope manageable, recommend three phases.

Phase 1: Minimal end to end model
	•	Only one contribution type: “work”.
	•	No special reviewer/curation/bugfix distinctions.
	•	No investors yet.
	•	Graph edges:
	•	Only parent -> child with default split.
	•	AI tracing:
	•	tracing_accuracy parameter but only one parent per derivative.
	•	Implement:
	•	Creator, User
	•	Project and Contribution
	•	Reward distribution
	•	Data collection
	•	Run simple batch experiments with:
	•	gas_fee_share_rate
	•	default_derivative_split
	•	tracing_accuracy

Goal: stable model that produces sensible dynamics.

Phase 2: Add investors and basic contribution types
	•	Add InvestorAgent
	•	Add “funding” contributions and type-specific splits for:
	•	funding
	•	review
	•	curation
	•	bugfix
	•	Implement edges with type_to_default_split.
	•	Add investor ROI metrics.

Goal: approximate full BITrewards mechanics from the V4 whitepaper.  ￼

Phase 3: Rich tracing and extended roles
	•	Introduce more contribution types (annotation, recommendation, moderation, event_organization, introduction, test_case).
	•	Support multiple parents per contribution.
	•	Add max_graph_depth and max_ancestors_per_event controls for performance.
	•	Add AI tracing accuracy as a key experimental dimension.

Goal: ready-to-export simulation dataset for external scenario analysis tools.
If 
