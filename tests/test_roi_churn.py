from __future__ import annotations

import math

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.agents import CreatorAgent, InvestorAgent
from bitrewards_abm.simulation.model import BitRewardsModel


def build_model_with_single_investor() -> BitRewardsModel:
    parameters = SimulationParameters(
        creator_count=0,
        investor_count=1,
        user_count=0,
        max_steps=10,
        aspiration_income_per_step=0.01,
        satisfaction_logistic_k=1.5,
        satisfaction_churn_threshold=0.2,
        satisfaction_churn_window=15,
        investor_roi_exit_threshold=-0.1,
        creator_roi_exit_threshold=-0.1,
        user_roi_exit_threshold=-0.1,
        roi_churn_window=3,
        satisfaction_noise_std=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    assert len(model.investors) == 1
    return model


def test_investor_with_negative_roi_eventually_churns() -> None:
    model = build_model_with_single_investor()
    investor: InvestorAgent = model.investors[0]
    investor.cumulative_cost = 100.0
    investor.cumulative_income = 0.0
    roi = investor.current_roi
    assert math.isclose(roi, -1.0, rel_tol=1e-6, abs_tol=1e-9)
    for _ in range(model.parameters.roi_churn_window):
        model._update_agent_satisfaction_and_churn()
    assert investor.is_active is False


def test_investor_with_positive_roi_does_not_churn() -> None:
    model = build_model_with_single_investor()
    investor: InvestorAgent = model.investors[0]
    investor.cumulative_cost = 100.0
    investor.cumulative_income = 150.0
    roi = investor.current_roi
    assert math.isclose(roi, 0.5, rel_tol=1e-6, abs_tol=1e-9)
    for _ in range(10 * model.parameters.roi_churn_window):
        model._update_agent_satisfaction_and_churn()
    assert investor.is_active is True


def build_model_with_single_creator() -> BitRewardsModel:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        max_steps=10,
        aspiration_income_per_step=0.01,
        satisfaction_logistic_k=1.5,
        satisfaction_churn_threshold=0.2,
        satisfaction_churn_window=15,
        creator_roi_exit_threshold=-0.1,
        investor_roi_exit_threshold=-0.1,
        user_roi_exit_threshold=-0.1,
        roi_churn_window=3,
        satisfaction_noise_std=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    assert len(model.creators) == 1
    return model


def test_creator_with_negative_roi_eventually_churns() -> None:
    model = build_model_with_single_creator()
    creator: CreatorAgent = model.creators[0]
    creator.cumulative_cost = 100.0
    creator.cumulative_income = 0.0
    for _ in range(model.parameters.roi_churn_window):
        model._update_agent_satisfaction_and_churn()
    assert creator.is_active is False
