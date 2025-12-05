#!/usr/bin/env python

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from bitrewards_abm.analysis.metrics import collect_metrics_from_model
from bitrewards_abm.analysis.visualization import (
    plot_ai_tracing_panel,
    plot_dag_snapshot,
    plot_life_of_contribution,
    plot_role_income_dashboard,
    plot_system_map,
)
from bitrewards_abm.domain.parameters import SimulationParameters
from bitrewards_abm.simulation.model import BitRewardsModel


def main() -> None:
    params = SimulationParameters(
        max_steps=200,
        creator_count=20,
        investor_count=5,
        user_count=50,
        supporting_creator_fraction=0.3,
        tracing_accuracy=0.8,
        tracing_false_positive_rate=0.05,
        funding_royalty_min=0.01,
        funding_royalty_max=0.03,
        investor_arrival_rate=0.05,
        investor_arrival_roi_sensitivity=0.2,
        initial_investor_budget=150.0,
        funding_min_amount=2.0,
        funding_max_amount=15.0,
    )
    model = BitRewardsModel(parameters=params)
    out_dir = Path("visuals/generated")
    dag_frames_dir = out_dir / "dag_frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    dag_frames_dir.mkdir(parents=True, exist_ok=True)
    for step in range(params.max_steps):
        model.step()
        fig_step = plot_dag_snapshot(model, max_nodes=60, include_true_vs_observed=True)
        fig_step.text(0.02, 0.96, f"Week {step + 1}", ha="left", va="top", fontsize=10, transform=fig_step.transFigure)
        fig_step.savefig(dag_frames_dir / f"dag_step_{step + 1:04d}.png", dpi=120)
        plt.close(fig_step)
    metrics = collect_metrics_from_model(model)

    fig = plot_system_map()
    fig.savefig(out_dir / "system_map.png", dpi=150)
    plt.close(fig)

    fig = plot_role_income_dashboard(metrics)
    fig.savefig(out_dir / "role_income_dashboard.png", dpi=150)
    plt.close(fig)

    fig = plot_dag_snapshot(model, max_nodes=60, include_true_vs_observed=True)
    fig.savefig(out_dir / "dag_snapshot.png", dpi=150)
    plt.close(fig)

    fig = plot_ai_tracing_panel(metrics, model)
    fig.savefig(out_dir / "ai_tracing_panel.png", dpi=150)
    plt.close(fig)

    if model.contributions:
        last_contribution_id = sorted(model.contributions.keys())[-1]
        fig = plot_life_of_contribution(model, metrics, last_contribution_id)
        fig.savefig(out_dir / f"life_of_contribution_{last_contribution_id}.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
