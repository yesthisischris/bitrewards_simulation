from __future__ import annotations

import math
from typing import Dict, List, Type

from mesa import Model
from mesa.datacollection import DataCollector

from bitrewards_abm.domain.entities import Contribution, ContributionType, UsageEvent, TreasuryState
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.infrastructure.graph_store import ContributionGraph
from bitrewards_abm.simulation.agents import CreatorAgent, EconomicAgent, InvestorAgent, UserAgent


class BitRewardsModel(Model):
    def __init__(self, parameters: SimulationParameters) -> None:
        super().__init__()
        self.parameters = parameters
        self.contribution_graph = ContributionGraph()
        self.contributions: Dict[str, Contribution] = {}
        self.usage_events: List[UsageEvent] = []
        self.next_contribution_index = 0
        self.total_fee_distributed_this_step = 0.0
        self.cumulative_fee_distributed = 0.0
        self.total_usage_events_this_step = 0
        self.agent_by_identifier: Dict[int, EconomicAgent] = {}
        self.treasury = TreasuryState()
        self.total_funding_invested = 0.0
        self.initial_total_wealth = 0.0
        self.cumulative_external_inflows = 0.0
        self.creators: List[CreatorAgent] = []
        self.investors: List[InvestorAgent] = []
        self.users: List[UserAgent] = []
        self.reward_paid_by_type_this_step: Dict[ContributionType, float] = {
            contribution_type: 0.0 for contribution_type in ContributionType
        }
        self.reward_paid_by_role_this_step: Dict[str, float] = {
            "creator": 0.0,
            "investor": 0.0,
            "user": 0.0,
        }
        self.total_reward_paid_by_type: Dict[ContributionType, float] = {
            contribution_type: 0.0 for contribution_type in ContributionType
        }
        self.total_reward_paid_by_role: Dict[str, float] = {
            "creator": 0.0,
            "investor": 0.0,
            "user": 0.0,
        }
        self.datacollector = DataCollector(
            model_reporters={
                "step": lambda m: m.steps,
                "contribution_count": contribution_count,
                "usage_event_count": usage_event_count,
                "active_creator_count": active_creator_count,
                "active_investor_count": active_investor_count,
                "active_user_count": active_user_count,
                "total_fee_distributed": total_fee_distributed,
                "cumulative_fee_distributed": cumulative_fee_distributed,
                "creator_wealth_gini": creator_wealth_gini,
                "investor_mean_roi": investor_mean_roi,
                "mean_creator_satisfaction": mean_creator_satisfaction,
                "mean_investor_satisfaction": mean_investor_satisfaction,
                "mean_user_satisfaction": mean_user_satisfaction,
                "creator_churned_count": creator_churned_count,
                "investor_churned_count": investor_churned_count,
                "user_churned_count": user_churned_count,
                "core_research_contribution_count": core_research_contribution_count,
                "funding_contribution_count": funding_contribution_count,
                "supporting_contribution_count": supporting_contribution_count,
                "total_reward_core_research": total_reward_core_research,
                "total_reward_funding": total_reward_funding,
                "total_reward_supporting": total_reward_supporting,
                "total_income_creators": total_income_creators,
                "total_income_investors": total_income_investors,
                "total_income_users": total_income_users,
                "role_income_share_creators": role_income_share_creators,
                "role_income_share_investors": role_income_share_investors,
                "role_income_share_users": role_income_share_users,
                "treasury_balance": treasury_balance,
                "total_funding_invested": total_funding_invested,
                "total_wealth": total_wealth,
            },
            agent_reporters={
                "wealth": "wealth",
                "satisfaction": "satisfaction",
                "active": "is_active",
                "agent_type": lambda agent: agent.__class__.__name__,
            },
        )
        self.create_initial_population()
        self.initial_total_wealth = self._compute_total_wealth()

    def _compute_total_wealth(self) -> float:
        total = 0.0
        for agent in self.agent_by_identifier.values():
            total += getattr(agent, "wealth", 0.0)
            total += getattr(agent, "budget", 0.0)
        total += self.treasury.balance
        return total

    def reset_step_internal_state(self) -> None:
        self.reset_agents_for_new_step()
        self.usage_events.clear()
        self.total_fee_distributed_this_step = 0.0
        self.total_usage_events_this_step = 0
        for contribution_type in self.reward_paid_by_type_this_step:
            self.reward_paid_by_type_this_step[contribution_type] = 0.0
        for role in self.reward_paid_by_role_this_step:
            self.reward_paid_by_role_this_step[role] = 0.0

    def step(self) -> None:
        self.reset_step_internal_state()
        self.run_phase_for_agent_type(CreatorAgent)
        self.run_phase_for_agent_type(InvestorAgent)
        self.run_phase_for_agent_type(UserAgent)
        self.distribute_usage_event_fees()
        self._update_agent_satisfaction_and_churn()
        self.datacollector.collect(self)

    def register_creator_contribution(
        self,
        creator: CreatorAgent,
        contribution_type: ContributionType,
        quality: float,
        parent_identifier: str | None,
    ) -> str:
        identifier = self.next_contribution_identifier()
        parents: List[str] = []
        if parent_identifier is not None and parent_identifier in self.contributions:
            parents.append(parent_identifier)
        contribution = Contribution(
            contribution_id=identifier,
            project_id=None,
            owner_id=creator.unique_id,
            contribution_type=contribution_type,
            quality=quality,
            parents=parents,
        )
        self.contributions[identifier] = contribution
        self.contribution_graph.add_contribution_node(identifier)
        derivative_split = self.parameters.get_derivative_split_for(contribution_type)
        if derivative_split > 0.0:
            for parent in parents:
                if self.random.random() <= self.parameters.tracing_accuracy:
                    self.contribution_graph.add_parent_child_edge(
                        parent_id=parent,
                        child_id=identifier,
                        split_fraction=derivative_split,
                    )
        return identifier

    def register_funding_contribution(
        self,
        investor: InvestorAgent,
        target_identifier: str,
    ) -> str | None:
        if target_identifier not in self.contributions:
            return None
        target_contribution = self.contributions[target_identifier]
        identifier = self.next_contribution_identifier()
        parents: List[str] = [target_identifier]
        contribution = Contribution(
            contribution_id=identifier,
            project_id=target_contribution.project_id,
            owner_id=investor.unique_id,
            contribution_type=ContributionType.FUNDING,
            quality=target_contribution.quality,
            parents=parents,
        )
        self.contributions[identifier] = contribution
        self.contribution_graph.add_contribution_node(identifier)
        cost = self.parameters.funding_contribution_cost
        if cost > 0.0:
            self.total_funding_invested += cost
            treasury_fraction = self.parameters.treasury_funding_rate
            treasury_amount = max(0.0, min(1.0, treasury_fraction)) * cost
            creator_amount = cost - treasury_amount
            creator_agent = self.agent_by_identifier.get(target_contribution.owner_id)
            if creator_agent is not None:
                creator_agent.wealth += creator_amount
            if treasury_amount > 0.0:
                self.treasury.balance += treasury_amount
                self.treasury.cumulative_inflows += treasury_amount
            if hasattr(target_contribution, "funding_raised"):
                target_contribution.funding_raised += cost
        funding_split = self.parameters.get_funding_split_for_target_type(
            target_contribution.contribution_type
        )
        if funding_split > 0.0:
            self.contribution_graph.add_parent_child_edge(
                parent_id=identifier,
                child_id=target_identifier,
                split_fraction=funding_split,
            )
        return identifier

    def register_usage_event(self, contribution_identifier: str, gross_value: float) -> None:
        if contribution_identifier not in self.contributions:
            return
        contribution = self.contributions[contribution_identifier]
        base_share = self.parameters.get_base_royalty_share_for(
            contribution.contribution_type
        )
        fee_amount = gross_value * self.parameters.gas_fee_share_rate * base_share
        if fee_amount <= 0.0:
            return
        usage_event = UsageEvent(
            contribution_id=contribution_identifier,
            gross_value=gross_value,
            fee_amount=fee_amount,
        )
        self.usage_events.append(usage_event)

    def next_contribution_identifier(self) -> str:
        identifier = f"c{self.next_contribution_index}"
        self.next_contribution_index += 1
        return identifier

    def create_initial_population(self) -> None:
        identifier = 0
        for _ in range(self.parameters.creator_count):
            role = "developer"
            skill = self.random.uniform(
                self.parameters.min_creator_skill,
                self.parameters.max_creator_skill,
            )
            creator = CreatorAgent(
                unique_id=identifier,
                model=self,
                parameters=self.parameters,
                role=role,
                skill=skill,
            )
            self.agent_by_identifier[identifier] = creator
            self.creators.append(creator)
            identifier += 1
        for _ in range(self.parameters.investor_count):
            investor = InvestorAgent(
                unique_id=identifier,
                model=self,
                parameters=self.parameters,
                initial_budget=self.parameters.initial_investor_budget,
            )
            self.agent_by_identifier[identifier] = investor
            self.investors.append(investor)
            identifier += 1
        for _ in range(self.parameters.user_count):
            user = UserAgent(
                unique_id=identifier,
                model=self,
                parameters=self.parameters,
            )
            self.agent_by_identifier[identifier] = user
            self.users.append(user)
            identifier += 1

    def reset_agents_for_new_step(self) -> None:
        for agent in self.agent_by_identifier.values():
            if isinstance(agent, EconomicAgent):
                agent.reset_step_state()

    def run_phase_for_agent_type(self, agent_type: Type[EconomicAgent]) -> None:
        if agent_type is CreatorAgent:
            agents = list(self.creators)
        elif agent_type is InvestorAgent:
            agents = list(self.investors)
        elif agent_type is UserAgent:
            agents = list(self.users)
        else:
            agents = []
        for agent in agents:
            agent.step()

    def select_parent_for_new_contribution(self) -> str | None:
        if not self.contributions:
            return None
        identifiers = list(self.contributions.keys())
        qualities = [self.contributions[i].quality for i in identifiers]
        minimum_quality = 0.01
        weights = [max(q, minimum_quality) for q in qualities]
        chosen_identifier = self.random.choices(identifiers, weights=weights, k=1)[0]
        return chosen_identifier

    def select_contribution_for_funding(self) -> str | None:
        candidates = [
            c
            for c in self.contributions.values()
            if c.contribution_type != ContributionType.FUNDING
            and c.quality >= self.parameters.investor_min_target_quality
        ]
        if not candidates:
            return None
        identifiers = [c.contribution_id for c in candidates]
        qualities = [c.quality for c in candidates]
        minimum_quality = 0.01
        weights = [max(q, minimum_quality) for q in qualities]
        chosen_identifier = self.random.choices(identifiers, weights=weights, k=1)[0]
        return chosen_identifier

    def distribute_usage_event_fees(self) -> None:
        for event in self.usage_events:
            total_fee = event.fee_amount
            if total_fee <= 0.0:
                continue
            self.total_usage_events_this_step += 1
            self.total_fee_distributed_this_step += total_fee
            self.cumulative_fee_distributed += total_fee
            self.cumulative_external_inflows += total_fee
            treasury_cut = total_fee * self.parameters.treasury_fee_rate
            royalty_pool = total_fee - treasury_cut
            if treasury_cut > 0.0:
                self.treasury.balance += treasury_cut
                self.treasury.cumulative_inflows += treasury_cut
            if royalty_pool <= 0.0:
                continue
            self.distribute_fee_pool_for_event(event, royalty_pool)

    def _update_agent_satisfaction_and_churn(self) -> None:
        epsilon = 1e-6
        k = self.parameters.satisfaction_logistic_k
        threshold = self.parameters.satisfaction_churn_threshold
        roi_window = self.parameters.roi_churn_window
        noise_std = self.parameters.satisfaction_noise_std
        for agent in self.agent_by_identifier.values():
            if not isinstance(agent, EconomicAgent):
                continue
            if isinstance(agent, UserAgent):
                target_income = agent.aspiration_income
                if target_income <= 0.0:
                    target_income = self.parameters.aspiration_income_per_step
                signal = agent.current_income / (target_income + epsilon)
            else:
                roi = agent.current_roi
                signal = 1.0 + roi
                if signal < 0.0:
                    signal = 0.0
            satisfaction = 1.0 / (1.0 + math.exp(-k * (signal - 1.0)))
            if noise_std > 0.0:
                satisfaction += self.random.gauss(0.0, noise_std)
            if satisfaction < 0.0:
                satisfaction = 0.0
            elif satisfaction > 1.0:
                satisfaction = 1.0
            agent.satisfaction = satisfaction
            if agent.satisfaction < threshold:
                agent.low_satisfaction_streak += 1
            else:
                agent.low_satisfaction_streak = 0
            if isinstance(agent, InvestorAgent):
                roi_threshold = self.parameters.investor_roi_exit_threshold
                if agent.current_roi < roi_threshold and agent.low_satisfaction_streak >= roi_window:
                    agent.is_active = False
            elif isinstance(agent, CreatorAgent):
                roi_threshold = self.parameters.creator_roi_exit_threshold
                if agent.current_roi < roi_threshold and agent.low_satisfaction_streak >= roi_window:
                    agent.is_active = False
            elif isinstance(agent, UserAgent):
                if agent.low_satisfaction_streak >= self.parameters.satisfaction_churn_window:
                    agent.is_active = False

    def distribute_fee_pool_for_event(self, event: UsageEvent, fee_pool: float) -> None:
        remaining_items: List[tuple[str, float]] = [
            (event.contribution_id, fee_pool)
        ]
        visited = set()
        while remaining_items:
            current_identifier, pool_value = remaining_items.pop()
            key = (current_identifier, pool_value)
            if key in visited:
                continue
            visited.add(key)
            parents = self.contribution_graph.get_parents(current_identifier)
            if not parents:
                self.pay_contribution_owner(current_identifier, pool_value)
                continue
            split_values = [
                self.contribution_graph.get_split_fraction(parent, current_identifier)
                for parent in parents
            ]
            clipped_splits = [max(0.0, min(1.0, value)) for value in split_values]
            total_split = sum(clipped_splits)
            if total_split == 0.0:
                self.pay_contribution_owner(current_identifier, pool_value)
                continue
            if total_split > 1.0:
                normalized_splits = [value / total_split for value in clipped_splits]
            else:
                normalized_splits = clipped_splits
            parent_amounts: List[float] = []
            total_parent_amount = 0.0
            for value in normalized_splits:
                amount = pool_value * value
                parent_amounts.append(amount)
                total_parent_amount += amount
            own_amount = pool_value - total_parent_amount
            if own_amount < 0.0:
                own_amount = 0.0
            self.pay_contribution_owner(current_identifier, own_amount)
            for parent_identifier, amount in zip(parents, parent_amounts):
                if amount <= 0.0:
                    continue
                remaining_items.append((parent_identifier, amount))

    def _infer_role_for_agent(self, agent: EconomicAgent) -> str | None:
        if isinstance(agent, CreatorAgent):
            return "creator"
        if isinstance(agent, InvestorAgent):
            return "investor"
        if isinstance(agent, UserAgent):
            return "user"
        return None

    def pay_contribution_owner(self, contribution_identifier: str, amount: float) -> None:
        if amount <= 0.0:
            return
        contribution = self.contributions.get(contribution_identifier)
        if contribution is None:
            return
        owner_identifier = contribution.owner_id
        agent = self.agent_by_identifier.get(owner_identifier)
        if agent is None or not agent.is_active:
            return
        if isinstance(agent, EconomicAgent):
            agent.record_income(amount)
        else:
            agent.receive_income(amount)
        contribution_type = contribution.contribution_type
        self.reward_paid_by_type_this_step[contribution_type] += amount
        self.total_reward_paid_by_type[contribution_type] += amount
        role_name = self._infer_role_for_agent(agent)
        if role_name is None:
            return
        self.reward_paid_by_role_this_step[role_name] += amount
        self.total_reward_paid_by_role[role_name] += amount


