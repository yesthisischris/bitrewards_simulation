from __future__ import annotations

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def run_single_simulation_step_sequence() -> None:
    parameters = SimulationParameters()
    model = BitRewardsModel(parameters)
    for _ in range(parameters.max_steps):
        model.step()
    model_dataframe = model.datacollector.get_model_vars_dataframe()
    print(model_dataframe.tail())


if __name__ == "__main__":
    run_single_simulation_step_sequence()
