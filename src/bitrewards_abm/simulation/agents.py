from __future__ import annotations

from typing import List, Set

from mesa import Agent

from bitrewards_abm.domain.entities import ContributionType
from bitrewards_abm.domain.parameters import SimulationParameters


class EconomicAgent(Agent):
    def __init__(self, unique_id: int, model, parameters: SimulationParameters) -> None:
        super().__init__(model)
        self.unique_id = unique_id
        self.parameters = parameters
        self.wealth = 0.0
        self.current_income = 0.0
        self.satisfaction = parameters.initial_agent_satisfaction
        self.aspiration_income = parameters.aspiration_income_per_step
        self.low_satisfaction_streak = 0
        self.is_active = True
        self.cumulative_income = 0.0
        self.cumulative_cost = 0.0
        self.roi_history: List[float] = []

    def reset_step_state(self) -> None:
        self.current_income = 0.0

    @property
    def current_roi(self) -> float:
        epsilon = 1e-6
        if self.cumulative_cost <= 0.0:
            return 0.0
        return self.cumulative_income / (self.cumulative_cost + epsilon) - 1.0

    def record_income(self, amount: float) -> None:
        if amount <= 0.0:
            return
        self.current_income += amount
        self.wealth += amount
        self.cumulative_income += amount
        self.roi_history.append(self.current_roi)

    def record_cost(self, amount: float) -> None:
        if amount <= 0.0:
            return
        self.cumulative_cost += amount
        self.roi_history.append(self.current_roi)

    def receive_income(self, amount: float) -> None:
        self.record_income(amount)


class CreatorAgent(EconomicAgent):
    def __init__(self, unique_id: int, model, parameters: SimulationParameters, role: str, skill: float) -> None:
        super().__init__(unique_id, model, parameters)
        self.role = role
        self.skill = skill

    def step(self) -> None:
        if not self.is_active:
            return
        probability = self.parameters.creator_base_contribution_probability
        if self.random.random() < probability:
            self.create_contribution()

    def create_contribution(self) -> None:
        contribution_type = self.infer_contribution_type_from_role()
        quality = self.draw_contribution_quality()
        parent_identifier = self.model.select_parent_for_new_contribution()
        cost = getattr(self.parameters, "creator_contribution_cost", 0.0)
        if cost > 0.0:
            self.record_cost(cost)
        self.model.register_creator_contribution(
            creator=self,
            contribution_type=contribution_type,
            quality=quality,
            parent_identifier=parent_identifier,
        )

    def infer_contribution_type_from_role(self) -> ContributionType:
        core_roles = {"developer", "scientist", "engineer", "researcher"}
        supporting_roles = {"reviewer", "educator", "curator", "moderator", "facilitator"}
        if self.role in core_roles:
            return ContributionType.CORE_RESEARCH
        if self.role in supporting_roles:
            return ContributionType.SUPPORTING
        return ContributionType.CORE_RESEARCH

    def draw_contribution_quality(self) -> float:
        noise_span = self.parameters.quality_noise_scale
        raw_quality = self.skill + self.random.uniform(-noise_span, noise_span)
        if raw_quality < 0.0:
            return 0.0
        if raw_quality > 1.0:
            return 1.0
        return raw_quality


class InvestorAgent(EconomicAgent):
    def __init__(self, unique_id: int, model, parameters: SimulationParameters, initial_budget: float) -> None:
        super().__init__(unique_id, model, parameters)
        self.budget = initial_budget
        self.total_invested = 0.0
        self.funding_contribution_identifiers: Set[str] = set()

    def step(self) -> None:
        if not self.is_active:
            return
        max_per_step = self.parameters.investor_max_funding_per_step
        if max_per_step <= 0:
            return
        cost = self.parameters.funding_contribution_cost
        for _ in range(max_per_step):
            if self.budget < cost:
                break
            target_identifier = self.model.select_contribution_for_funding()
            if target_identifier is None:
                break
            funding_identifier = self.model.register_funding_contribution(
                investor=self,
                target_identifier=target_identifier,
            )
            if funding_identifier is None:
                break
            self.budget -= cost
            self.total_invested += cost
            self.record_cost(cost)
            self.funding_contribution_identifiers.add(funding_identifier)


class UserAgent(EconomicAgent):
    def step(self) -> None:
        if not self.is_active:
            return
        if not self.model.contributions:
            return
        if self.random.random() > self.parameters.user_usage_probability:
            return
        mean_usage = getattr(self.parameters, "user_mean_usage_rate", 1.0)
        if mean_usage <= 0.0:
            return
        num_events = self.model._sample_poisson(mean_usage)
        if num_events <= 0:
            return
        for _ in range(num_events):
            contribution_identifier = self.select_contribution_for_usage()
            if contribution_identifier is None:
                break
            gross_value = self.parameters.base_gross_value
            self.model.register_usage_event(contribution_identifier, gross_value)

    def select_contribution_for_usage(self) -> str | None:
        identifiers = list(self.model.contributions.keys())
        if not identifiers:
            return None
        index = self.random.randrange(len(identifiers))
        return identifiers[index]