def contribution_count(model: BitRewardsModel) -> int:
    return len(model.contributions)


def usage_event_count(model: BitRewardsModel) -> int:
    return model.total_usage_events_this_step


def total_fee_distributed(model: BitRewardsModel) -> float:
    return model.total_fee_distributed_this_step


def cumulative_fee_distributed(model: BitRewardsModel) -> float:
    return model.cumulative_fee_distributed


def active_creator_count(model: BitRewardsModel) -> int:
    return count_active_agents_for_type(model, CreatorAgent)


def active_investor_count(model: BitRewardsModel) -> int:
    return count_active_agents_for_type(model, InvestorAgent)


def active_user_count(model: BitRewardsModel) -> int:
    return count_active_agents_for_type(model, UserAgent)


def count_active_agents_for_type(
    model: BitRewardsModel,
    agent_type: Type[EconomicAgent],
) -> int:
    if agent_type is CreatorAgent:
        agents = model.creators
    elif agent_type is InvestorAgent:
        agents = model.investors
    elif agent_type is UserAgent:
        agents = model.users
    else:
        agents = []
    return sum(1 for agent in agents if agent.is_active)


def gini(values: List[float]) -> float:
    non_negative_values = [value for value in values if value >= 0.0]
    if not non_negative_values:
        return 0.0
    ordered_values = sorted(non_negative_values)
    count = len(ordered_values)
    total = sum(ordered_values)
    if total == 0.0:
        return 0.0
    weighted_sum = 0.0
    for index, value in enumerate(ordered_values, start=1):
        weighted_sum += index * value
    coefficient = (2.0 * weighted_sum) / (count * total) - (count + 1.0) / count
    return coefficient


