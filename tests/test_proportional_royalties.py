from __future__ import annotations

import math

from bitrewards_abm.infrastructure.graph_store import ContributionGraph


def test_proportional_royalties_splits_half_upstream() -> None:
    graph = ContributionGraph()
    graph.add_contribution_node("p1")
    graph.add_contribution_node("p2")
    graph.add_contribution_node("child")
    graph.add_parent_child_edge("p1", "child", split_fraction=0.5)
    graph.add_parent_child_edge("p2", "child", split_fraction=0.5)
    total_value = 100.0
    shares = graph.compute_royalty_shares(
        start_id="child",
        total_value=total_value,
        mode="proportional_50_50",
        keep_fraction=0.5,
    )
    assert math.isclose(shares.get("child", 0.0), 50.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("p1", 0.0), 25.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("p2", 0.0), 25.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(sum(shares.values()), total_value, rel_tol=1e-9, abs_tol=1e-9)
