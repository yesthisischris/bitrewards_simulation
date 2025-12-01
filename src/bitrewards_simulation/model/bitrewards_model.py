"""Core Mesa model for the BITrewards simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from mesa import Model
from mesa.datacollection import DataCollector

from bitrewards_simulation.model.agents import CreatorAgent, EconomicAgent, UserAgent


@dataclass
class Contribution:
    contribution_id: int
    owner_id: int
    timestamp_created: int
    quality: float
    parents: List[int] = field(default_factory=list)


class BitRewardsModel(Model):
    def __init__(
        self,
        N_creators: int = 50,
        N_users: int = 200,
        max_steps: int = 200,
        base_expected_payoff: float = 1.0,
        intrinsic_motivation_weight: float = 0.5,
        monetary_weight: float = 0.5,
        contribution_beta: float = 4.0,
        contribution_threshold: float = 0.5,
        income_ema_alpha: float = 0.3,
        max_usage_events_per_user: int = 3,
        gross_value: float = 1.0,
        fee_share_rate: float = 0.005,
        random_seed: Optional[int] = None,
    ) -> None:
        super().__init__(seed=random_seed)
        self.random_seed = random_seed

        self.N_creators = N_creators
        self.N_users = N_users
        self.max_steps = max_steps
        self.base_expected_payoff = base_expected_payoff
        self.intrinsic_motivation_weight = intrinsic_motivation_weight
        self.monetary_weight = monetary_weight
        self.contribution_beta = contribution_beta
        self.contribution_threshold = contribution_threshold
        self.income_ema_alpha = income_ema_alpha
        self.max_usage_events_per_user = max_usage_events_per_user
        self.gross_value = gross_value
        self.fee_share_rate = fee_share_rate

        self.running: bool = True

        self.contributions: Dict[int, Contribution] = {}
        self.next_contribution_id: int = 0

        self.usage_events: List[Tuple[int, float, float]] = []
        self.total_usage_events_this_step: int = 0

        self.creators: List[CreatorAgent] = []
        self.users: List[UserAgent] = []
        self.agents_by_id: Dict[int, EconomicAgent] = {}

        self._create_agents()

        self.datacollector = DataCollector(
            model_reporters={
                "step": lambda m: m.steps,
                "contribution_count": lambda m: len(m.contributions),
                "usage_event_count": lambda m: m.total_usage_events_this_step,
                "active_creator_count": lambda m: sum(
                    1 for agent in m.creators if agent.active
                ),
                "active_user_count": lambda m: sum(
                    1 for agent in m.users if agent.active
                ),
            },
        )

    def _create_agents(self) -> None:
        for _ in range(self.N_creators):
            skill = self.random.uniform(0.3, 1.0)
            intrinsic_motivation = self.random.uniform(0.3, 1.0)
            risk_aversion = self.random.uniform(0.0, 1.0)
            aspiration_income = self.random.uniform(0.5, 2.0)
            agent = CreatorAgent(
                model=self,
                aspiration_income=aspiration_income,
                skill=skill,
                intrinsic_motivation=intrinsic_motivation,
                risk_aversion=risk_aversion,
            )
            self.creators.append(agent)
            self.agents_by_id[agent.unique_id] = agent

        for _ in range(self.N_users):
            aspiration_income = 0.0
            agent = UserAgent(
                model=self,
                aspiration_income=aspiration_income,
            )
            self.users.append(agent)
            self.agents_by_id[agent.unique_id] = agent

    def create_contribution(
        self,
        owner_agent: CreatorAgent,
        parent_contribution_id: Optional[int] = None,
    ) -> Optional[Contribution]:
        contribution_id = self.next_contribution_id
        self.next_contribution_id += 1

        quality_noise = self.random.uniform(-0.1, 0.1)
        quality = max(0.0, min(1.0, owner_agent.skill + quality_noise))

        parents: List[int] = []

        contribution = Contribution(
            contribution_id=contribution_id,
            owner_id=owner_agent.unique_id,
            timestamp_created=self.steps,
            quality=quality,
            parents=parents,
        )
        self.contributions[contribution_id] = contribution

        return contribution

    def pick_parent_contribution(self) -> Optional[int]:
        return None

    def pick_contribution_for_usage(self) -> Optional[int]:
        if not self.contributions:
            return None
        contributions = list(self.contributions.values())
        weights = [max(contribution.quality, 0.01) for contribution in contributions]
        chosen = self.random.choices(contributions, weights=weights, k=1)[0]
        return chosen.contribution_id

    def register_usage_event(
        self, contribution_id: int, gross_value: float, fee_amount: float
    ) -> None:
        if contribution_id not in self.contributions:
            return
        self.usage_events.append((contribution_id, gross_value, fee_amount))

    def step(self) -> None:
        if self.steps > self.max_steps:
            self.running = False
            return

        self.usage_events = []
        self.total_usage_events_this_step = 0

        creators = list(self.creators)
        self.random.shuffle(creators)
        for agent in creators:
            agent.step()

        users = list(self.users)
        self.random.shuffle(users)
        for agent in users:
            agent.step()

        self.total_usage_events_this_step = len(self.usage_events)

        for agent in self.agents:
            agent.update_after_rewards()

        self.datacollector.collect(self)

        if self.steps >= self.max_steps:
            self.running = False