def creator_wealth_gini(model: BitRewardsModel) -> float:
    creator_values = [agent.wealth for agent in model.creators]
    return gini(creator_values)


def investor_mean_roi(model: BitRewardsModel) -> float:
    investor_agents = model.investors
    roi_values: List[float] = []
    for investor in investor_agents:
        if getattr(investor, "cumulative_cost", 0.0) <= 0.0:
            continue
        roi_values.append(investor.current_roi)
    if not roi_values:
        return 0.0
    return sum(roi_values) / len(roi_values)


def mean_creator_satisfaction(model: BitRewardsModel) -> float:
    return mean_satisfaction(model.creators)


def mean_investor_satisfaction(model: BitRewardsModel) -> float:
    return mean_satisfaction(model.investors)


def mean_user_satisfaction(model: BitRewardsModel) -> float:
    return mean_satisfaction(model.users)


def mean_satisfaction(agents: List[EconomicAgent]) -> float:
    if not agents:
        return 0.0
    return sum(agent.satisfaction for agent in agents) / len(agents)


def creator_churned_count(model: BitRewardsModel) -> int:
    return churned_count(model.creators)


def investor_churned_count(model: BitRewardsModel) -> int:
    return churned_count(model.investors)


def user_churned_count(model: BitRewardsModel) -> int:
    return churned_count(model.users)


