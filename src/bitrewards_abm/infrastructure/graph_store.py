from __future__ import annotations

from typing import List

import networkx as nx


class ContributionGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_contribution_node(self, contribution_id: str) -> None:
        self.graph.add_node(contribution_id)

    def add_parent_child_edge(self, parent_id: str, child_id: str, split_fraction: float) -> None:
        self.graph.add_edge(parent_id, child_id, split=split_fraction)

    def contribution_exists(self, contribution_id: str) -> bool:
        return contribution_id in self.graph.nodes

    def parent_count(self, contribution_id: str) -> int:
        if contribution_id not in self.graph.nodes:
            return 0
        return len(list(self.graph.predecessors(contribution_id)))

    def get_parents(self, contribution_id: str) -> List[str]:
        if contribution_id not in self.graph.nodes:
            return []
        return list(self.graph.predecessors(contribution_id))

    def get_split_fraction(self, parent_id: str, child_id: str) -> float:
        if not self.graph.has_edge(parent_id, child_id):
            return 0.0
        attributes = self.graph[parent_id][child_id]
        value = attributes.get("split", 0.0)
        return float(value)
