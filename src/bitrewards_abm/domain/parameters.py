from __future__ import annotations

from dataclasses import dataclass

from bitrewards_abm.domain.entities import ContributionType


@dataclass
class SimulationParameters:
    creator_count: int = 10
    investor_count: int = 3
    user_count: int = 20
    max_steps: int = 200
    gas_fee_share_rate: float = 0.004
    tracing_accuracy: float = 0.8
    tracing_false_positive_rate: float = 0.05
    creator_base_contribution_probability: float = 0.3
    quality_noise_scale: float = 0.1
    user_usage_probability: float = 0.6
    base_gross_value: float = 1.0
    min_creator_skill: float = 0.3
    max_creator_skill: float = 0.9
    initial_investor_budget: float = 100.0
    initial_agent_satisfaction: float = 1.0
    supporting_creator_fraction: float = 0.3
    funding_royalty_min: float = 0.01
    funding_royalty_max: float = 0.05
    funding_min_amount: float = 5.0
    funding_max_amount: float = 50.0
    royalty_accrual_per_usage: float = 1.0
    royalty_batch_interval: int = 30

    default_derivative_split: float = 0.5
    supporting_derivative_split: float = 0.5

    core_research_base_royalty_share: float = 1.0
    funding_base_royalty_share: float = 1.0
    supporting_base_royalty_share: float = 1.0

    funding_split_fraction: float = 0.015
    funding_contribution_cost: float = 10.0
    investor_max_funding_per_step: int = 1
    investor_min_target_quality: float = 0.5
    aspiration_income_per_step: float = 0.01
    satisfaction_logistic_k: float = 1.5
    satisfaction_churn_threshold: float = 0.15
    satisfaction_churn_window: int = 15
    treasury_fee_rate: float = 0.0
    treasury_funding_rate: float = 0.0
    creator_roi_exit_threshold: float = -0.2
    investor_roi_exit_threshold: float = -0.2
    user_roi_exit_threshold: float = -0.2
    roi_churn_window: int = 10
    satisfaction_noise_std: float = 0.0
    creator_arrival_rate: float = 0.0
    investor_arrival_rate: float = 0.0
    user_arrival_rate: float = 0.0
    creator_arrival_roi_sensitivity: float = 0.0
    investor_arrival_roi_sensitivity: float = 0.0
    user_arrival_roi_sensitivity: float = 0.0
    user_mean_usage_rate: float = 1.0
    usage_shock_std: float = 0.0
    funding_lockup_period_steps: int = 0
    payout_lag_steps: int = 0
    min_reputation_for_full_rewards: float = 0.0
    identity_creation_cost: float = 0.0
    reputation_gain_per_usage: float = 0.0
    reputation_penalty_for_churn: float = 0.0
    reputation_decay_per_step: float = 0.0
    creator_contribution_cost: float = 0.0
    disable_churn: bool = False
    honor_seal_enabled: bool = False
    honor_seal_initial_adoption_rate: float = 0.0
    honor_seal_mint_cost_btc: float = 0.0
    honor_seal_demand_multiplier: float = 1.0
    honor_seal_unsealed_penalty_multiplier: float = 1.0
    honor_seal_fake_rate: float = 0.0
    honor_seal_fake_detection_prob_per_step: float = 0.0
    honor_seal_enforcement_ramp_steps: int = 0
    honor_seal_dishonored_penalty_multiplier: float = 0.5
    investor_rewards_structure_enabled: bool = True
    investor_return_cap_multiple: float = 3.0
    investor_post_cap_payout_fraction: float = 0.25
    royalty_mode: str = "single_path"
    royalty_keep_fraction: float = 0.5

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

    def treasury_cut_from_fee(self, fee_amount: float) -> float:
        return fee_amount * self.treasury_fee_rate
