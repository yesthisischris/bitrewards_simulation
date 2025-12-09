from __future__ import annotations

from typing import Dict, List

import networkx as nx


class ContributionGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_contribution_node(self, contribution_id: str) -> None:
        self.graph.add_node(contribution_id)

    def add_parent_child_edge(self, parent_id: str, child_id: str, split_fraction: float, edge_type: str = "derivative") -> None:
        self.graph.add_edge(parent_id, child_id, split=split_fraction, edge_type=edge_type)

    def add_royalty_edge(self, parent_identifier: str, child_identifier: str, royalty_percent: float, edge_type: str = "derivative") -> None:
        self.add_parent_child_edge(
            parent_id=parent_identifier,
            child_id=child_identifier,
            split_fraction=royalty_percent,
            edge_type=edge_type,
        )

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

    def get_edge_type(self, parent_id: str, child_id: str) -> str:
        if not self.graph.has_edge(parent_id, child_id):
            return "other"
        attributes = self.graph[parent_id][child_id]
        return str(attributes.get("edge_type", "other"))

    def compute_royalty_shares(
        self,
        root_identifier: str | None = None,
        total_value: float = 0.0,
        start_id: str | None = None,
    ) -> Dict[str, float]:
        root_id = root_identifier if root_identifier is not None else start_id
        if total_value <= 0.0 or root_id is None or root_id not in self.graph.nodes:
            return {}
        shares: Dict[str, float] = {}
        current_id = root_id
        pool_value = total_value
        visited = set()
        while pool_value > 0.0 and current_id not in visited:
            visited.add(current_id)
            parents = self.get_parents(current_id)
            if not parents:
                shares[current_id] = shares.get(current_id, 0.0) + pool_value
                break
            parent_splits = [(parent, self.get_split_fraction(parent, current_id)) for parent in parents]
            funding_parents = [
                pair for pair in parent_splits if self.get_edge_type(pair[0], current_id) == "funding"
            ]
            if funding_parents:
                funding_parents.sort(key=lambda x: (-x[1], x[0]))
                selected_parent, selected_split = funding_parents[0]
            else:
                parent_splits.sort(key=lambda x: (-x[1], x[0]))
                selected_parent, selected_split = parent_splits[0]
            split = max(0.0, min(1.0, selected_split))
            own_share = pool_value * (1.0 - split)
            if own_share > 0.0:
                shares[current_id] = shares.get(current_id, 0.0) + own_share
            parent_share = pool_value * split
            if parent_share <= 0.0 or selected_parent is None:
                break
            if self.get_edge_type(selected_parent, current_id) == "funding":
                shares[selected_parent] = shares.get(selected_parent, 0.0) + parent_share
                break
            pool_value = parent_share
            current_id = selected_parent
        return shares

    def to_networkx(self) -> nx.DiGraph:
        graph_copy = nx.DiGraph()
        graph_copy.add_nodes_from(self.graph.nodes)
        for parent, child, data in self.graph.edges(data=True):
            edge_data = dict(data)
            if "split" in data and "royalty_percent" not in edge_data:
                edge_data["royalty_percent"] = data.get("split")
            graph_copy.add_edge(parent, child, **edge_data)
        return graph_copy
