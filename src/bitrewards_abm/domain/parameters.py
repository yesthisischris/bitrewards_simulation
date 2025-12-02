from __future__ import annotations

from dataclasses import dataclass

from bitrewards_abm.domain.entities import ContributionType


@dataclass
class SimulationParameters:
    creator_count: int = 10
    investor_count: int = 3
    user_count: int = 20
    max_steps: int = 200
    gas_fee_share_rate: float = 0.005
    tracing_accuracy: float = 0.8
    creator_base_contribution_probability: float = 0.3
    quality_noise_scale: float = 0.1
    user_usage_probability: float = 0.6
    base_gross_value: float = 1.0
    min_creator_skill: float = 0.3
    max_creator_skill: float = 0.9
    initial_investor_budget: float = 100.0
    initial_agent_satisfaction: float = 1.0

    default_derivative_split: float = 0.5
    supporting_derivative_split: float = 0.25

    core_research_base_royalty_share: float = 1.0
    funding_base_royalty_share: float = 1.0
    supporting_base_royalty_share: float = 1.0

    funding_split_fraction: float = 0.02
    funding_contribution_cost: float = 10.0
    investor_max_funding_per_step: int = 1
    investor_min_target_quality: float = 0.5
    aspiration_income_per_step: float = 0.01
    satisfaction_logistic_k: float = 1.5
    satisfaction_churn_threshold: float = 0.15
    satisfaction_churn_window: int = 15

    def get_base_royalty_share_for(self, contribution_type: ContributionType) -> float:
        if contribution_type is ContributionType.CORE_RESEARCH:
            return self.core_research_base_royalty_share
        if contribution_type is ContributionType.FUNDING:
            return self.funding_base_royalty_share
        if contribution_type is ContributionType.SUPPORTING:
            return self.supporting_base_royalty_share
        return self.core_research_base_royalty_share

    def get_derivative_split_for(self, contribution_type: ContributionType) -> float:
        if contribution_type is ContributionType.SUPPORTING:
            return self.supporting_derivative_split
        if contribution_type is ContributionType.FUNDING:
            return 0.0
        return self.default_derivative_split

    def get_funding_split_for_target_type(self, contribution_type: ContributionType) -> float:
        return self.funding_split_fraction
