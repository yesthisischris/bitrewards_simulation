from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _filter_run(df: pd.DataFrame, run_id: int) -> pd.DataFrame:
    if "run_id" not in df.columns:
        return df
    run_df = df[df["run_id"] == run_id].copy()
    return run_df.sort_values("step") if "step" in run_df.columns else run_df


def plot_active_roles(timeseries: pd.DataFrame, run_id: int, output_path: Path) -> None:
    df = _filter_run(timeseries, run_id)
    required = {"step", "active_creator_count", "active_investor_count", "active_user_count"}
    if not required.issubset(df.columns):
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df["step"], df["active_creator_count"], label="Creators (active)")
    ax.plot(df["step"], df["active_investor_count"], label="Investors (active)")
    ax.plot(df["step"], df["active_user_count"], label="Users (active)")
    ax.set_xlabel("Step")
    ax.set_ylabel("Active agents")
    ax.set_title(f"Run {run_id}: Active agents by role")
    ax.legend()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_contribution_mix(timeseries: pd.DataFrame, run_id: int, output_path: Path) -> None:
    df = _filter_run(timeseries, run_id)
    required = {
        "step",
        "core_research_contribution_count",
        "supporting_contribution_count",
        "funding_contribution_count",
    }
    if not required.issubset(df.columns):
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(
        df["step"],
        df["core_research_contribution_count"],
        df["supporting_contribution_count"],
        df["funding_contribution_count"],
        labels=["Core", "Supporting", "Funding"],
    )
    ax.set_xlabel("Step")
    ax.set_ylabel("Contribution count")
    ax.set_title(f"Run {run_id}: Contribution mix")
    ax.legend(loc="upper left")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_rewards_by_type(timeseries: pd.DataFrame, run_id: int, output_path: Path) -> None:
    df = _filter_run(timeseries, run_id)
    required = {
        "step",
        "total_reward_core_research",
        "total_reward_supporting",
        "total_reward_funding",
    }
    if not required.issubset(df.columns):
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df["step"], df["total_reward_core_research"], label="Core rewards")
    ax.plot(df["step"], df["total_reward_supporting"], label="Supporting rewards")
    ax.plot(df["step"], df["total_reward_funding"], label="Funding rewards")
    ax.set_xlabel("Step")
    ax.set_ylabel("Cumulative rewards")
    ax.set_title(f"Run {run_id}: Rewards by contribution type")
    ax.legend(loc="upper left")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_role_income_shares(timeseries: pd.DataFrame, run_id: int, output_path: Path) -> None:
    df = _filter_run(timeseries, run_id)
    required = {
        "step",
        "role_income_share_creators",
        "role_income_share_investors",
        "role_income_share_users",
    }
    if not required.issubset(df.columns):
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df["step"], df["role_income_share_creators"], label="Creators")
    ax.plot(df["step"], df["role_income_share_investors"], label="Investors")
    ax.plot(df["step"], df["role_income_share_users"], label="Users")
    ax.set_xlabel("Step")
    ax.set_ylabel("Share of income")
    ax.set_ylim(0.0, 1.0)
    ax.set_title(f"Run {run_id}: Role income shares")
    ax.legend(loc="upper right")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_usage(timeseries: pd.DataFrame, run_id: int, output_path: Path) -> None:
    df = _filter_run(timeseries, run_id)
    required = {"step", "usage_event_count"}
    if not required.issubset(df.columns):
        return
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(df["step"], df["usage_event_count"], width=0.8, label="Usage events")
    ax.set_xlabel("Step")
    ax.set_ylabel("Count")
    ax.set_title(f"Run {run_id}: Usage events per step")
    ax.legend()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_investor_roi_distribution(run_summary: pd.DataFrame, output_path: Path) -> None:
    if "investor_mean_roi" not in run_summary.columns:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(run_summary["investor_mean_roi"].dropna(), bins=15)
    ax.set_xlabel("Investor mean ROI")
    ax.set_ylabel("Count")
    ax.set_title("Investor ROI distribution across runs")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_tracing_metrics(run_summary: pd.DataFrame, output_path: Path) -> None:
    columns = [
        "tracing_true_links",
        "tracing_detected_true_links",
        "tracing_false_positive_links",
        "tracing_missed_true_links",
    ]
    available = [col for col in columns if col in run_summary.columns]
    if not available:
        return
    totals = {col: float(run_summary[col].sum()) for col in available}
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(list(totals.keys()), list(totals.values()))
    ax.set_ylabel("Count")
    ax.set_title("Tracing diagnostics (sum over runs)")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_funding_histograms(run_summary: pd.DataFrame, output_dir: Path) -> None:
    amount_cols = ["funding_min_amount", "funding_max_amount"]
    royalty_cols = ["funding_royalty_min", "funding_royalty_max"]
    if any(col in run_summary.columns for col in amount_cols):
        fig, ax = plt.subplots(figsize=(8, 4))
        if "funding_min_amount" in run_summary.columns:
            ax.hist(run_summary["funding_min_amount"], bins=10, alpha=0.6, label="Min amount")
        if "funding_max_amount" in run_summary.columns:
            ax.hist(run_summary["funding_max_amount"], bins=10, alpha=0.6, label="Max amount")
        ax.set_xlabel("Funding amount")
        ax.set_ylabel("Count")
        ax.set_title("Funding amount parameters across runs")
        ax.legend()
        output_dir.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(output_dir / "funding_amounts.png", dpi=150)
        plt.close(fig)
    if any(col in run_summary.columns for col in royalty_cols):
        fig, ax = plt.subplots(figsize=(8, 4))
        if "funding_royalty_min" in run_summary.columns:
            ax.hist(run_summary["funding_royalty_min"], bins=10, alpha=0.6, label="Min royalty")
        if "funding_royalty_max" in run_summary.columns:
            ax.hist(run_summary["funding_royalty_max"], bins=10, alpha=0.6, label="Max royalty")
        ax.set_xlabel("Funding royalty percent")
        ax.set_ylabel("Count")
        ax.set_title("Funding royalty parameters across runs")
        ax.legend()
        output_dir.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(output_dir / "funding_royalties.png", dpi=150)
        plt.close(fig)


