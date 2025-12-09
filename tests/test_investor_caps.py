from __future__ import annotations

import math

from bitrewards_abm.domain.entities import ContributionType
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def test_investor_cap_and_tail_redirects_to_treasury() -> None:
    params = SimulationParameters(
        creator_count=1,
        investor_count=1,
        user_count=0,
        gas_fee_share_rate=1.0,
        funding_min_amount=10.0,
        funding_max_amount=10.0,
        funding_royalty_min=1.0,
        funding_royalty_max=1.0,
        investor_return_cap_multiple=1.0,
        investor_post_cap_payout_fraction=0.25,
        investor_rewards_structure_enabled=True,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
        max_steps=1,
    )
    model = BitRewardsModel(parameters=params)
    creator = model.creators[0]
    investor = model.investors[0]
    core_id = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    funding_id = model.register_funding_contribution(
        investor=investor,
        target_identifier=core_id,
    )
    assert funding_id is not None
    model.reset_step_internal_state()
    model.register_usage_event(contribution_identifier=core_id, gross_value=100.0)
    model.distribute_usage_event_fees()
    funding = model.contributions[funding_id]
    expected_investor = 10.0 + (100.0 - 10.0) * 0.25
    expected_redirect = 100.0 - expected_investor
    assert math.isclose(funding.funding_cumulative_rewards, expected_investor, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(investor.wealth, expected_investor, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(model.treasury.balance, expected_redirect, rel_tol=1e-9, abs_tol=1e-9)


def test_investor_cap_disabled_behaves_like_baseline() -> None:
    params = SimulationParameters(
        creator_count=1,
        investor_count=1,
        user_count=0,
        gas_fee_share_rate=1.0,
        funding_min_amount=10.0,
        funding_max_amount=10.0,
        funding_royalty_min=1.0,
        funding_royalty_max=1.0,
        investor_return_cap_multiple=0.0,
        investor_post_cap_payout_fraction=1.0,
        investor_rewards_structure_enabled=True,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
        max_steps=1,
    )
    model = BitRewardsModel(parameters=params)
    creator = model.creators[0]
    investor = model.investors[0]
    core_id = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    funding_id = model.register_funding_contribution(
        investor=investor,
        target_identifier=core_id,
    )
    assert funding_id is not None
    model.reset_step_internal_state()
    model.register_usage_event(contribution_identifier=core_id, gross_value=100.0)
    model.distribute_usage_event_fees()
    funding = model.contributions[funding_id]
    assert math.isclose(funding.funding_cumulative_rewards, 100.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(investor.wealth, 100.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(model.treasury.balance, 0.0, rel_tol=1e-9, abs_tol=1e-9)
