"""Batch experiment runner for the BitRewardsModel."""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.experiment.config import ExperimentConfig, load_experiment_configuration
from bitrewards_abm.simulation.model import BitRewardsModel


KEY_PARAMETERS_FOR_LOGGING = [
    "creator_base_contribution_probability",
    "user_usage_probability",
    "gas_fee_share_rate",
    "funding_split_fraction",
    "tracing_accuracy",
    "default_derivative_split",
    "supporting_derivative_split",
    "core_research_base_royalty_share",
    "funding_base_royalty_share",
    "supporting_base_royalty_share",
    "aspiration_income_per_step",
    "satisfaction_logistic_k",
    "satisfaction_churn_threshold",
    "satisfaction_churn_window",
]


def parameter_grid(variable_params: Dict[str, Iterable]) -> Iterable[Dict[str, object]]:
    if not variable_params:
        yield {}
        return
    keys = list(variable_params.keys())
    values_product = itertools.product(*(variable_params[key] for key in keys))
    for values in values_product:
        yield dict(zip(keys, values))


def parameters_to_log(parameters: SimulationParameters) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for name in KEY_PARAMETERS_FOR_LOGGING:
        if hasattr(parameters, name):
            result[name] = getattr(parameters, name)
    return result


def _parameters_for_run(
    base_parameters: SimulationParameters,
    parameter_overrides: Dict[str, object],
) -> SimulationParameters:
    combined = dict(base_parameters.__dict__)
    combined.update(parameter_overrides)
    return SimulationParameters(**combined)


def _seed_for_run(experiment_config: ExperimentConfig, run_id: int) -> int | None:
    if experiment_config.random_seed_base is None:
        return None
    return experiment_config.random_seed_base + run_id


def _run_single_model(
    parameters: SimulationParameters,
    seed: int | None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    model = BitRewardsModel(parameters)
    if seed is not None:
        model.random.seed(seed)
    for _ in range(parameters.max_steps):
        model.step()
    model_dataframe = model.datacollector.get_model_vars_dataframe()
    model_dataframe = model_dataframe.reset_index()
    tracing_metrics = dict(model.tracing_metrics) if hasattr(model, "tracing_metrics") else {}
    return model_dataframe, tracing_metrics


def run_experiments_for_config(
    config_path: Path,
    out_dir: Path | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if out_dir is None:
        out_dir = Path("data")

    base_parameters, experiment_config = load_experiment_configuration(config_path)

    run_summaries: List[pd.Series] = []
    timeseries_frames: List[pd.DataFrame] = []
    run_id = 0

    for parameter_overrides in parameter_grid(experiment_config.sweeps):
        for rep in range(experiment_config.runs_per_config):
            parameters = _parameters_for_run(base_parameters, parameter_overrides)
            seed = _seed_for_run(experiment_config, run_id)
            model_dataframe, tracing_metrics = _run_single_model(parameters, seed)

            model_dataframe["run_id"] = run_id
            model_dataframe["rep"] = rep
            model_dataframe["scenario_name"] = experiment_config.name

            logged_params = parameters_to_log(parameters)
            combined_parameters = {**logged_params, **parameter_overrides}
            for key, value in combined_parameters.items():
                model_dataframe[key] = value

            timeseries_frames.append(model_dataframe)

            final_row = model_dataframe.iloc[-1].copy()
            final_row["run_id"] = run_id
            final_row["rep"] = rep
            final_row["scenario_name"] = experiment_config.name
            for key, value in combined_parameters.items():
                final_row[key] = value
            final_row["mean_creator_satisfaction_over_run"] = float(
                model_dataframe["mean_creator_satisfaction"].mean()
            )
            final_row["mean_investor_satisfaction_over_run"] = float(
                model_dataframe["mean_investor_satisfaction"].mean()
            )
            final_row["mean_user_satisfaction_over_run"] = float(
                model_dataframe["mean_user_satisfaction"].mean()
            )
            for key, value in tracing_metrics.items():
                final_row[f"tracing_{key}"] = value

            run_summaries.append(final_row)
            run_id += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    timeseries_df = pd.concat(timeseries_frames, ignore_index=True)
    run_summary_df = pd.DataFrame(run_summaries)

    timeseries_path = out_dir / "timeseries.csv"
    run_summary_path = out_dir / "run_summary.csv"

    timeseries_df.to_csv(timeseries_path, index=False)
    run_summary_df.to_csv(run_summary_path, index=False)

    print(f"Wrote run summaries to {run_summary_path}")
    print(f"Wrote time series to {timeseries_path}")

    return run_summary_df, timeseries_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch experiments for BitRewardsModel.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/baseline.toml"),
        help="Path to a TOML configuration file.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data"),
        help="Directory where CSV outputs will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_experiments_for_config(args.config, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
