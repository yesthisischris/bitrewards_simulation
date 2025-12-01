"""Batch experiment runner for the BitRewardsModel."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from bitrewards_simulation.model.bitrewards_model import BitRewardsModel


def parameter_grid(variable_params: Dict[str, Iterable]) -> Iterable[Dict[str, object]]:
    keys = list(variable_params.keys())
    values_product = itertools.product(*(variable_params[key] for key in keys))
    for combo in values_product:
        yield dict(zip(keys, combo))


def run_experiments() -> None:
    fixed_params = {
        "N_creators": 50,
        "N_users": 200,
        "max_steps": 200,
    }
    variable_params = {
        "max_usage_events_per_user": [1, 3],
        "contribution_threshold": [0.3, 0.5],
        "fee_share_rate": [0.002, 0.005],
    }
    repetitions_per_setting = 3

    run_summaries: List[pd.Series] = []
    timeseries_frames: List[pd.DataFrame] = []

    run_id = 0

    for param_combo in parameter_grid(variable_params):
        params = {**fixed_params, **param_combo}

        for rep in range(repetitions_per_setting):
            model = BitRewardsModel(
                **params,
                random_seed=run_id,
            )

            while model.running:
                model.step()

            model_df = model.datacollector.get_model_vars_dataframe().reset_index()
            model_df["run_id"] = run_id
            model_df["rep"] = rep
            for key, value in params.items():
                model_df[key] = value
            timeseries_frames.append(model_df)

            final_row = model_df.iloc[-1].copy()
            final_row["run_id"] = run_id
            final_row["rep"] = rep
            for key, value in params.items():
                final_row[key] = value
            run_summaries.append(final_row)

            run_id += 1

    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)

    run_summary_df = pd.DataFrame(run_summaries)
    timeseries_df = pd.concat(timeseries_frames, ignore_index=True)

    run_summary_path = out_dir / "run_summary.csv"
    timeseries_path = out_dir / "timeseries.csv"

    run_summary_df.to_csv(run_summary_path, index=False)
    timeseries_df.to_csv(timeseries_path, index=False)

    print(f"Wrote run summaries to {run_summary_path}")
    print(f"Wrote time series to {timeseries_path}")


if __name__ == "__main__":
    run_experiments()
