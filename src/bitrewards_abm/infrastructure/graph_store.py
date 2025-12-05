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
        remaining: List[tuple[str, float]] = [(root_id, total_value)]
        visited = set()
        while remaining:
            current_id, pool_value = remaining.pop()
            if pool_value <= 0.0:
                continue
            key = (current_id, pool_value)
            if key in visited:
                continue
            visited.add(key)
            parents = self.get_parents(current_id)
            if not parents:
                shares[current_id] = shares.get(current_id, 0.0) + pool_value
                continue
            split_values = [self.get_split_fraction(parent, current_id) for parent in parents]
            clipped_splits = [max(0.0, min(1.0, value)) for value in split_values]
            total_split = sum(clipped_splits)
            if total_split == 0.0:
                shares[current_id] = shares.get(current_id, 0.0) + pool_value
                continue
            if total_split > 1.0:
                normalized_splits = [value / total_split for value in clipped_splits]
            else:
                normalized_splits = clipped_splits
            parent_amounts: List[float] = []
            total_parent_amount = 0.0
            for value in normalized_splits:
                amount = pool_value * value
                parent_amounts.append(amount)
                total_parent_amount += amount
            own_amount = pool_value - total_parent_amount
            if own_amount < 0.0:
                own_amount = 0.0
            if own_amount > 0.0:
                shares[current_id] = shares.get(current_id, 0.0) + own_amount
            for parent_id, amount in zip(parents, parent_amounts):
                if amount <= 0.0:
                    continue
                remaining.append((parent_id, amount))
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
