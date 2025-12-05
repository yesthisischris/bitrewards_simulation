from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from bitrewards_abm.analysis.metrics import SimulationMetrics
from bitrewards_abm.domain.entities import ContributionType
from bitrewards_abm.infrastructure.graph_store import ContributionGraph
from bitrewards_abm.simulation.model import BitRewardsModel


def plot_system_map() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axis("off")
    ax.text(0.1, 0.5, "Usage\n(events)", ha="center", va="center", bbox=dict(boxstyle="round", edgecolor="black"))
    ax.text(0.4, 0.7, "Gas\nchannel", ha="center", va="center", bbox=dict(boxstyle="round", edgecolor="black"))
    ax.text(0.4, 0.3, "Royalty\nchannel", ha="center", va="center", bbox=dict(boxstyle="round", edgecolor="black"))
    ax.text(0.75, 0.75, "Core\ncreators", ha="center", va="center", bbox=dict(boxstyle="round", edgecolor="black"))
    ax.text(0.75, 0.5, "Supporting\nroles", ha="center", va="center", bbox=dict(boxstyle="round", edgecolor="black"))
    ax.text(0.75, 0.25, "Investors\n(funding)", ha="center", va="center", bbox=dict(boxstyle="round", edgecolor="black"))
    ax.annotate("", xy=(0.32, 0.7), xytext=(0.18, 0.56), arrowprops=dict(arrowstyle="->"))
    ax.annotate("", xy=(0.32, 0.3), xytext=(0.18, 0.44), arrowprops=dict(arrowstyle="->"))
    for y in (0.75, 0.5, 0.25):
        ax.annotate("", xy=(0.67, y), xytext=(0.48, 0.7), arrowprops=dict(arrowstyle="->"))
        ax.annotate("", xy=(0.67, y), xytext=(0.48, 0.3), arrowprops=dict(arrowstyle="->", linestyle="dashed"))
    ax.set_title("BitRewards system map: usage → gas + royalties → roles")
    return fig


def plot_role_income_dashboard(metrics: SimulationMetrics) -> plt.Figure:
    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(10, 8),
        gridspec_kw={"height_ratios": [2, 1]},
    )
    role_income = metrics.role_income_by_step
    if not role_income.empty:
        pivot = role_income.pivot_table(
            index="step",
            columns="recipient_role",
            values="amount",
            aggfunc="sum",
        ).fillna(0.0)
        pivot.sort_index(inplace=True)
        ax_top.stackplot(pivot.index, pivot.T.values, labels=pivot.columns)
        ax_top.set_xlabel("Step")
        ax_top.set_ylabel("Reward amount")
        ax_top.set_title("Rewards by role over time")
        ax_top.legend(loc="upper left")
    else:
        ax_top.text(0.5, 0.5, "No reward events recorded", ha="center", va="center")
        ax_top.set_axis_off()
    gas_vs_royalty = metrics.gas_vs_royalty_by_role
    if not gas_vs_royalty.empty:
        pivot2 = gas_vs_royalty.pivot_table(
            index="recipient_role",
            columns="channel",
            values="amount",
            aggfunc="sum",
        ).fillna(0.0)
        pivot2.plot(kind="bar", stacked=True, ax=ax_bottom)
        ax_bottom.set_xlabel("Role")
        ax_bottom.set_ylabel("Total rewards")
        ax_bottom.set_title("Gas vs royalty rewards by role (final totals)")
    else:
        ax_bottom.text(0.5, 0.5, "No reward events recorded", ha="center", va="center")
        ax_bottom.set_axis_off()
    fig.tight_layout()
    return fig


def plot_dag_snapshot(
    model: BitRewardsModel,
    max_nodes: int = 50,
    include_true_vs_observed: bool = False,
) -> plt.Figure:
    graph: ContributionGraph = model.contribution_graph
    full_graph = graph.to_networkx()
    nodes = list(full_graph.nodes())

    def select_nodes_with_edges() -> set[str]:
        if len(nodes) <= max_nodes:
            return set(nodes)
        selected = list(nodes[-max_nodes:])
        selected_set = set(selected)
        index = 0
        while len(selected_set) < max_nodes and index < len(selected):
            node = selected[index]
            index += 1
            for parent in full_graph.predecessors(node):
                if len(selected_set) >= max_nodes:
                    break
                selected_set.add(parent)
            for child in full_graph.successors(node):
                if len(selected_set) >= max_nodes:
                    break
                selected_set.add(child)
        if len(selected_set) > max_nodes:
            selected_list = list(selected_set)
            selected_set = set(selected_list[-max_nodes:])
        return selected_set

    selected_nodes = select_nodes_with_edges()
    G = full_graph.subgraph(selected_nodes).copy()
    if G.number_of_edges() == 0 and full_graph.number_of_edges() > 0:
        nodes_with_edges = [node for edge in full_graph.edges() for node in edge]
        if len(nodes_with_edges) > max_nodes:
            nodes_with_edges = nodes_with_edges[-max_nodes:]
        G = full_graph.subgraph(nodes_with_edges).copy()
    pos = nx.spring_layout(G, seed=42)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_title("Contribution DAG snapshot")
    node_colors = []
    for node_id in G.nodes():
        contribution = model.contributions.get(node_id)
        if contribution is None:
            node_colors.append("lightgray")
            continue
        if contribution.contribution_type is ContributionType.FUNDING or contribution.kind == "funding":
            node_colors.append("orange")
        elif contribution.kind in {"reviewer", "educator", "curator", "moderator", "facilitator"}:
            node_colors.append("green")
        else:
            node_colors.append("blue")
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, ax=ax, node_size=140)
    nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        arrows=True,
        alpha=0.7,
        width=1.8,
        edge_color="#555555",
        arrowsize=10,
        connectionstyle="arc3,rad=0.08",
    )
    misattributed: list[str] = []
    if include_true_vs_observed:
        for node_id in G.nodes():
            contribution = model.contributions.get(node_id)
            if contribution is None:
                continue
            true_parents = set(contribution.true_parents or [])
            observed_parents = set(contribution.parents or [])
            if true_parents and observed_parents != true_parents:
                misattributed.append(node_id)
        if misattributed:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=misattributed,
                node_color="red",
                node_size=160,
                ax=ax,
                alpha=0.6,
            )
    ax.axis("off")
    from matplotlib.patches import Patch

    legend_handles = [
        Patch(color="blue"),
        Patch(color="green"),
        Patch(color="orange"),
    ]
    legend_labels = [
        "core/other",
        "supporting",
        "funding",
    ]
    if misattributed:
        legend_handles.append(Patch(color="red", alpha=0.6))
        legend_labels.append("misattributed")
    legend = ax.legend(
        legend_handles,
        legend_labels,
        loc="lower left",
        bbox_to_anchor=(-0.02, -0.02),
        frameon=False,
        borderaxespad=0.0,
    )
    legend.set_in_layout(False)
    return fig


