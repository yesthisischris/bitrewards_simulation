from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def plot_single_run(timeseries_path: Path, run_id: int, output_path: Path) -> None:
    df = load_csv(timeseries_path)
    required = {"step", "run_id", "contribution_count", "usage_event_count", "total_fee_distributed"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in timeseries: {missing}")
    run_df = df[df["run_id"] == run_id].copy()
    if run_df.empty:
        raise ValueError(f"No rows for run_id {run_id}")
    run_df = run_df.sort_values("step")

    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(run_df["step"], run_df["contribution_count"], label="Contributions")
    ax1.plot(run_df["step"], run_df["usage_event_count"], label="Usage events")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Count")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(run_df["step"], run_df["total_fee_distributed"], linestyle="--", color="darkorange", label="Fee distributed")
    ax2.set_ylabel("Fee distributed per step")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right")

    ax1.set_title(f"Run {run_id}: Contributions, Usage, and Fees Over Time")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_creator_wealth_histogram(agent_path: Path, output_path: Path) -> None:
    df = load_csv(agent_path)
    required = {"Step", "AgentID", "wealth", "agent_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in agent data: {missing}")
    creators = df[df["agent_type"] == "CreatorAgent"].copy()
    if creators.empty:
        raise ValueError("No creator rows in agent data")
    final_step = creators["Step"].max()
    final_creators = creators[creators["Step"] == final_step]
    wealth_values = final_creators["wealth"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(wealth_values, bins=20)
    ax.set_xlabel("Creator wealth at final step")
    ax.set_ylabel("Number of creators")
    ax.set_title("Distribution of Creator Wealth at Final Step")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_investor_roi_vs_split(summary_path: Path, output_path: Path, funding_split_column: str = "funding_split_fraction") -> None:
    df = load_csv(summary_path)
    required = {funding_split_column, "investor_mean_roi"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in run summary: {missing}")
    grouped = df.groupby(funding_split_column)["investor_mean_roi"].mean().reset_index()
    grouped = grouped.sort_values(funding_split_column)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(grouped[funding_split_column], grouped["investor_mean_roi"], marker="o")
    ax.set_xlabel("Funding split fraction")
    ax.set_ylabel("Average investor mean ROI")
    ax.set_title("Investor ROI vs Funding Split Fraction")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_investor_roi_vs_fee_rate(summary_path: Path, output_path: Path) -> None:
    df = load_csv(summary_path)
    required = {"gas_fee_share_rate", "investor_mean_roi"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in run summary: {missing}")
    grouped = df.groupby("gas_fee_share_rate")["investor_mean_roi"].mean().reset_index()
    grouped = grouped.sort_values("gas_fee_share_rate")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(grouped["gas_fee_share_rate"], grouped["investor_mean_roi"], marker="o")
    ax.set_xlabel("Gas fee share rate")
    ax.set_ylabel("Average investor mean ROI")
    ax.set_title("Investor ROI vs Gas Fee Share Rate")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_creator_satisfaction_and_churn(timeseries_path: Path, run_id: int, output_path: Path) -> None:
    df = load_csv(timeseries_path)
    required = {
        "run_id",
        "step",
        "mean_creator_satisfaction",
        "active_creator_count",
        "creator_churned_count",
    }
    missing = required - set(df.columns)
    if missing:
        return
    run_df = df[df["run_id"] == run_id].copy()
    if run_df.empty:
        return
    run_df = run_df.sort_values("step")
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(run_df["step"], run_df["mean_creator_satisfaction"], label="Mean creator satisfaction", color="teal")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Satisfaction")
    ax2 = ax1.twinx()
    ax2.plot(run_df["step"], run_df["active_creator_count"], label="Active creators", color="steelblue")
    ax2.plot(run_df["step"], run_df["creator_churned_count"], label="Churned creators", color="darkorange", linestyle="--")
    ax2.set_ylabel("Creators")
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right")
    ax1.set_title(f"Run {run_id}: Creator Satisfaction and Churn")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeseries", type=Path, default=Path("data/timeseries.csv"))
    parser.add_argument("--run-summary", dest="run_summary", type=Path, default=Path("data/run_summary.csv"))
    parser.add_argument("--agents", type=Path, default=Path("data/agents_run0.csv"))
    parser.add_argument("--run-id", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("visuals/output"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_single_run(args.timeseries, args.run_id, output_dir / f"run_{args.run_id}_trajectory.png")
    if args.agents.exists():
        plot_creator_wealth_histogram(args.agents, output_dir / "creator_wealth_histogram.png")
    plot_investor_roi_vs_split(args.run_summary, output_dir / "investor_roi_vs_split.png")
    plot_investor_roi_vs_fee_rate(args.run_summary, output_dir / "investor_roi_vs_fee_rate.png")
    plot_creator_satisfaction_and_churn(args.timeseries, args.run_id, output_dir / f"run_{args.run_id}_creator_satisfaction_churn.png")


if __name__ == "__main__":
    main()
