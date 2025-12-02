from __future__ import annotations

import math

from bitrewards_abm.domain.entities import ContributionType
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def build_parameters_for_reward_tests(
    *,
    derivative_split: float,
    supporting_split: float,
    funding_split: float,
) -> SimulationParameters:
    return SimulationParameters(
        creator_count=1,
        investor_count=1,
        user_count=0,
        gas_fee_share_rate=1.0,
        tracing_accuracy=1.0,
        default_derivative_split=derivative_split,
        supporting_derivative_split=supporting_split,
        core_research_base_royalty_share=1.0,
        supporting_base_royalty_share=1.0,
        funding_base_royalty_share=1.0,
        funding_split_fraction=funding_split,
    )


def build_model_for_reward_tests(
    derivative_split: float,
    supporting_split: float,
    funding_split: float,
) -> BitRewardsModel:
    parameters = build_parameters_for_reward_tests(
        derivative_split=derivative_split,
        supporting_split=supporting_split,
        funding_split=funding_split,
    )
    model = BitRewardsModel(parameters)
    return model


def test_total_rewards_equal_fee_pool_in_two_node_chain() -> None:
    model = build_model_for_reward_tests(
        derivative_split=0.5,
        supporting_split=0.5,
        funding_split=0.25,
    )
    model.reset_step_internal_state()
    creator = model.creators[0]

    root_identifier = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    child_identifier = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=root_identifier,
    )

    model.register_usage_event(contribution_identifier=child_identifier, gross_value=1.0)
    model.distribute_usage_event_fees()

    total_fee = model.total_fee_distributed_this_step
    total_income = sum(agent.current_income for agent in model.agent_by_identifier.values())

    assert math.isclose(total_fee, 1.0, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(total_income, total_fee, rel_tol=1e-9, abs_tol=1e-12)


def test_reward_fractions_by_type_follow_configured_splits() -> None:
    supporting_split = 0.5
    funding_split = 0.25
    model = build_model_for_reward_tests(
        derivative_split=0.0,
        supporting_split=supporting_split,
        funding_split=funding_split,
    )

    creator = model.creators[0]
    investor = model.investors[0]

    model.reset_step_internal_state()

    core_identifier = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    supporting_identifier = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.SUPPORTING,
        quality=1.0,
        parent_identifier=core_identifier,
    )
    funding_identifier = model.register_funding_contribution(
        investor=investor,
        target_identifier=core_identifier,
    )
    assert funding_identifier is not None

    model.reset_step_internal_state()

    model.register_usage_event(contribution_identifier=supporting_identifier, gross_value=1.0)
    model.distribute_usage_event_fees()

    expected_total_fee = 1.0
    expected_supporting = expected_total_fee * (1.0 - supporting_split)
    expected_core = expected_total_fee * supporting_split * (1.0 - funding_split)
    expected_funding = expected_total_fee * supporting_split * funding_split

    rewards_by_type = model.reward_paid_by_type_this_step
    actual_supporting = rewards_by_type[ContributionType.SUPPORTING]
    actual_core = rewards_by_type[ContributionType.CORE_RESEARCH]
    actual_funding = rewards_by_type[ContributionType.FUNDING]

    assert math.isclose(
        model.total_fee_distributed_this_step,
        expected_total_fee,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )
    assert math.isclose(actual_supporting, expected_supporting, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(actual_core, expected_core, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(actual_funding, expected_funding, rel_tol=1e-9, abs_tol=1e-12)


def test_supporting_split_changes_reallocate_rewards_across_types() -> None:
    low_supporting_split = 0.25
    high_supporting_split = 0.75
    funding_split = 0.2

    def run_single_supporting_event(supporting_split: float) -> dict[ContributionType, float]:
        model = build_model_for_reward_tests(
            derivative_split=0.0,
            supporting_split=supporting_split,
            funding_split=funding_split,
        )
        creator = model.creators[0]
        investor = model.investors[0]

        model.reset_step_internal_state()

        core_identifier = model.register_creator_contribution(
            creator=creator,
            contribution_type=ContributionType.CORE_RESEARCH,
            quality=1.0,
            parent_identifier=None,
        )
        supporting_identifier = model.register_creator_contribution(
            creator=creator,
            contribution_type=ContributionType.SUPPORTING,
            quality=1.0,
            parent_identifier=core_identifier,
        )
        funding_identifier = model.register_funding_contribution(
            investor=investor,
            target_identifier=core_identifier,
        )
        assert funding_identifier is not None

        model.reset_step_internal_state()

        model.register_usage_event(contribution_identifier=supporting_identifier, gross_value=1.0)
        model.distribute_usage_event_fees()

        return dict(model.reward_paid_by_type_this_step)

    low_rewards = run_single_supporting_event(low_supporting_split)
    high_rewards = run_single_supporting_event(high_supporting_split)

    assert math.isclose(
        sum(low_rewards.values()),
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )
    assert math.isclose(
        sum(high_rewards.values()),
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )

    assert high_rewards[ContributionType.SUPPORTING] < low_rewards[ContributionType.SUPPORTING]
    assert high_rewards[ContributionType.CORE_RESEARCH] > low_rewards[ContributionType.CORE_RESEARCH]
    assert high_rewards[ContributionType.FUNDING] > low_rewards[ContributionType.FUNDING]