def plot_ai_tracing_panel(
    metrics: SimulationMetrics,
    model: BitRewardsModel,
) -> plt.Figure:
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10, 4))
    tm = metrics.tracing_metrics or {}
    labels = ["true_links", "detected_true_links", "false_positive_links", "missed_true_links"]
    values = [tm.get(key, 0) for key in labels]
    ax_left.bar(labels, values)
    ax_left.set_title("AI tracing link metrics")
    ax_left.set_ylabel("Count")
    ax_left.tick_params(axis="x", rotation=45)
    reward_df = metrics.reward_events
    if reward_df.empty:
        ax_right.text(0.5, 0.5, "No reward events", ha="center", va="center")
        ax_right.axis("off")
        fig.tight_layout()
        return fig

    def is_true_ancestor(recipient_id: int, source_contribution_id: str) -> bool:
        owned = [cid for cid, c in model.contributions.items() if c.owner_id == recipient_id]
        if not owned:
            return False
        if source_contribution_id not in model.contributions:
            return False
        ancestors = {source_contribution_id}
        stack = list(model.contributions[source_contribution_id].true_parents)
        while stack:
            parent_id = stack.pop()
            if parent_id in ancestors:
                continue
            ancestors.add(parent_id)
            parent_contribution = model.contributions.get(parent_id)
            if parent_contribution:
                stack.extend(parent_contribution.true_parents or [])
        return any(cid in ancestors for cid in owned)

    true_amount = 0.0
    non_true_amount = 0.0
    for _, row in reward_df.iterrows():
        recipient_id = int(row["recipient_id"])
        source_cid = str(row["source_contribution_id"])
        if is_true_ancestor(recipient_id, source_cid):
            true_amount += float(row["amount"])
        else:
            non_true_amount += float(row["amount"])
    ax_right.bar(["true_ancestors", "non_true"], [true_amount, non_true_amount])
    ax_right.set_title("Rewards to true vs non-true ancestors")
    ax_right.set_ylabel("Total rewards")
    fig.tight_layout()
    return fig


def plot_life_of_contribution(
    model: BitRewardsModel,
    metrics: SimulationMetrics,
    contribution_id: str,
) -> plt.Figure:
    reward_df = metrics.reward_events
    if reward_df.empty or contribution_id not in model.contributions:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No data for contribution", ha="center", va="center")
        ax.axis("off")
        return fig
    contribution = model.contributions[contribution_id]
    owner_id = contribution.owner_id
    graph = model.contribution_graph.to_networkx()
    descendants = set()
    if contribution_id in graph.nodes():
        descendants = nx.descendants(graph, contribution_id)
    relevant_roots = {contribution_id} | descendants
    funding_contributions = [
        cid
        for cid, c in model.contributions.items()
        if c.contribution_type is ContributionType.FUNDING and contribution_id in (c.parents or [])
    ]
    funding_owner_ids = {model.contributions[cid].owner_id for cid in funding_contributions}
    df = reward_df[reward_df["source_contribution_id"].isin(relevant_roots)].copy()
    if df.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No rewards associated with this contribution", ha="center", va="center")
        ax.axis("off")
        return fig
    df["step"] = df["step"].astype(int)
    df.sort_values("step", inplace=True)

    def bucket_row(row: pd.Series) -> str:
        recipient_id = int(row["recipient_id"])
        if recipient_id == owner_id:
            return "owner"
        if recipient_id in funding_owner_ids:
            return "funding_investors"
        return "others"

    df["bucket"] = df.apply(bucket_row, axis=1)
    pivot = (
        df.groupby(["step", "bucket"])["amount"]
        .sum()
        .reset_index()
        .pivot_table(index="step", columns="bucket", values="amount", aggfunc="sum")
        .fillna(0.0)
        .sort_index()
    )
    cumsum = pivot.cumsum()
    fig, ax = plt.subplots(figsize=(8, 4))
    for column in cumsum.columns:
        ax.plot(cumsum.index, cumsum[column], label=column)
    ax.set_xlabel("Step")
    ax.set_ylabel("Cumulative rewards")
    ax.set_title(f"Life of contribution {contribution_id}")
    ax.legend(loc="upper left")
    return fig
