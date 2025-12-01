"""Batch experiment runner for the BitRewardsModel."""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def parameter_grid(variable_params: Dict[str, Iterable]) -> Iterable[Dict[str, object]]:
    keys = list(variable_params.keys())
    values_product = itertools.product(*(variable_params[key] for key in keys))
    for combo in values_product:
        yield dict(zip(keys, combo))


def run_experiments() -> None:
    base_parameters = SimulationParameters()
    variable_params = {
        "creator_base_contribution_probability": [0.2, 0.4],
        "user_usage_probability": [0.4, 0.7],
        "gas_fee_share_rate": [0.002, 0.005],
        "funding_split_fraction": [0.01, 0.02],
    }
    repetitions_per_setting = 2

    run_summaries: List[pd.Series] = []
    timeseries_frames: List[pd.DataFrame] = []
    run_id = 0

    for param_combo in parameter_grid(variable_params):
        for rep in range(repetitions_per_setting):
            parameters = SimulationParameters(**{**base_parameters.__dict__, **param_combo})
            model = BitRewardsModel(parameters)
            for _ in range(parameters.max_steps):
                model.step()

            model_df = model.datacollector.get_model_vars_dataframe().reset_index()
            model_df["run_id"] = run_id
            model_df["rep"] = rep
            for key, value in param_combo.items():
                model_df[key] = value
            timeseries_frames.append(model_df)

            final_row = model_df.iloc[-1].copy()
            final_row["run_id"] = run_id
            final_row["rep"] = rep
            for key, value in param_combo.items():
                final_row[key] = value
            run_summaries.append(final_row)

            run_id += 1

    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)

    run_summary_df = pd.DataFrame(run_summaries)
    timeseries_df = pd.concat(timeseries_frames, ignore_index=True)

    run_summary_df.to_csv(out_dir / "run_summary.csv", index=False)
    timeseries_df.to_csv(out_dir / "timeseries.csv", index=False)

    print(f"Wrote run summaries to {out_dir / 'run_summary.csv'}")
    print(f"Wrote time series to {out_dir / 'timeseries.csv'}")


if __name__ == "__main__":
    run_experiments()
