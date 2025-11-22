"""
Unit tests for dependency graph and topological sorting.

Tests the dependency resolution and computation order using NetworkX.
"""

import pytest
import networkx as nx


class TestDependencyGraph:
    """Test dependency graph using NetworkX DiGraph."""

    def test_simple_linear_chain(self):
        """Test a simple linear dependency chain: C -> B -> A."""
        graph = nx.DiGraph()
        graph.add_edge("C", "B")  # C comes before B
        graph.add_edge("B", "A")  # B comes before A

        order = list(nx.topological_sort(graph))

        # C should come before B, B should come before A
        assert order.index("C") < order.index("B")
        assert order.index("B") < order.index("A")

    def test_parallel_dependencies(self):
        """Test parallel dependencies: C is required by both A and B."""
        graph = nx.DiGraph()
        graph.add_edge("C", "A")  # C comes before A
        graph.add_edge("C", "B")  # C comes before B

        order = list(nx.topological_sort(graph))

        # C should come before both A and B
        assert order.index("C") < order.index("A")
        assert order.index("C") < order.index("B")

    def test_diamond_dependency(self):
        """Test diamond dependency: A -> B,C -> D."""
        graph = nx.DiGraph()
        graph.add_edge("A", "B")  # A before B
        graph.add_edge("A", "C")  # A before C
        graph.add_edge("B", "D")  # B before D
        graph.add_edge("C", "D")  # C before D

        order = list(nx.topological_sort(graph))

        # A should come first
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        # B and C should come before D
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_cyclic_dependency_simple(self):
        """Test detection of simple cycle: A -> B -> A."""
        graph = nx.DiGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")  # Cycle!

        with pytest.raises(nx.NetworkXUnfeasible):
            list(nx.topological_sort(graph))

    def test_cyclic_dependency_complex(self):
        """Test detection of complex cycle: A -> B -> C -> A."""
        graph = nx.DiGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")  # Creates cycle

        with pytest.raises(nx.NetworkXUnfeasible):
            list(nx.topological_sort(graph))

    def test_self_dependency(self):
        """Test detection of self-dependency: A -> A."""
        graph = nx.DiGraph()
        graph.add_edge("A", "A")  # A depends on itself

        with pytest.raises(nx.NetworkXUnfeasible):
            list(nx.topological_sort(graph))

    def test_isolated_nodes(self):
        """Test graph with isolated nodes (no dependencies)."""
        graph = nx.DiGraph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")

        order = list(nx.topological_sort(graph))

        # All nodes should be present
        assert len(order) == 3
        assert set(order) == {"A", "B", "C"}

    def test_empty_graph(self):
        """Test empty graph."""
        graph = nx.DiGraph()
        order = list(nx.topological_sort(graph))
        assert order == []

    def test_complex_entity_chain(self):
        """Test realistic entity dependency chain."""
        # Simulating: Source -> Entity1 -> Entity2 -> Entity3 -> Endpoint
        graph = nx.DiGraph()
        graph.add_edge("Source", "Entity1")
        graph.add_edge("Entity1", "Entity2")
        graph.add_edge("Entity2", "Entity3")
        graph.add_edge("Entity3", "Endpoint")

        order = list(nx.topological_sort(graph))

        # Verify order
        assert order.index("Source") < order.index("Entity1")
        assert order.index("Entity1") < order.index("Entity2")
        assert order.index("Entity2") < order.index("Entity3")
        assert order.index("Entity3") < order.index("Endpoint")

    def test_multiple_sources(self):
        """Test entity with multiple parent sources."""
        graph = nx.DiGraph()
        graph.add_edge("SourceA", "EntityCombined")
        graph.add_edge("SourceB", "EntityCombined")

        order = list(nx.topological_sort(graph))

        # Both sources should come before the combined entity
        assert order.index("SourceA") < order.index("EntityCombined")
        assert order.index("SourceB") < order.index("EntityCombined")


class TestEntityDependencyScenarios:
    """Test realistic FDSL entity dependency scenarios."""

    def test_computed_entity_with_parent(self):
        """Test Entity(Parent) dependency."""
        graph = nx.DiGraph()
        graph.add_edge("ParentEntity", "ComputedEntity")

        order = list(nx.topological_sort(graph))
        assert order.index("ParentEntity") < order.index("ComputedEntity")

    def test_multi_parent_entity(self):
        """Test Entity(Parent1, Parent2) dependency."""
        graph = nx.DiGraph()
        graph.add_edge("Parent1", "ChildEntity")
        graph.add_edge("Parent2", "ChildEntity")

        order = list(nx.topological_sort(graph))

        assert order.index("Parent1") < order.index("ChildEntity")
        assert order.index("Parent2") < order.index("ChildEntity")

    def test_entity_hierarchy_three_levels(self):
        """Test three-level entity hierarchy."""
        # Grandparent -> Parent -> Child
        graph = nx.DiGraph()
        graph.add_edge("Grandparent", "Parent")
        graph.add_edge("Parent", "Child")

        order = list(nx.topological_sort(graph))

        assert order == ["Grandparent", "Parent", "Child"]

    def test_detect_cycle_in_entity_hierarchy(self):
        """Test cycle detection in entity hierarchy."""
        graph = nx.DiGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")  # Cycle

        with pytest.raises(nx.NetworkXUnfeasible):
            list(nx.topological_sort(graph))
