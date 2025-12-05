from __future__ import annotations

import math

from bitrewards_abm.domain.entities import ContributionType
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def build_model_for_funding_test() -> BitRewardsModel:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=1,
        user_count=0,
        max_steps=1,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
        funding_contribution_cost=100.0,
        initial_investor_budget=100.0,
        investor_max_funding_per_step=1,
        treasury_funding_rate=0.25,
        gas_fee_share_rate=0.0,
    )
    return BitRewardsModel(parameters=parameters)


def test_funding_reallocates_capital_without_destruction() -> None:
    model = build_model_for_funding_test()
    creator = model.creators[0]
    investor = model.investors[0]

    contribution_id = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    assert contribution_id is not None

    initial_total_wealth = model._compute_total_wealth()
    assert math.isclose(initial_total_wealth, investor.budget, rel_tol=1e-9, abs_tol=1e-12)

    model.reset_step_internal_state()
    investor.step()

    assert math.isclose(investor.budget, 0.0, rel_tol=1e-9, abs_tol=1e-12)

    expected_creator_amount = 100.0 * (1.0 - model.parameters.treasury_funding_rate)
    expected_treasury_amount = 100.0 * model.parameters.treasury_funding_rate

    assert math.isclose(
        creator.wealth,
        expected_creator_amount,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )
    assert math.isclose(
        model.treasury.balance,
        expected_treasury_amount,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )

    final_total_wealth = model._compute_total_wealth()
    assert math.isclose(
        final_total_wealth,
        initial_total_wealth,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )


def build_model_for_usage_test() -> BitRewardsModel:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        max_steps=1,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
        core_research_base_royalty_share=1.0,
        gas_fee_share_rate=0.1,
        treasury_fee_rate=0.2,
    )
    return BitRewardsModel(parameters=parameters)


def test_usage_event_mints_fee_and_splits_between_treasury_and_creator() -> None:
    model = build_model_for_usage_test()
    creator = model.creators[0]

    contribution_id = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    assert contribution_id is not None

    initial_total_wealth = model._compute_total_wealth()

    gross_value = 100.0
    model.reset_step_internal_state()
    model.register_usage_event(contribution_identifier=contribution_id, gross_value=gross_value)
    model.distribute_usage_event_fees()

    total_fee = (
        gross_value
        * model.parameters.gas_fee_share_rate
        * model.parameters.core_research_base_royalty_share
    )
    treasury_cut = total_fee * model.parameters.treasury_fee_rate
    royalty_pool = total_fee - treasury_cut

    assert math.isclose(
        model.treasury.balance,
        treasury_cut,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )
    assert math.isclose(
        creator.wealth,
        royalty_pool,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )

    final_total_wealth = model._compute_total_wealth()
    assert math.isclose(
        final_total_wealth,
        initial_total_wealth + total_fee,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )
