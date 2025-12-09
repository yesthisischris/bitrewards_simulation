from __future__ import annotations

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def test_disable_churn_keeps_agents_active() -> None:
    parameters = SimulationParameters(
        creator_count=1,
        investor_count=0,
        user_count=0,
        disable_churn=True,
        satisfaction_churn_threshold=0.0,
    )
    model = BitRewardsModel(parameters)
    creator = model.creators[0]
    creator.is_active = True
    creator.low_satisfaction_streak = 100
    model._update_agent_satisfaction_and_churn()
    assert creator.is_active
