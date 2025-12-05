from __future__ import annotations

import math

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.agents import EconomicAgent
from bitrewards_abm.simulation.model import BitRewardsModel


def test_token_supply_constant_without_inflation_or_fees() -> None:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        max_steps=5,
        gas_fee_share_rate=0.0,
        token_initial_supply=0.0,
        token_inflation_rate=0.0,
        token_buyback_burn_rate=0.0,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    initial_supply = model.token_state.total_supply
    for _ in range(5):
        model.step()
    assert math.isclose(
        model.token_state.total_supply,
        initial_supply,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )


def test_token_supply_grows_with_inflation() -> None:
    parameters = SimulationParameters(
        creator_count=0,
        investor_count=0,
        user_count=0,
        max_steps=5,
        gas_fee_share_rate=0.0,
        token_initial_supply=100.0,
        token_inflation_rate=0.1,
        token_buyback_burn_rate=0.0,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    initial_supply = model.token_state.total_supply
    steps = 3
    for _ in range(steps):
        model.step()
    expected_supply = initial_supply * ((1.0 + parameters.token_inflation_rate) ** steps)
    assert math.isclose(
        model.token_state.total_supply,
        expected_supply,
        rel_tol=1e-6,
        abs_tol=1e-6,
    )


def test_holding_time_updates_when_balance_changes() -> None:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        max_steps=3,
        gas_fee_share_rate=0.0,
        creator_base_contribution_probability=0.0,
        user_usage_probability=0.0,
    )
    model = BitRewardsModel(parameters=parameters)
    creator: EconomicAgent = model.creators[0]
    model.current_step = 1
    creator.record_income(10.0)
    model._update_token_holding_times()
    model.current_step = 2
    creator.record_cost(5.0)
    model._update_token_holding_times()
    assert creator.holding_time_ema > 0.0
    assert model.token_state.mean_holding_time_steps >= creator.holding_time_ema - 1e-9
