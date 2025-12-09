from __future__ import annotations

from bitrewards_abm.domain.entities import ContributionType, HonorSealStatus
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def build_model_with_honor_seal() -> BitRewardsModel:
    params = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        honor_seal_enabled=True,
        honor_seal_initial_adoption_rate=1.0,
        honor_seal_mint_cost_btc=0.0,
        honor_seal_fake_rate=0.0,
        creator_base_contribution_probability=0.0,
        max_steps=1,
    )
    return BitRewardsModel(parameters=params)


def test_root_contribution_mints_honor_seal() -> None:
    model = build_model_with_honor_seal()
    creator = model.creators[0]
    identifier = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    contribution = model.contributions[identifier]
    assert contribution.honor_seal_status is HonorSealStatus.HONEST
    assert contribution.honor_seal_mint_step == model.current_step


def test_fake_seal_is_detected() -> None:
    params = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        honor_seal_enabled=True,
        honor_seal_initial_adoption_rate=0.0,
        honor_seal_fake_detection_prob_per_step=1.0,
        creator_base_contribution_probability=0.0,
        max_steps=1,
    )
    model = BitRewardsModel(parameters=params)
    creator = model.creators[0]
    identifier = model.register_creator_contribution(
        creator=creator,
        contribution_type=ContributionType.CORE_RESEARCH,
        quality=1.0,
        parent_identifier=None,
    )
    contribution = model.contributions[identifier]
    contribution.honor_seal_status = HonorSealStatus.FAKE
    model._enforce_honor_seal()
    assert contribution.honor_seal_status is HonorSealStatus.DISHONORED
