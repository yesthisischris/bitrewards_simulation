from __future__ import annotations

import math

from bitrewards_abm.domain.entities import Contribution, ContributionType
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.agents import CreatorAgent
from bitrewards_abm.simulation.model import BitRewardsModel


def build_model_for_sybil_gating() -> BitRewardsModel:
    params = SimulationParameters(
        creator_count=0,
        investor_count=0,
        user_count=0,
        max_steps=1,
        min_reputation_for_full_rewards=1.0,
        reputation_gain_per_usage=0.0,
        reputation_decay_per_step=0.0,
        reputation_penalty_for_churn=0.0,
    )
    return BitRewardsModel(parameters=params)


def test_low_reputation_agent_gets_less_and_difference_goes_to_treasury() -> None:
    model = build_model_for_sybil_gating()
    high_rep = CreatorAgent(
        unique_id=1,
        model=model,
        parameters=model.parameters,
        role="developer",
        skill=0.8,
    )
    low_rep = CreatorAgent(
        unique_id=2,
        model=model,
        parameters=model.parameters,
        role="developer",
        skill=0.8,
    )
    high_rep.reputation_score = 1.0
    low_rep.reputation_score = 0.5
    model.agent_by_identifier[1] = high_rep
    model.agent_by_identifier[2] = low_rep
    model.creators.extend([high_rep, low_rep])
    c_high = Contribution(
        contribution_id="c-high",
        project_id=None,
        owner_id=high_rep.unique_id,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parents=[],
    )
    c_low = Contribution(
        contribution_id="c-low",
        project_id=None,
        owner_id=low_rep.unique_id,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parents=[],
    )
    model.contributions["c-high"] = c_high
    model.contributions["c-low"] = c_low
    nominal_amount = 100.0
    model.pay_contribution_owner("c-high", nominal_amount)
    model.pay_contribution_owner("c-low", nominal_amount)
    assert math.isclose(high_rep.wealth, 100.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(low_rep.wealth, 50.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(model.treasury.balance, 50.0, rel_tol=1e-9, abs_tol=1e-9)