def churned_count(agents: List[EconomicAgent]) -> int:
    return sum(1 for agent in agents if not agent.is_active)


def contribution_count_for_type(
    model: BitRewardsModel,
    contribution_type: ContributionType,
) -> int:
    return sum(1 for contribution in model.contributions.values() if contribution.contribution_type is contribution_type)


def core_research_contribution_count(model: BitRewardsModel) -> int:
    return contribution_count_for_type(model, ContributionType.CORE_RESEARCH)


def funding_contribution_count(model: BitRewardsModel) -> int:
    return contribution_count_for_type(model, ContributionType.FUNDING)


def supporting_contribution_count(model: BitRewardsModel) -> int:
    return contribution_count_for_type(model, ContributionType.SUPPORTING)


def total_reward_core_research(model: BitRewardsModel) -> float:
    return model.total_reward_paid_by_type.get(ContributionType.CORE_RESEARCH, 0.0)


def total_reward_funding(model: BitRewardsModel) -> float:
    return model.total_reward_paid_by_type.get(ContributionType.FUNDING, 0.0)


def total_reward_supporting(model: BitRewardsModel) -> float:
    return model.total_reward_paid_by_type.get(ContributionType.SUPPORTING, 0.0)


def total_income_creators(model: BitRewardsModel) -> float:
    return model.total_reward_paid_by_role.get("creator", 0.0)


def total_income_investors(model: BitRewardsModel) -> float:
    return model.total_reward_paid_by_role.get("investor", 0.0)


def total_income_users(model: BitRewardsModel) -> float:
    return model.total_reward_paid_by_role.get("user", 0.0)


def role_income_share_creators(model: BitRewardsModel) -> float:
    total_fee = model.cumulative_fee_distributed
    if total_fee <= 0.0:
        return 0.0
    return total_income_creators(model) / total_fee


def role_income_share_investors(model: BitRewardsModel) -> float:
    total_fee = model.cumulative_fee_distributed
    if total_fee <= 0.0:
        return 0.0
    return total_income_investors(model) / total_fee


def role_income_share_users(model: BitRewardsModel) -> float:
    total_fee = model.cumulative_fee_distributed
    if total_fee <= 0.0:
        return 0.0
    return total_income_users(model) / total_fee


def treasury_balance(model: BitRewardsModel) -> float:
    return model.treasury.balance


def total_funding_invested(model: BitRewardsModel) -> float:
    return model.total_funding_invested


def total_wealth(model: BitRewardsModel) -> float:
    return model._compute_total_wealth()
