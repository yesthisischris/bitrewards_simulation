from __future__ import annotations

from pathlib import Path

import pandas as pd

from bitrewards_abm.experiment.config import load_experiment_configuration
from bitrewards_abm.simulation.model import BitRewardsModel


SCENARIO_CONFIGS = [
    Path("configs/baseline.toml"),
    Path("configs/low_tracing_accuracy.toml"),
    Path("configs/high_funding_share.toml"),
    Path("configs/high_investor_share.toml"),
]


def _run_tiny_simulation(config_path: Path, max_steps: int = 40) -> pd.DataFrame:
    parameters, experiment_config = load_experiment_configuration(config_path)
    if parameters.max_steps > max_steps:
        parameters.max_steps = max_steps

    model = BitRewardsModel(parameters)
    if experiment_config.random_seed_base is not None:
        model.random.seed(experiment_config.random_seed_base)

    for _ in range(parameters.max_steps):
        model.step()

    df = model.datacollector.get_model_vars_dataframe().reset_index()
    df["scenario_name"] = experiment_config.name
    return df


def test_scenario_configs_produce_non_degenerate_runs(tmp_path: Path) -> None:
    all_frames = []
    for config_path in SCENARIO_CONFIGS:
        assert config_path.exists(), f"Missing scenario config: {config_path}"
        df = _run_tiny_simulation(config_path)
        assert not df.empty
        all_frames.append(df)

        assert (df["total_fee_distributed"] >= 0.0).all()
        assert df["total_fee_distributed"].sum() > 0.0

        assert df["active_creator_count"].iloc[0] > 0
        assert df["active_investor_count"].iloc[0] >= 0
        assert df["active_user_count"].iloc[0] >= 0

        for column in [
            "mean_creator_satisfaction",
            "mean_investor_satisfaction",
            "mean_user_satisfaction",
        ]:
            assert (df[column] >= 0.0).all()
            assert (df[column] <= 1.0).all()

    combined = pd.concat(all_frames, ignore_index=True)
    assert combined["scenario_name"].nunique() == len(SCENARIO_CONFIGS)
