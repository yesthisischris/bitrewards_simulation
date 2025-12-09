from __future__ import annotations

import math

from bitrewards_abm.infrastructure.graph_store import ContributionGraph


def test_canonical_dag_royalty_splits() -> None:
    graph = ContributionGraph()
    graph.add_contribution_node("discovery-01")
    graph.add_contribution_node("funding-01")
    graph.add_contribution_node("code-01")
    graph.add_contribution_node("derivative-01")
    graph.add_parent_child_edge("discovery-01", "code-01", split_fraction=0.5)
    graph.add_parent_child_edge("funding-01", "code-01", split_fraction=0.5, edge_type="funding")
    graph.add_parent_child_edge("code-01", "derivative-01", split_fraction=0.5)
    total_value = 1000.0
    shares = graph.compute_royalty_shares(start_id="derivative-01", total_value=total_value)
    assert math.isclose(shares.get("derivative-01", 0.0), 500.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("funding-01", 0.0), 250.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(shares.get("code-01", 0.0), 250.0, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(sum(shares.values()), total_value, rel_tol=1e-9, abs_tol=1e-9)


def test_root_node_gets_full_value_when_no_parents() -> None:
    graph = ContributionGraph()
    graph.add_contribution_node("root-01")
    total_value = 42.0
    shares = graph.compute_royalty_shares(start_id="root-01", total_value=total_value)
    assert math.isclose(shares.get("root-01", 0.0), total_value, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(sum(shares.values()), total_value, rel_tol=1e-9, abs_tol=1e-9)
