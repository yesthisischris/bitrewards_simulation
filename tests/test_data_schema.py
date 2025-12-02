from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pandas as pd

from bitrewards_abm.domain.parameters import SimulationParameters
from experiments.run_batch import run_experiments


def test_data_schema_and_metrics(tmp_path: Path) -> None:
    base_parameters = SimulationParameters(
        creator_count=5,
        investor_count=2,
        user_count=5,
        max_steps=20,
    )
    variable_params = {
        "creator_base_contribution_probability": [
            base_parameters.creator_base_contribution_probability
        ],
        "user_usage_probability": [base_parameters.user_usage_probability],
        "gas_fee_share_rate": [base_parameters.gas_fee_share_rate],
        "funding_split_fraction": [base_parameters.funding_split_fraction],
    }

    run_experiments(
        out_dir=tmp_path,
        base_parameters=base_parameters,
        repetitions_per_setting=1,
        variable_params=variable_params,
    )

    timeseries_path = tmp_path / "timeseries.csv"
    summary_path = tmp_path / "run_summary.csv"

    assert timeseries_path.exists()
    assert summary_path.exists()

    timeseries_df = pd.read_csv(timeseries_path)
    summary_df = pd.read_csv(summary_path)

    required_timeseries_columns = {
        "run_id",
        "rep",
        "step",
        "contribution_count",
        "usage_event_count",
        "active_creator_count",
        "active_investor_count",
        "active_user_count",
        "total_fee_distributed",
        "cumulative_fee_distributed",
        "creator_wealth_gini",
        "investor_mean_roi",
        "mean_creator_satisfaction",
        "mean_investor_satisfaction",
        "mean_user_satisfaction",
        "creator_churned_count",
        "investor_churned_count",
        "user_churned_count",
        "core_research_contribution_count",
        "funding_contribution_count",
        "supporting_contribution_count",
        "total_reward_core_research",
        "total_reward_funding",
        "total_reward_supporting",
        "total_income_creators",
        "total_income_investors",
        "total_income_users",
        "gas_fee_share_rate",
        "funding_split_fraction",
    }
    missing_timeseries = required_timeseries_columns - set(timeseries_df.columns)
    assert not missing_timeseries

    required_summary_columns = {
        "run_id",
        "rep",
        "step",
        "cumulative_fee_distributed",
        "creator_wealth_gini",
        "investor_mean_roi",
        "total_reward_core_research",
        "total_reward_funding",
        "total_reward_supporting",
        "total_income_creators",
        "total_income_investors",
        "total_income_users",
        "role_income_share_creators",
        "role_income_share_investors",
        "role_income_share_users",
        "gas_fee_share_rate",
        "funding_split_fraction",
        "mean_creator_satisfaction_over_run",
        "mean_investor_satisfaction_over_run",
        "mean_user_satisfaction_over_run",
    }
    missing_summary = required_summary_columns - set(summary_df.columns)
    assert not missing_summary

    assert (timeseries_df["total_fee_distributed"] >= 0.0).all()
    assert (timeseries_df["cumulative_fee_distributed"] >= 0.0).all()

    assert (summary_df["creator_wealth_gini"] >= 0.0).all()
    assert (summary_df["creator_wealth_gini"] <= 1.0).all()

    for column in [
        "total_reward_core_research",
        "total_reward_funding",
        "total_reward_supporting",
        "total_income_creators",
        "total_income_investors",
        "total_income_users",
    ]:
        assert (summary_df[column] >= 0.0).all()

    shares = summary_df[
        [
            "role_income_share_creators",
            "role_income_share_investors",
            "role_income_share_users",
        ]
    ]
    assert (shares >= 0.0).to_numpy().all()
    share_sums = shares.sum(axis=1)
    assert (share_sums <= 1.01).all()
