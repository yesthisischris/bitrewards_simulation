from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Dict, List, Tuple

from bitrewards_abm.domain.parameters import SimulationParameters


@dataclass
class ExperimentConfig:
    name: str
    runs_per_config: int
    steps_per_run: int | None
    random_seed_base: int | None
    sweeps: Dict[str, List[object]]


def _load_toml(path: Path) -> dict:
    import tomllib

    with path.open("rb") as file:
        data = tomllib.load(file)
    return data


def _build_simulation_parameters(config_data: dict) -> SimulationParameters:
    simulation_section = config_data.get("simulation", {})
    parameter_fields = {field.name for field in fields(SimulationParameters)}
    init_kwargs = {
        key: value for key, value in simulation_section.items() if key in parameter_fields
    }
    return SimulationParameters(**init_kwargs)


def _build_experiment_config(config_data: dict, config_path: Path) -> ExperimentConfig:
    experiment_section = config_data.get("experiment", {})

    name_value = experiment_section.get("name") or config_path.stem

    runs_per_config_value = int(experiment_section.get("runs_per_config", 4))

    steps_per_run_raw = experiment_section.get("steps_per_run")
    steps_per_run_value: int | None
    if steps_per_run_raw is None:
        steps_per_run_value = None
    else:
        steps_per_run_value = int(steps_per_run_raw)

    random_seed_base_raw = experiment_section.get("random_seed_base")
    random_seed_base_value: int | None
    if random_seed_base_raw is None:
        random_seed_base_value = None
    else:
        random_seed_base_value = int(random_seed_base_raw)

    sweeps_source = experiment_section.get("sweeps", {})
    sweeps: Dict[str, List[object]] = {}
    for key, value in sweeps_source.items():
        if isinstance(value, list):
            sweeps[key] = list(value)
        else:
            sweeps[key] = [value]

    return ExperimentConfig(
        name=name_value,
        runs_per_config=runs_per_config_value,
        steps_per_run=steps_per_run_value,
        random_seed_base=random_seed_base_value,
        sweeps=sweeps,
    )


def load_experiment_configuration(config_path: Path) -> Tuple[SimulationParameters, ExperimentConfig]:
    data = _load_toml(config_path)
    simulation_parameters = _build_simulation_parameters(data)
    experiment_config = _build_experiment_config(data, config_path)
    if experiment_config.steps_per_run is not None:
        simulation_parameters.max_steps = experiment_config.steps_per_run
    return simulation_parameters, experiment_config
