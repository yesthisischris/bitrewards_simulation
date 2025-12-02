from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd

from experiments.run_batch import run_experiments_for_config


def test_experiment_harness_writes_outputs(tmp_path: Path) -> None:
    config_text = dedent(
        """
        [simulation]
        creator_count = 3
        investor_count = 1
        user_count = 5
        max_steps = 10

        [experiment]
        name = "test_harness"
        runs_per_config = 1
        steps_per_run = 5
        random_seed_base = 123

        [experiment.sweeps]
        gas_fee_share_rate = [0.002]
        funding_split_fraction = [0.01]
        """
    ).strip()
    config_path = tmp_path / "test_config.toml"
    config_path.write_text(config_text)

    out_dir = tmp_path / "out"
    run_experiments_for_config(config_path, out_dir=out_dir)

    timeseries_path = out_dir / "timeseries.csv"
    summary_path = out_dir / "run_summary.csv"

    assert timeseries_path.exists()
    assert summary_path.exists()

    timeseries_df = pd.read_csv(timeseries_path)
    summary_df = pd.read_csv(summary_path)

    assert not timeseries_df.empty
    assert not summary_df.empty

    assert "run_id" in timeseries_df.columns
    assert "run_id" in summary_df.columns
    assert summary_df["run_id"].nunique() == 1
