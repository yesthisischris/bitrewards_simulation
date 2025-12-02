from __future__ import annotations

from dataclasses import dataclass


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
    funding_split_fraction: float = 0.02
    funding_contribution_cost: float = 10.0
    investor_max_funding_per_step: int = 1
    investor_min_target_quality: float = 0.5
    aspiration_income_per_step: float = 0.01
    satisfaction_logistic_k: float = 1.5
    satisfaction_churn_threshold: float = 0.15
    satisfaction_churn_window: int = 15
