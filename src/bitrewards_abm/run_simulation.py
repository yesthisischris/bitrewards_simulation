from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.experiment.config import load_experiment_configuration
from bitrewards_abm.simulation.model import BitRewardsModel


def build_parameters_from_args(args: argparse.Namespace) -> Tuple[SimulationParameters, int | None]:
    if args.config is None:
        parameters = SimulationParameters()
        if args.steps is not None:
            parameters.max_steps = args.steps
        seed_value = args.seed
        return parameters, seed_value

    config_path = Path(args.config)
    parameters_from_config, experiment_config = load_experiment_configuration(config_path)
    if args.steps is not None:
        parameters_from_config.max_steps = args.steps
    seed_value = args.seed
    if seed_value is None:
        seed_value = experiment_config.random_seed_base
    return parameters_from_config, seed_value


def run_single_simulation(parameters: SimulationParameters, seed: int | None = None) -> None:
    model = BitRewardsModel(parameters)
    if seed is not None:
        model.random.seed(seed)
    for _ in range(parameters.max_steps):
        model.step()
    model_dataframe = model.datacollector.get_model_vars_dataframe()
    print(model_dataframe.tail())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single BitRewardsModel simulation.")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Optional path to a TOML configuration file.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Optional override for the number of steps.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for the Mesa random number generator.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parameters, seed = build_parameters_from_args(args)
    run_single_simulation(parameters, seed)


if __name__ == "__main__":
    main()