def plot_satisfaction_and_churn(timeseries: pd.DataFrame, run_id: int, output_path: Path) -> None:
    df = _filter_run(timeseries, run_id)
    required = {
        "step",
        "mean_creator_satisfaction",
        "mean_investor_satisfaction",
        "mean_user_satisfaction",
        "creator_churned_count",
        "investor_churned_count",
        "user_churned_count",
    }
    if not required.issubset(df.columns):
        return
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(df["step"], df["mean_creator_satisfaction"], label="Creator satisfaction")
    ax1.plot(df["step"], df["mean_investor_satisfaction"], label="Investor satisfaction")
    ax1.plot(df["step"], df["mean_user_satisfaction"], label="User satisfaction")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Satisfaction")
    ax2 = ax1.twinx()
    ax2.plot(df["step"], df["creator_churned_count"], linestyle="--", label="Creator churned", color="tab:blue")
    ax2.plot(df["step"], df["investor_churned_count"], linestyle="--", label="Investor churned", color="tab:orange")
    ax2.plot(df["step"], df["user_churned_count"], linestyle="--", label="User churned", color="tab:green")
    ax2.set_ylabel("Churned agents")
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right")
    ax1.set_title(f"Run {run_id}: Satisfaction and churn")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def generate_all_plots(
    timeseries_path: Path,
    run_summary_path: Path,
    run_id: int,
    output_dir: Path,
) -> None:
    timeseries = load_csv(timeseries_path)
    run_summary = load_csv(run_summary_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_active_roles(timeseries, run_id, output_dir / f"run_{run_id}_active_agents.png")
    plot_contribution_mix(timeseries, run_id, output_dir / f"run_{run_id}_contribution_mix.png")
    plot_rewards_by_type(timeseries, run_id, output_dir / f"run_{run_id}_rewards_by_type.png")
    plot_role_income_shares(timeseries, run_id, output_dir / f"run_{run_id}_role_income_shares.png")
    plot_usage(timeseries, run_id, output_dir / f"run_{run_id}_usage_events.png")
    plot_satisfaction_and_churn(timeseries, run_id, output_dir / f"run_{run_id}_satisfaction_churn.png")
    plot_investor_roi_distribution(run_summary, output_dir / "investor_roi_distribution.png")
    plot_tracing_metrics(run_summary, output_dir / "tracing_metrics.png")
    plot_funding_histograms(run_summary, output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate visuals for BITrewards ABM outputs.")
    parser.add_argument("--timeseries", type=Path, default=Path("data/timeseries.csv"))
    parser.add_argument("--run-summary", dest="run_summary", type=Path, default=Path("data/run_summary.csv"))
    parser.add_argument("--run-id", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("visuals/output"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_all_plots(args.timeseries, args.run_summary, args.run_id, args.output_dir)


if __name__ == "__main__":
    main()
