"""Native Pydantic builder graphs within LychD's serial station contract.

Pydantic owns node execution and routing. LychD admits only a single BaseNode
station at a time because its checkpoint and wait-owner law is serial.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic_graph import BaseNode, Decision, EndNode, Graph, GraphBuilder, StartNode
from pydantic_graph.id_types import NodeID
from pydantic_graph.paths import DestinationMarker, LabelMarker, Path
from pydantic_graph.step import NodeStep


def build_serial_graph[StateT, DepsT, OutputT](
    *,
    nodes: Sequence[type[BaseNode[StateT, DepsT, OutputT]]],
    state_type: type[StateT],
    deps_type: type[DepsT],
    output_type: type[OutputT],
    name: str | None = None,
) -> Graph[StateT, DepsT, BaseNode[StateT, DepsT, OutputT], OutputT]:
    """Build a native graph whose first declared node is its fresh entry station."""
    if not nodes:
        msg = "A serial workflow graph requires an entry station."
        raise ValueError(msg)
    builder = GraphBuilder[StateT, DepsT, BaseNode[StateT, DepsT, OutputT], OutputT](
        name=name,
        state_type=state_type,
        deps_type=deps_type,
        input_type=BaseNode[StateT, DepsT, OutputT],
        output_type=output_type,
    )
    builder.add(builder.edge_from(builder.start_node).to(NodeStep(nodes[0])))
    for node in nodes:
        builder.add(builder.node(node))
    graph = builder.build()
    serial_graph_topology(graph)
    return graph


def serial_graph_topology(  # noqa: C901 - validate the closed native node/path vocabulary
    graph: Graph[Any, Any, Any, Any],
) -> tuple[dict[str, type[BaseNode[Any, Any, Any]]], set[tuple[str, str]]]:
    """Validate the supported builder shape and return station/terminal edges.

    Builder-generated decisions describe BaseNode return unions. Their routes
    are transparent to the serial score; forks, joins, transforms, and arbitrary
    function steps have no admitted durable checkpoint contract here.
    """
    for node in graph.nodes.values():
        if not isinstance(node, (NodeStep, StartNode, EndNode, Decision)):
            msg = "Durable workflow graphs support serial BaseNode stations only."
            raise TypeError(msg)
    stations = {str(node.id): node.node_type for node in graph.nodes.values() if isinstance(node, NodeStep)}

    def destinations(path: Path, seen: frozenset[str] = frozenset()) -> set[str]:
        targets = [item for item in path.items if isinstance(item, DestinationMarker)]
        if len(targets) != 1 or any(not isinstance(item, (DestinationMarker, LabelMarker)) for item in path.items):
            msg = "Durable workflow paths require one untransformed serial destination."
            raise ValueError(msg)
        target = str(targets[0].destination_id)
        node = graph.nodes[NodeID(target)]
        if isinstance(node, Decision):
            if target in seen:
                msg = "Durable workflow routing decisions must reach a station."
                raise ValueError(msg)
            return set[str]().union(*(destinations(branch.path, seen | {target}) for branch in node.branches))
        if not isinstance(node, (NodeStep, EndNode)):
            msg = "Durable workflow routing must reach a station or terminal."
            raise TypeError(msg)
        return {target}

    edges: set[tuple[str, str]] = set()
    for source, paths in graph.edges_by_source.items():
        if not isinstance(graph.nodes[source], (NodeStep, StartNode)):
            continue
        if len(paths) != 1:
            msg = "Durable workflow stations require a single serial route."
            raise ValueError(msg)
        edges.update((str(source), target) for target in destinations(paths[0]))
    return stations, edges
