"""Mesa agents for the BITrewards simulation."""

from __future__ import annotations

import math
from typing import Set

from mesa import Agent


class EconomicAgent(Agent):
    """Agent with wealth, income, satisfaction, and churn state."""

    def __init__(self, model, aspiration_income: float) -> None:
        super().__init__(model)
        self.wealth: float = 0.0
        self.current_income: float = 0.0
        self.aspiration_income: float = aspiration_income
        self.satisfaction: float = 1.0
        self.active: bool = True

    def receive_income(self, amount: float) -> None:
        if amount <= 0.0:
            return
        self.wealth += amount
        self.current_income += amount

    def update_after_rewards(self) -> None:
        self.current_income = 0.0
        self.satisfaction = 1.0


class CreatorAgent(EconomicAgent):
    """Agent that mints new contributions."""

    def __init__(
        self,
        model,
        aspiration_income: float,
        skill: float,
        intrinsic_motivation: float,
        risk_aversion: float,
    ) -> None:
        super().__init__(model, aspiration_income)
        self.skill: float = skill
        self.intrinsic_motivation: float = intrinsic_motivation
        self.risk_aversion: float = risk_aversion
        self.contributions_owned: Set[int] = set()
        self.running_income_avg: float = 0.0
        self.contributions_made: int = 0

    def step(self) -> None:
        if not self.active:
            return

        if self.random.random() < self._contribution_probability():
            parent_id = self.model.pick_parent_contribution()
            contribution = self.model.create_contribution(
                owner_agent=self,
                parent_contribution_id=parent_id,
            )
            if contribution is not None:
                self.contributions_owned.add(contribution.contribution_id)
                self.contributions_made += 1

    def _contribution_probability(self) -> float:
        base_expected = self.model.base_expected_payoff
        expected_payoff = max(self.running_income_avg, base_expected)
        target = self.aspiration_income if self.aspiration_income > 0.0 else 1.0
        income_ratio = expected_payoff / target
        utility = (
            self.model.intrinsic_motivation_weight * self.intrinsic_motivation
            + self.model.monetary_weight * income_ratio
        )
        beta = self.model.contribution_beta
        threshold = self.model.contribution_threshold
        probability = 1.0 / (1.0 + math.exp(-beta * (utility - threshold)))
        return max(0.0, min(1.0, probability))

    def update_after_rewards(self) -> None:
        alpha = self.model.income_ema_alpha
        self.running_income_avg = (
            (1.0 - alpha) * self.running_income_avg + alpha * self.current_income
        )
        super().update_after_rewards()


class UserAgent(EconomicAgent):
    """Agent that generates usage events for contributions."""

    def __init__(self, model, aspiration_income: float) -> None:
        super().__init__(model, aspiration_income)

    def step(self) -> None:
        if not self.active:
            return

        max_events = self.model.max_usage_events_per_user
        if max_events <= 0:
            return

        num_events = self.random.randint(0, max_events)
        for _ in range(num_events):
            contribution_id = self.model.pick_contribution_for_usage()
            if contribution_id is None:
                break

            gross_value = self.model.gross_value
            fee_amount = gross_value * self.model.fee_share_rate
            self.model.register_usage_event(
                contribution_id=contribution_id,
                gross_value=gross_value,
                fee_amount=fee_amount,
            )
