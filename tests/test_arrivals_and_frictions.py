from __future__ import annotations

import math

from bitrewards_abm.domain.entities import ContributionType
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def test_creator_arrivals_are_positive_with_nonzero_lambda() -> None:
    parameters = SimulationParameters(
        creator_count=0,
        investor_count=0,
        user_count=0,
        max_steps=100,
        creator_arrival_rate=0.5,
        creator_arrival_roi_sensitivity=0.0,
        investor_arrival_rate=0.0,
        user_arrival_rate=0.0,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    total_new_creators = 0
    steps = 50
    for _ in range(steps):
        model.step()
        total_new_creators += model.new_creators_this_step
    average_new_per_step = total_new_creators / steps
    assert average_new_per_step > 0.0


def test_funding_lockup_blocks_investor_royalties_until_expired() -> None:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=1,
        user_count=0,
        max_steps=10,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
        funding_contribution_cost=10.0,
        initial_investor_budget=10.0,
        investor_max_funding_per_step=1,
        funding_lockup_period_steps=3,
        gas_fee_share_rate=0.1,
        core_research_base_royalty_share=1.0,
        treasury_fee_rate=0.0,
        payout_lag_steps=0,
    )
    model = BitRewardsModel(parameters=parameters)
    creator = model.creators[0]
    investor = model.investors[0]
    contribution_id = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    investor.step()
    investor_wealth_start = investor.wealth
    for _ in range(parameters.funding_lockup_period_steps):
        model.reset_step_internal_state()
        model.register_usage_event(contribution_identifier=contribution_id, gross_value=100.0)
        model.distribute_usage_event_fees()
        model._decrement_funding_lockups()
    assert math.isclose(investor.wealth, investor_wealth_start, rel_tol=1e-9, abs_tol=1e-9)
    model.reset_step_internal_state()
    model.register_usage_event(contribution_identifier=contribution_id, gross_value=100.0)
    model.distribute_usage_event_fees()
    model._decrement_funding_lockups()
    assert investor.wealth > investor_wealth_start


def test_payout_lag_delays_income_until_flush() -> None:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        max_steps=10,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
        gas_fee_share_rate=0.2,
        core_research_base_royalty_share=1.0,
        payout_lag_steps=2,
        treasury_fee_rate=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    creator = model.creators[0]
    contribution_id = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    total_fee = parameters.base_gross_value * parameters.gas_fee_share_rate * parameters.core_research_base_royalty_share
    for step in range(1, 4):
        model.current_step = step
        model.reset_step_internal_state()
        model.register_usage_event(contribution_identifier=contribution_id, gross_value=parameters.base_gross_value)
        model.distribute_usage_event_fees()
        model._flush_pending_payouts_if_due()
        if step == 1:
            assert math.isclose(creator.wealth, 0.0, rel_tol=1e-9, abs_tol=1e-9)
        if step == 2:
            assert math.isclose(creator.wealth, total_fee * 2, rel_tol=1e-9, abs_tol=1e-9)
