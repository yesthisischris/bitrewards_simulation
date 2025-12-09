from __future__ import annotations

import math

from bitrewards_abm.infrastructure.graph_store import ContributionGraph


def test_linear_chain_single_path() -> None:
    graph = ContributionGraph()
    graph.add_contribution_node("c0")
    graph.add_contribution_node("c1")
    graph.add_contribution_node("c2")
    graph.add_parent_child_edge("c0", "c1", split_fraction=0.5)
    graph.add_parent_child_edge("c1", "c2", split_fraction=0.5)
    total_value = 100.0
    shares = graph.compute_royalty_shares(start_id="c2", total_value=total_value)
    assert math.isclose(shares.get("c2", 0.0), 50.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("c1", 0.0), 25.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("c0", 0.0), 25.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(sum(shares.values()), total_value, rel_tol=1e-9, abs_tol=1e-9)


def test_binary_choice_prefers_highest_split() -> None:
    graph = ContributionGraph()
    graph.add_contribution_node("p_low")
    graph.add_contribution_node("p_high")
    graph.add_contribution_node("child")
    graph.add_parent_child_edge("p_low", "child", split_fraction=0.4)
    graph.add_parent_child_edge("p_high", "child", split_fraction=0.6)
    total_value = 120.0
    shares = graph.compute_royalty_shares(start_id="child", total_value=total_value)
    assert math.isclose(shares.get("child", 0.0), 48.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("p_high", 0.0), 72.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(sum(shares.values()), total_value, rel_tol=1e-9, abs_tol=1e-9)


def test_diamond_selects_single_branch() -> None:
    graph = ContributionGraph()
    graph.add_contribution_node("root")
    graph.add_contribution_node("a")
    graph.add_contribution_node("b")
    graph.add_contribution_node("leaf")
    graph.add_parent_child_edge("root", "a", split_fraction=0.5)
    graph.add_parent_child_edge("root", "b", split_fraction=0.5)
    graph.add_parent_child_edge("a", "leaf", split_fraction=0.5)
    graph.add_parent_child_edge("b", "leaf", split_fraction=0.5)
    total_value = 100.0
    shares = graph.compute_royalty_shares(start_id="leaf", total_value=total_value)
    assert math.isclose(shares.get("leaf", 0.0), 50.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("a", 0.0), 25.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("root", 0.0), 25.0, rel_tol=1e-9, abs_tol=1e-9)
    assert "b" not in shares or math.isclose(shares.get("b", 0.0), 0.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(sum(shares.values()), total_value, rel_tol=1e-9, abs_tol=1e-9)
