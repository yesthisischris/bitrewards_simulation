from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def plot_active_agents_by_role(timeseries_path: Path, run_id: int, output_path: Path) -> None:
    df = load_csv(timeseries_path)
    required = {
        "run_id",
        "step",
        "active_creator_count",
        "active_investor_count",
        "active_user_count",
    }
    missing = required - set(df.columns)
    if missing:
        return
    run_df = df[df["run_id"] == run_id].copy()
    if run_df.empty:
        return
    run_df = run_df.sort_values("step")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(run_df["step"], run_df["active_creator_count"], label="Creators")
    ax.plot(run_df["step"], run_df["active_investor_count"], label="Investors")
    ax.plot(run_df["step"], run_df["active_user_count"], label="Users")
    ax.set_xlabel("Step")
    ax.set_ylabel("Active agents")
    ax.set_title(f"Run {run_id}: Active agents by role")
    ax.legend(loc="upper right")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_satisfaction_and_churn(
    timeseries_path: Path,
    run_id: int,
    output_path: Path,
) -> None:
    df = load_csv(timeseries_path)
    required = {
        "run_id",
        "step",
        "mean_creator_satisfaction",
        "mean_investor_satisfaction",
        "mean_user_satisfaction",
        "creator_churned_count",
        "investor_churned_count",
        "user_churned_count",
    }
    missing = required - set(df.columns)
    if missing:
        return
    run_df = df[df["run_id"] == run_id].copy()
    if run_df.empty:
        return
    run_df = run_df.sort_values("step")

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(run_df["step"], run_df["mean_creator_satisfaction"], label="Creator satisfaction")
    ax1.plot(run_df["step"], run_df["mean_investor_satisfaction"], label="Investor satisfaction")
    ax1.plot(run_df["step"], run_df["mean_user_satisfaction"], label="User satisfaction")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Mean satisfaction")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(run_df["step"], run_df["creator_churned_count"], linestyle="--", label="Creators churned")
    ax2.plot(run_df["step"], run_df["investor_churned_count"], linestyle="--", label="Investors churned")
    ax2.plot(run_df["step"], run_df["user_churned_count"], linestyle="--", label="Users churned")
    ax2.set_ylabel("Cumulative churn")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right")

    ax1.set_title(f"Run {run_id}: Satisfaction and churn")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_role_reward_shares(summary_path: Path, output_path: Path) -> None:
    df = load_csv(summary_path)
    required = {
        "total_income_creators",
        "total_income_investors",
        "total_income_users",
    }
    missing = required - set(df.columns)
    if missing:
        return

    total_creators = float(df["total_income_creators"].sum())
    total_investors = float(df["total_income_investors"].sum())
    total_users = float(df["total_income_users"].sum())

    values = [total_creators, total_investors, total_users]
    total_value = sum(values)
    if total_value <= 0.0:
        return

    labels = ["Creators", "Investors", "Users"]
    shares = [value / total_value for value in values]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, shares)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Share of total income")
    ax.set_title("Role reward shares (all runs)")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a mini dashboard for a reference scenario."
    )
    parser.add_argument(
        "--scenario-dir",
        type=Path,
        default=Path("data/reference/baseline"),
        help="Directory containing timeseries.csv and run_summary.csv.",
    )
    parser.add_argument(
        "--run-id",
        type=int,
        default=0,
        help="Run identifier to visualize.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("visuals/reference"),
        help="Directory where PNG figures will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario_dir = args.scenario_dir
    output_dir = args.output_dir

    timeseries_path = scenario_dir / "timeseries.csv"
    summary_path = scenario_dir / "run_summary.csv"

    plot_active_agents_by_role(
        timeseries_path,
        args.run_id,
        output_dir / f"{scenario_dir.name}_run_{args.run_id}_active_agents.png",
    )
    plot_satisfaction_and_churn(
        timeseries_path,
        args.run_id,
        output_dir / f"{scenario_dir.name}_run_{args.run_id}_satisfaction_churn.png",
    )
    plot_role_reward_shares(
        summary_path,
        output_dir / f"{scenario_dir.name}_role_reward_shares.png",
    )


if __name__ == "__main__":
    main()
