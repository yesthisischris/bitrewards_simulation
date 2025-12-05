from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd

from bitrewards_abm.simulation.model import BitRewardsModel


@dataclass
class SimulationMetrics:
    reward_events: pd.DataFrame
    usage_events: pd.DataFrame
    tracing_metrics: Dict[str, float]
    role_income_by_step: pd.DataFrame
    gas_vs_royalty_by_role: pd.DataFrame


def collect_metrics_from_model(model: BitRewardsModel) -> SimulationMetrics:
    reward_df = pd.DataFrame(model.reward_events or [])
    usage_df = pd.DataFrame(model.usage_events or [])

    if reward_df.empty:
        reward_df = pd.DataFrame(
            columns=[
                "step",
                "payout_type",
                "channel",
                "amount",
                "recipient_id",
                "recipient_role",
                "source_contribution_id",
            ]
        )
    if usage_df.empty:
        usage_df = pd.DataFrame(
            columns=[
                "step",
                "contribution_id",
                "user_id",
            ]
        )

    if not reward_df.empty:
        role_income_by_step = (
            reward_df.groupby(["step", "recipient_role"])["amount"]
            .sum()
            .reset_index()
        )
    else:
        role_income_by_step = pd.DataFrame(
            columns=["step", "recipient_role", "amount"]
        )

    if not reward_df.empty:
        gas_vs_royalty_by_role = (
            reward_df.groupby(["recipient_role", "channel"])["amount"]
            .sum()
            .reset_index()
        )
    else:
        gas_vs_royalty_by_role = pd.DataFrame(
            columns=["recipient_role", "channel", "amount"]
        )

    tracing_metrics = dict(getattr(model, "tracing_metrics", {}))

    return SimulationMetrics(
        reward_events=reward_df,
        usage_events=usage_df,
        tracing_metrics=tracing_metrics,
        role_income_by_step=role_income_by_step,
        gas_vs_royalty_by_role=gas_vs_royalty_by_role,
    )
