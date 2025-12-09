from __future__ import annotations

import math
from typing import Dict, List, Type

from mesa import Model
from mesa.datacollection import DataCollector

from bitrewards_abm.domain.entities import (
    Contribution,
    ContributionType,
    UsageEvent,
    TreasuryState,
    HonorSealStatus,
)
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.infrastructure.graph_store import ContributionGraph
from bitrewards_abm.simulation.agents import CreatorAgent, EconomicAgent, InvestorAgent, UserAgent


class BitRewardsModel(Model):
    def __init__(self, parameters: SimulationParameters) -> None:
        super().__init__()
        self.parameters = parameters
        self.contribution_graph = ContributionGraph()
        self.contributions: Dict[str, Contribution] = {}
        self.reward_events: List[dict[str, object]] = []
        self.usage_events: List[dict[str, object]] = []
        self.pending_usage_events: List[UsageEvent] = []
        self.next_contribution_index = 0
        self.total_fee_distributed_this_step = 0.0
        self.cumulative_fee_distributed = 0.0
        self.total_usage_events_this_step = 0
        self.usage_events_by_honor_seal_this_step: Dict[HonorSealStatus, int] = {
            status: 0 for status in HonorSealStatus
        }
        self.agent_by_identifier: Dict[int, EconomicAgent] = {}
        self.next_agent_identifier: int = 0
        self.current_step: int = 0
        self.new_creators_this_step: int = 0
        self.new_investors_this_step: int = 0
        self.new_users_this_step: int = 0
        self.pending_payouts: List[dict[str, object]] = []
        self.treasury = TreasuryState()
        self.total_funding_invested = 0.0
        self.initial_total_wealth = 0.0
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
        self.tracing_metrics: Dict[str, int] = {
            "true_links": 0,
            "detected_true_links": 0,
            "false_positive_links": 0,
            "missed_true_links": 0,
        }
        self.datacollector = DataCollector(
            model_reporters={
                "step": lambda m: m.current_step,
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
                "new_creators_this_step": new_creators_this_step,
                "new_investors_this_step": new_investors_this_step,
                "new_users_this_step": new_users_this_step,
                "locked_funding_positions": locked_funding_positions,
                "honor_seal_honest_contribution_count": honor_seal_honest_contribution_count,
                "honor_seal_fake_contribution_count": honor_seal_fake_contribution_count,
                "honor_seal_dishonored_contribution_count": honor_seal_dishonored_contribution_count,
                "honor_seal_sealed_usage_share": honor_seal_sealed_usage_share,
                "honor_seal_dishonored_usage_share": honor_seal_dishonored_usage_share,
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

    def _agent_role_label(self, agent: EconomicAgent) -> str:
        if isinstance(agent, CreatorAgent):
            return agent.role
        if isinstance(agent, InvestorAgent):
            return "investor"
        if isinstance(agent, UserAgent):
            return "user"
        return "other"

    def _record_reward_event(
        self,
        *,
        step: int,
        payout_type: str,
        amount: float,
        recipient_id: int,
        source_contribution_id: str,
        channel: str,
    ) -> None:
        if amount <= 0.0:
            return
        agent = self.agent_by_identifier.get(recipient_id)
        if agent is None:
            return
        role_label = self._agent_role_label(agent)
        self.reward_events.append(
            {
                "step": int(step),
                "payout_type": payout_type,
                "channel": channel,
                "amount": float(amount),
                "recipient_id": int(recipient_id),
                "recipient_role": role_label,
                "source_contribution_id": source_contribution_id,
            }
        )

    def _compute_total_wealth(self) -> float:
        total = 0.0
        for agent in self.agent_by_identifier.values():
            total += getattr(agent, "wealth", 0.0)
            total += getattr(agent, "budget", 0.0)
        total += self.treasury.balance
        return total

    def reset_step_internal_state(self) -> None:
        self.reset_agents_for_new_step()
        self.pending_usage_events.clear()
        self.total_fee_distributed_this_step = 0.0
        self.total_usage_events_this_step = 0
        self.new_creators_this_step = 0
        self.new_investors_this_step = 0
        self.new_users_this_step = 0
        for contribution_type in self.reward_paid_by_type_this_step:
            self.reward_paid_by_type_this_step[contribution_type] = 0.0
        for role in self.reward_paid_by_role_this_step:
            self.reward_paid_by_role_this_step[role] = 0.0
        for status in self.usage_events_by_honor_seal_this_step:
            self.usage_events_by_honor_seal_this_step[status] = 0

    def step(self) -> None:
        self.current_step += 1
        self.reset_step_internal_state()
        self.spawn_new_agents()
        self.run_phase_for_agent_type(CreatorAgent)
        self.run_phase_for_agent_type(InvestorAgent)
        self.run_phase_for_agent_type(UserAgent)
        self.distribute_usage_event_fees()
        self._enforce_honor_seal()
        self._unlock_all_escrows()
        if self.parameters.royalty_batch_interval > 0 and self.current_step % self.parameters.royalty_batch_interval == 0:
            self._distribute_batched_royalties()
        self._flush_pending_payouts_if_due()
        self._decrement_funding_lockups(unlock=False)
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
        contribution = Contribution(
            contribution_id=identifier,
            project_id=None,
            owner_id=creator.unique_id,
            contribution_type=contribution_type,
            quality=quality,
            parents=[],
            true_parents=[],
            kind=creator.role,
        )
        self.contributions[identifier] = contribution
        self.contribution_graph.add_contribution_node(identifier)
        true_parents: List[str] = []
        if parent_identifier is not None and parent_identifier in self.contributions:
            true_parents.append(parent_identifier)
        contribution.true_parents = true_parents
        parent_for_inheritance: str | None = true_parents[0] if true_parents else None
        if parent_for_inheritance is None:
            self._apply_honor_seal_to_root(contribution, creator)
        else:
            self._inherit_honor_seal(contribution, parent_for_inheritance)
        self.tracing_metrics["true_links"] += len(true_parents)
        if not true_parents:
            return identifier
        true_parent_id = true_parents[0]
        tracing_accuracy = max(0.0, min(1.0, self.parameters.tracing_accuracy))
        false_positive_rate = max(
            0.0,
            min(1.0, getattr(self.parameters, "tracing_false_positive_rate", 0.0)),
        )
        edge_parent: str | None = None
        if self.random.random() < tracing_accuracy:
            edge_parent = true_parent_id
            self.tracing_metrics["detected_true_links"] += 1
        else:
            self.tracing_metrics["missed_true_links"] += 1
            if self.random.random() < false_positive_rate:
                candidates = [
                    cid
                    for cid in self.contributions.keys()
                    if cid not in true_parents and cid != identifier
                ]
                if candidates:
                    edge_parent = self.random.choice(candidates)
                    self.tracing_metrics["false_positive_links"] += 1
        if edge_parent is not None:
            contribution.parents = [edge_parent]
            royalty_percent = self.parameters.get_derivative_split_for(contribution_type)
            if royalty_percent > 0.0:
                edge_type = "supporting" if contribution_type is ContributionType.SUPPORTING else "derivative"
                self.contribution_graph.add_royalty_edge(
                    parent_identifier=edge_parent,
                    child_identifier=identifier,
                    royalty_percent=royalty_percent,
                    edge_type=edge_type,
                )
        return identifier

    def _apply_honor_seal_to_root(self, contribution: Contribution, creator: CreatorAgent) -> None:
        if not getattr(self.parameters, "honor_seal_enabled", False):
            return
        adoption_rate = getattr(self.parameters, "honor_seal_initial_adoption_rate", 0.0)
        if adoption_rate <= 0.0:
            return
        if self.random.random() > adoption_rate:
            return
        cost = getattr(self.parameters, "honor_seal_mint_cost_btc", 0.0)
        if cost > 0.0 and creator.wealth < cost:
            return
        if cost > 0.0:
            creator.wealth -= cost
            self.treasury.balance += cost
            self.treasury.cumulative_inflows += cost
        fake_rate = getattr(self.parameters, "honor_seal_fake_rate", 0.0)
        if fake_rate > 0.0 and self.random.random() < fake_rate:
            contribution.honor_seal_status = HonorSealStatus.FAKE
        else:
            contribution.honor_seal_status = HonorSealStatus.HONEST
        contribution.honor_seal_mint_step = self.current_step

    def _inherit_honor_seal(self, contribution: Contribution, parent_identifier: str) -> None:
        parent = self.contributions.get(parent_identifier)
        if parent is None:
            return
        contribution.honor_seal_status = parent.honor_seal_status
        contribution.honor_seal_mint_step = parent.honor_seal_mint_step

    def register_funding_contribution(
        self,
        investor: InvestorAgent,
        target_identifier: str,
    ) -> str | None:
        if target_identifier not in self.contributions:
            return None
        target_contribution = self.contributions[target_identifier]
        max_available = min(self.parameters.funding_max_amount, investor.budget)
        if max_available <= 0.0:
            return None
        min_available = min(self.parameters.funding_min_amount, max_available)
        amount = self.random.uniform(min_available, max_available)
        royalty_percent = self.random.uniform(
            self.parameters.funding_royalty_min,
            self.parameters.funding_royalty_max,
        )
        investor.budget -= amount
        investor.total_invested += amount
        investor.record_cost(amount)
        identifier = self.next_contribution_identifier()
        parents: List[str] = [target_identifier]
        contribution = Contribution(
            contribution_id=identifier,
            project_id=target_contribution.project_id,
            owner_id=investor.unique_id,
            contribution_type=ContributionType.FUNDING,
            quality=target_contribution.quality,
            parents=parents,
            kind="funding",
            royalty_percent=royalty_percent,
        )
        lockup_steps = max(0, self.parameters.funding_lockup_period_steps)
        contribution.lockup_remaining_steps = lockup_steps
        self.contributions[identifier] = contribution
        self.contribution_graph.add_contribution_node(identifier)
        self.total_funding_invested += amount
        treasury_fraction = self.parameters.treasury_funding_rate
        treasury_amount = max(0.0, min(1.0, treasury_fraction)) * amount
        creator_amount = amount - treasury_amount
        creator_agent = self.agent_by_identifier.get(target_contribution.owner_id)
        if creator_agent is not None:
            creator_agent.wealth += creator_amount
        if treasury_amount > 0.0:
            self.treasury.balance += treasury_amount
            self.treasury.cumulative_inflows += treasury_amount
        if hasattr(target_contribution, "funding_raised"):
            target_contribution.funding_raised += amount
        funding_split = self.parameters.get_funding_split_for_target_type(
            target_contribution.contribution_type
        )
        if funding_split > 0.0:
            self.contribution_graph.add_royalty_edge(
                parent_identifier=identifier,
                child_identifier=target_identifier,
                royalty_percent=royalty_percent if royalty_percent > 0.0 else funding_split,
                edge_type="funding",
            )
        return identifier

    def register_usage_event(self, contribution_identifier: str, gross_value: float, user_id: int | None = None) -> None:
        if contribution_identifier not in self.contributions:
            return
        adjusted_value = gross_value
        if self.parameters.usage_shock_std > 0.0:
            adjusted_value = adjusted_value * math.exp(
                self.random.gauss(0.0, self.parameters.usage_shock_std)
            )
        usage_event = UsageEvent(
            contribution_id=contribution_identifier,
            gross_value=adjusted_value,
            fee_amount=0.0,
        )
        self.pending_usage_events.append(usage_event)
        self.usage_events.append(
            {
                "step": int(self.current_step),
                "contribution_id": contribution_identifier,
                "user_id": int(user_id) if user_id is not None else None,
                "gross_value": float(adjusted_value),
            }
        )

    def next_contribution_identifier(self) -> str:
        identifier = f"c{self.next_contribution_index}"
        self.next_contribution_index += 1
        return identifier

    def _sample_creator_role(self) -> str:
        supporting_fraction = getattr(self.parameters, "supporting_creator_fraction", 0.0)
        if supporting_fraction < 0.0:
            supporting_fraction = 0.0
        elif supporting_fraction > 1.0:
            supporting_fraction = 1.0
        is_supporting = self.random.random() < supporting_fraction
        if is_supporting and CreatorAgent.SUPPORTING_ROLES:
            roles = tuple(CreatorAgent.SUPPORTING_ROLES)
        else:
            roles = tuple(CreatorAgent.CORE_ROLES)
        if not roles:
            return "developer"
        index = self.random.randrange(len(roles))
        return roles[index]

    def create_initial_population(self) -> None:
        identifier = 0
        for _ in range(self.parameters.creator_count):
            role = self._sample_creator_role()
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
        self.next_agent_identifier = identifier

    def reset_agents_for_new_step(self) -> None:
        for agent in self.agent_by_identifier.values():
            if isinstance(agent, EconomicAgent):
                agent.reset_step_state()

    def _sample_poisson(self, lam: float) -> int:
        if lam <= 0.0:
            return 0
        limit = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= self.random.random()
            if p <= limit:
                return k - 1

    def _mean_roi_for_agents(self, agents: List[EconomicAgent]) -> float:
        rois: List[float] = []
        for agent in agents:
            if not agent.is_active:
                continue
            if getattr(agent, "cumulative_cost", 0.0) <= 0.0:
                continue
            rois.append(agent.current_roi)
        if not rois:
            return 0.0
        return sum(rois) / len(rois)

    def _effective_arrival_rate(
        self,
        base_rate: float,
        sensitivity: float,
        agents: List[EconomicAgent],
    ) -> float:
        if base_rate <= 0.0:
            return 0.0
        mean_roi = self._mean_roi_for_agents(agents)
        multiplier = 1.0 + sensitivity * mean_roi
        if multiplier < 0.0:
            multiplier = 0.0
        return base_rate * multiplier

    def spawn_new_agents(self) -> None:
        creator_lambda = self._effective_arrival_rate(
            self.parameters.creator_arrival_rate,
            self.parameters.creator_arrival_roi_sensitivity,
            self.creators,
        )
        num_creators = self._sample_poisson(creator_lambda)
        for _ in range(num_creators):
            role = self._sample_creator_role()
            skill = self.random.uniform(
                self.parameters.min_creator_skill,
                self.parameters.max_creator_skill,
            )
            creator = CreatorAgent(
                unique_id=self.next_agent_identifier,
                model=self,
                parameters=self.parameters,
                role=role,
                skill=skill,
            )
            self.agent_by_identifier[self.next_agent_identifier] = creator
            self.creators.append(creator)
            self.next_agent_identifier += 1
            self.new_creators_this_step += 1
            identity_cost = self.parameters.identity_creation_cost
            if identity_cost > 0.0:
                creator.cumulative_cost += identity_cost
                creator.wealth -= identity_cost
                self.treasury.balance += identity_cost
                self.treasury.cumulative_inflows += identity_cost

        investor_lambda = self._effective_arrival_rate(
            self.parameters.investor_arrival_rate,
            self.parameters.investor_arrival_roi_sensitivity,
            self.investors,
        )
        num_investors = self._sample_poisson(investor_lambda)
        for _ in range(num_investors):
            investor = InvestorAgent(
                unique_id=self.next_agent_identifier,
                model=self,
                parameters=self.parameters,
                initial_budget=self.parameters.initial_investor_budget,
            )
            self.agent_by_identifier[self.next_agent_identifier] = investor
            self.investors.append(investor)
            self.next_agent_identifier += 1
            self.new_investors_this_step += 1
            identity_cost = self.parameters.identity_creation_cost
            if identity_cost > 0.0:
                investor.cumulative_cost += identity_cost
                investor.wealth -= identity_cost
                self.treasury.balance += identity_cost
                self.treasury.cumulative_inflows += identity_cost

        user_lambda = self._effective_arrival_rate(
            self.parameters.user_arrival_rate,
            self.parameters.user_arrival_roi_sensitivity,
            self.users,
        )
        num_users = self._sample_poisson(user_lambda)
        for _ in range(num_users):
            user = UserAgent(
                unique_id=self.next_agent_identifier,
                model=self,
                parameters=self.parameters,
            )
            self.agent_by_identifier[self.next_agent_identifier] = user
            self.users.append(user)
            self.next_agent_identifier += 1
            self.new_users_this_step += 1
            identity_cost = self.parameters.identity_creation_cost
            if identity_cost > 0.0:
                user.cumulative_cost += identity_cost
                user.wealth -= identity_cost
                self.treasury.balance += identity_cost
                self.treasury.cumulative_inflows += identity_cost

    def _unlock_all_escrows(self) -> None:
        for agent in self.agent_by_identifier.values():
            if hasattr(agent, "unlock_escrowed_rewards"):
                agent.unlock_escrowed_rewards(self.current_step)

    def _decrement_funding_lockups(self, unlock: bool = True) -> None:
        if self.parameters.funding_lockup_period_steps > 0:
            for contribution in self.contributions.values():
                if contribution.contribution_type is not ContributionType.FUNDING:
                    continue
                remaining = getattr(contribution, "lockup_remaining_steps", 0)
                if remaining > 0:
                    contribution.lockup_remaining_steps = remaining - 1
        if unlock:
            self._unlock_all_escrows()

    def _schedule_payout(
        self,
        contribution_identifier: str,
        amount: float,
        payout_type: str | None = None,
        source_contribution_id: str | None = None,
        channel: str | None = None,
    ) -> None:
        if amount <= 0.0:
            return
        lag = self.parameters.payout_lag_steps
        payout_channel = channel if channel is not None else payout_type
        entry = {
            "contribution_id": contribution_identifier,
            "amount": amount,
            "payout_type": payout_type,
            "source_contribution_id": source_contribution_id,
            "channel": payout_channel,
        }
        if lag <= 0:
            self.pay_contribution_owner(
                contribution_identifier,
                amount,
                payout_type,
                source_contribution_id,
                payout_channel,
            )
            return
        self.pending_payouts.append(entry)

    def _credit_reward(
        self,
        contribution_identifier: str,
        amount: float,
        lockup_steps: int = 0,
        payout_type: str | None = None,
        source_contribution_id: str | None = None,
        channel: str | None = None,
    ) -> None:
        if amount <= 0.0:
            return
        contribution = self.contributions.get(contribution_identifier)
        if contribution is None:
            return
        lock_duration = max(0, lockup_steps)
        if lock_duration > 0:
            owner = self.agent_by_identifier.get(contribution.owner_id)
            if owner is None or not getattr(owner, "is_active", False):
                return
            owner.escrowed_rewards.append(
                {
                    "contribution_id": contribution_identifier,
                    "amount": amount,
                    "release_step": lock_duration,
                    "payout_type": payout_type,
                    "source_contribution_id": source_contribution_id,
                    "channel": channel if channel is not None else payout_type,
                }
            )
            return
        self._schedule_payout(
            contribution_identifier,
            amount,
            payout_type,
            source_contribution_id,
            channel,
        )

    def _flush_pending_payouts_if_due(self) -> None:
        lag = self.parameters.payout_lag_steps
        if lag <= 0:
            return
        if self.current_step <= 0:
            return
        if self.current_step % lag != 0:
            return
        for entry in list(self.pending_payouts):
            contribution_identifier = str(entry.get("contribution_id"))
            amount = float(entry.get("amount", 0.0))
            payout_type = entry.get("payout_type")
            source_contribution_id = entry.get("source_contribution_id")
            channel = entry.get("channel")
            self.pay_contribution_owner(
                contribution_identifier,
                amount,
                payout_type if isinstance(payout_type, str) else None,
                source_contribution_id if isinstance(source_contribution_id, str) else None,
                channel if isinstance(channel, str) else None,
            )
        self.pending_payouts.clear()

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
        for event in self.pending_usage_events:
            contribution = self.contributions.get(event.contribution_id)
            if contribution is None:
                continue
            self.total_usage_events_this_step += 1
            status = getattr(contribution, "honor_seal_status", HonorSealStatus.NONE)
            if status in self.usage_events_by_honor_seal_this_step:
                self.usage_events_by_honor_seal_this_step[status] += 1
            self._apply_gas_rewards(event.contribution_id, event.gross_value)
            increment = self.parameters.royalty_accrual_per_usage
            if increment > 0.0:
                contribution.accrued_royalty_value += increment
            if hasattr(contribution, "usage_count"):
                contribution.usage_count += 1
        self.pending_usage_events.clear()

    def _enforce_honor_seal(self) -> None:
        if not getattr(self.parameters, "honor_seal_enabled", False):
            return
        detection_prob = getattr(self.parameters, "honor_seal_fake_detection_prob_per_step", 0.0)
        if detection_prob <= 0.0:
            return
        for contribution in self.contributions.values():
            if contribution.honor_seal_status is not HonorSealStatus.FAKE:
                continue
            if self.random.random() < detection_prob:
                contribution.honor_seal_status = HonorSealStatus.DISHONORED

    def _apply_gas_rewards(self, used_identifier: str, gross_value: float) -> None:
        if gross_value <= 0.0:
            return
        contribution = self.contributions.get(used_identifier)
        if contribution is None:
            return
        gas_share_rate = self.parameters.gas_fee_share_rate
        if gas_share_rate <= 0.0:
            return
        total_fee = gas_share_rate * gross_value
        if total_fee <= 0.0:
            return
        self.total_fee_distributed_this_step += total_fee
        self.cumulative_fee_distributed += total_fee
        treasury_cut = total_fee * self.parameters.treasury_fee_rate
        if treasury_cut > 0.0:
            self.treasury.balance += treasury_cut
            self.treasury.cumulative_inflows += treasury_cut
        gas_reward_pool = total_fee - treasury_cut
        if gas_reward_pool <= 0.0:
            return
        self._distribute_value_pool(
            root_identifier=used_identifier,
            pool_value=gas_reward_pool,
            payout_type="gas",
            channel="gas",
        )

    def _distribute_value_pool(self, root_identifier: str, pool_value: float, payout_type: str, channel: str) -> None:
        if pool_value <= 0.0:
            return
        shares = self.contribution_graph.compute_royalty_shares(
            root_identifier=root_identifier,
            total_value=pool_value,
        )
        if not shares:
            return
        for contribution_id, amount in shares.items():
            contribution = self.contributions.get(contribution_id)
            if contribution is None or amount <= 0.0:
                continue
            lockup_steps = 0
            if contribution.contribution_type is ContributionType.FUNDING:
                lockup_steps = max(0, getattr(contribution, "lockup_remaining_steps", 0))
            self._credit_reward(
                contribution_id,
                amount,
                lockup_steps,
                payout_type=payout_type,
                source_contribution_id=root_identifier,
                channel=channel,
            )

    def _distribute_batched_royalties(self) -> None:
        pending: List[tuple[str, float]] = []
        for contribution_id, contribution in self.contributions.items():
            if contribution.accrued_royalty_value > 0.0:
                pending.append((contribution_id, contribution.accrued_royalty_value))
        if not pending:
            return
        for root_identifier, total_value in pending:
            self._distribute_value_pool(
                root_identifier=root_identifier,
                pool_value=total_value,
                payout_type="royalty",
                channel="royalty",
            )
            contribution = self.contributions[root_identifier]
            contribution.accrued_royalty_value = 0.0

    def _update_agent_satisfaction_and_churn(self) -> None:
        if getattr(self.parameters, "disable_churn", False):
            return
        epsilon = 1e-6
        k = self.parameters.satisfaction_logistic_k
        threshold = self.parameters.satisfaction_churn_threshold
        roi_window = self.parameters.roi_churn_window
        noise_std = self.parameters.satisfaction_noise_std
        rep_decay = self.parameters.reputation_decay_per_step
        rep_penalty = self.parameters.reputation_penalty_for_churn
        for agent in self.agent_by_identifier.values():
            if not isinstance(agent, EconomicAgent):
                continue
            if rep_decay > 0.0:
                agent.reputation_score = max(0.0, agent.reputation_score - rep_decay)
            was_active = agent.is_active
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
            if was_active and not agent.is_active and rep_penalty > 0.0:
                agent.reputation_score = max(0.0, agent.reputation_score - rep_penalty)

    def _handle_own_share_with_frictions(
        self,
        contribution_identifier: str,
        amount: float,
    ) -> None:
        if amount <= 0.0:
            return
        contribution = self.contributions.get(contribution_identifier)
        if contribution is None:
            return
        lockup_steps = 0
        if contribution.contribution_type is ContributionType.FUNDING:
            lockup_steps = max(0, getattr(contribution, "lockup_remaining_steps", 0))
        self._credit_reward(contribution_identifier, amount, lockup_steps)

    def distribute_fee_pool_for_event(
        self,
        event: UsageEvent,
        fee_pool: float,
        payout_type: str = "gas",
        channel: str | None = None,
    ) -> None:
        if fee_pool <= 0.0:
            return
        self._distribute_value_pool(
            event.contribution_id,
            fee_pool,
            payout_type,
            channel if channel is not None else payout_type,
        )

    def _infer_role_for_agent(self, agent: EconomicAgent) -> str | None:
        if isinstance(agent, CreatorAgent):
            return "creator"
        if isinstance(agent, InvestorAgent):
            return "investor"
        if isinstance(agent, UserAgent):
            return "user"
        return None

    def pay_contribution_owner(
        self,
        contribution_identifier: str,
        amount: float,
        payout_type: str | None = None,
        source_contribution_id: str | None = None,
        channel: str | None = None,
    ) -> None:
        if amount <= 0.0:
            return
        contribution = self.contributions.get(contribution_identifier)
        if contribution is None:
            return
        owner_identifier = contribution.owner_id
        agent = self.agent_by_identifier.get(owner_identifier)
        if agent is None or not agent.is_active:
            return
        gated_amount = amount
        slashed_amount = 0.0
        if isinstance(agent, EconomicAgent):
            threshold = self.parameters.min_reputation_for_full_rewards
            if threshold > 0.0:
                reputation = getattr(agent, "reputation_score", 1.0)
                if reputation < threshold:
                    gating_factor = max(0.0, reputation / threshold)
                else:
                    gating_factor = 1.0
                gated_amount = amount * gating_factor
                slashed_amount = amount - gated_amount
        if slashed_amount > 0.0:
            self.treasury.balance += slashed_amount
            self.treasury.cumulative_inflows += slashed_amount
        if gated_amount > 0.0:
            if isinstance(agent, EconomicAgent):
                agent.record_income(gated_amount)
                gain = self.parameters.reputation_gain_per_usage
                if gain > 0.0:
                    agent.reputation_score = min(1.0, agent.reputation_score + gain)
            else:
                agent.receive_income(gated_amount)
        contribution_type = contribution.contribution_type
        self.reward_paid_by_type_this_step[contribution_type] += gated_amount
        self.total_reward_paid_by_type[contribution_type] += gated_amount
        role_name = self._infer_role_for_agent(agent)
        if role_name is None:
            return
        self.reward_paid_by_role_this_step[role_name] += gated_amount
        self.total_reward_paid_by_role[role_name] += gated_amount
        if payout_type is None or source_contribution_id is None:
            return
        if gated_amount <= 0.0:
            return
        payout_channel = channel if channel is not None else payout_type
        self._record_reward_event(
            step=self.current_step,
            payout_type=payout_type,
            amount=gated_amount,
            recipient_id=owner_identifier,
            source_contribution_id=source_contribution_id,
            channel=payout_channel,
        )


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
    total_income = (
        total_income_creators(model)
        + total_income_investors(model)
        + total_income_users(model)
    )
    if total_income <= 0.0:
        return 0.0
    return total_income_creators(model) / total_income


def role_income_share_investors(model: BitRewardsModel) -> float:
    total_income = (
        total_income_creators(model)
        + total_income_investors(model)
        + total_income_users(model)
    )
    if total_income <= 0.0:
        return 0.0
    return total_income_investors(model) / total_income


def role_income_share_users(model: BitRewardsModel) -> float:
    total_income = (
        total_income_creators(model)
        + total_income_investors(model)
        + total_income_users(model)
    )
    if total_income <= 0.0:
        return 0.0
    return total_income_users(model) / total_income


def treasury_balance(model: BitRewardsModel) -> float:
    return model.treasury.balance


def total_funding_invested(model: BitRewardsModel) -> float:
    return model.total_funding_invested


def total_wealth(model: BitRewardsModel) -> float:
    return model._compute_total_wealth()


def new_creators_this_step(model: BitRewardsModel) -> int:
    return model.new_creators_this_step


def new_investors_this_step(model: BitRewardsModel) -> int:
    return model.new_investors_this_step


def new_users_this_step(model: BitRewardsModel) -> int:
    return model.new_users_this_step


def locked_funding_positions(model: BitRewardsModel) -> int:
    count = 0
    for contribution in model.contributions.values():
        if (
            contribution.contribution_type is ContributionType.FUNDING
            and getattr(contribution, "lockup_remaining_steps", 0) > 0
        ):
            count += 1
    return count


def honor_seal_honest_contribution_count(model: BitRewardsModel) -> int:
    return sum(1 for c in model.contributions.values() if c.honor_seal_status is HonorSealStatus.HONEST)


def honor_seal_fake_contribution_count(model: BitRewardsModel) -> int:
    return sum(1 for c in model.contributions.values() if c.honor_seal_status is HonorSealStatus.FAKE)


def honor_seal_dishonored_contribution_count(model: BitRewardsModel) -> int:
    return sum(1 for c in model.contributions.values() if c.honor_seal_status is HonorSealStatus.DISHONORED)


def honor_seal_sealed_usage_share(model: BitRewardsModel) -> float:
    sealed = model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.HONEST, 0) + model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.FAKE, 0)
    total = sealed + model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.NONE, 0) + model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.DISHONORED, 0)
    if total <= 0:
        return 0.0
    return sealed / total


def honor_seal_dishonored_usage_share(model: BitRewardsModel) -> float:
    total = model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.HONEST, 0) + model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.FAKE, 0) + model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.NONE, 0) + model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.DISHONORED, 0)
    if total <= 0:
        return 0.0
    dishonored = model.usage_events_by_honor_seal_this_step.get(HonorSealStatus.DISHONORED, 0)
    return dishonored / total
