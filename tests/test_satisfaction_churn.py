from __future__ import annotations

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def build_model(
    aspiration: float = 1.0,
    threshold: float = 0.6,
    window: int = 2,
    k: float = 5.0,
) -> BitRewardsModel:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        max_steps=1,
        aspiration_income_per_step=aspiration,
        satisfaction_churn_threshold=threshold,
        satisfaction_churn_window=window,
        satisfaction_logistic_k=k,
        roi_churn_window=window,
        creator_roi_exit_threshold=-0.1,
        investor_roi_exit_threshold=-0.1,
        user_roi_exit_threshold=-0.1,
        satisfaction_noise_std=0.0,
    )
    return BitRewardsModel(parameters)


def test_agent_churns_after_consecutive_low_satisfaction() -> None:
    model = build_model()
    creator = model.creators[0]

    creator.cumulative_cost = 1.0
    creator.cumulative_income = 0.0
    model._update_agent_satisfaction_and_churn()
    assert creator.is_active
    assert creator.low_satisfaction_streak == 1

    creator.cumulative_cost = 1.0
    creator.cumulative_income = 0.0
    model._update_agent_satisfaction_and_churn()
    assert not creator.is_active


def test_satisfaction_recovery_resets_streak() -> None:
    model = build_model()
    creator = model.creators[0]

    creator.cumulative_cost = 1.0
    creator.cumulative_income = 0.0
    model._update_agent_satisfaction_and_churn()
    assert creator.low_satisfaction_streak == 1

    creator.cumulative_income = 5.0
    model._update_agent_satisfaction_and_churn()
    assert creator.is_active
    assert creator.low_satisfaction_streak == 0
