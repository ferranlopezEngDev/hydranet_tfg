"""System containers for assembled H-based hydraulic networks.

The goal of this module is to keep the canonical network structure very
simple:

- one dictionary for nodes;
- one dictionary for ordered connections.

We intentionally do not store adjacency structures here. Different
solvers may want different auxiliary representations, and those can be
built temporarily from this canonical model.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from math import isfinite

from src.contracts import Connection

from .nodes import Node


class ConnectionEntry:
    """Store one hydraulic connection together with its ordered nodes."""

    __slots__ = ("connection", "node1Id", "node2Id")

    def __init__(
        self,
        connection: Connection,
        node1Id: str,
        node2Id: str,
    ) -> None:
        self.replace(
            connection=connection,
            node1Id=node1Id,
            node2Id=node2Id,
        )

    def setConnection(self, connection: Connection) -> None:
        """Replace only the hydraulic element stored in the entry."""
        self._requireConnection(connection)
        self.connection = connection

    def setNode1Id(self, node1Id: str) -> None:
        """Replace the first endpoint while preserving entry consistency."""
        self._requireEndpointIds(node1Id, self.node2Id)
        self.node1Id = node1Id

    def setNode2Id(self, node2Id: str) -> None:
        """Replace the second endpoint while preserving entry consistency."""
        self._requireEndpointIds(self.node1Id, node2Id)
        self.node2Id = node2Id

    def replace(
        self,
        connection: Connection,
        node1Id: str,
        node2Id: str,
    ) -> None:
        """
        Replace the full content of the entry.

        This is the class-level equivalent of removing and re-adding the
        entry while preserving the outer connection id.
        """
        self._requireConnection(connection)
        self._requireEndpointIds(node1Id, node2Id)

        self.connection = connection
        self.node1Id = node1Id
        self.node2Id = node2Id

    def containsNode(self, nodeId: str) -> bool:
        """Return whether the requested node is one end of the connection."""
        return nodeId == self.node1Id or nodeId == self.node2Id

    def getOtherNodeId(self, nodeId: str) -> str:
        """Return the node id at the opposite end of the connection."""
        if nodeId == self.node1Id:
            return self.node2Id

        if nodeId == self.node2Id:
            return self.node1Id

        raise KeyError(f"Node '{nodeId}' does not belong to this connection")

    def getFlowLeavingNode(
        self,
        nodeId: str,
        nodeHead: float,
        otherNodeHead: float,
    ) -> float:
        """
        Return the signed flow contribution seen as leaving `nodeId`.

        The internal `Connection` object always uses the ordered pair
        `(node1Id, node2Id)` as its positive direction. When the caller
        asks for the flow leaving `node2Id`, the sign must therefore be
        inverted.
        """
        if nodeId == self.node1Id:
            return self.connection.getFlowRate(nodeHead, otherNodeHead)

        if nodeId == self.node2Id:
            return -self.connection.getFlowRate(otherNodeHead, nodeHead)

        raise KeyError(f"Node '{nodeId}' does not belong to this connection")

    @staticmethod
    def _requireConnection(connection: Connection) -> None:
        """Raise an explicit error when the object is not a Connection."""
        if not isinstance(connection, Connection):
            raise TypeError("connection must implement the Connection contract")

    @staticmethod
    def _requireEndpointIds(node1Id: str, node2Id: str) -> None:
        """Validate the ordered endpoint ids stored in the entry."""
        if not node1Id or not node2Id:
            raise ValueError("node1Id and node2Id must be non-empty")

        if node1Id == node2Id:
            raise ValueError("A connection cannot connect a node to itself")


class HydraulicSystem:
    """
    Canonical container for a hydraulic system in H-formulation.

    This object owns only the persistent network description. Solver
    indices, adjacency caches, sparse assembly data, and other numerical
    helpers should stay outside unless they become broadly shared.
    """

    __slots__ = ("nodes", "connections")

    def __init__(
        self,
        nodes: Mapping[str, Node] | None = None,
        connections: Mapping[str, ConnectionEntry] | None = None,
    ) -> None:
        self.nodes: dict[str, Node] = {}
        self.connections: dict[str, ConnectionEntry] = {}

        if nodes is not None:
            for nodeId, node in nodes.items():
                self.addNode(nodeId, node)

        if connections is not None:
            for connectionId, connectionEntry in connections.items():
                self.addConnectionEntry(connectionId, connectionEntry)

    def addNode(self, nodeId: str, node: Node) -> None:
        """Register one node in the system."""
        self._requireNewNodeId(nodeId)
        self._requireNodeObject(node)
        self.nodes[nodeId] = node

    def removeNode(
        self,
        nodeId: str,
        *,
        removeIncidentConnections: bool = False,
    ) -> Node:
        """
        Remove one node from the system and return it.

        By default, the operation is rejected when there are still
        connections attached to the node so the structure cannot become
        inconsistent by accident.
        """
        self._requireNode(nodeId)

        incidentConnectionIds: tuple[str, ...] = tuple(
            connectionId
            for connectionId, _ in self.iterConnectionsForNode(nodeId)
        )

        if incidentConnectionIds and not removeIncidentConnections:
            raise ValueError(
                "Cannot remove node "
                f"'{nodeId}' because it is referenced by connections: "
                + ", ".join(sorted(incidentConnectionIds))
            )

        for connectionId in incidentConnectionIds:
            self.removeConnection(connectionId)

        return self.nodes.pop(nodeId)

    def replaceNode(self, nodeId: str, node: Node) -> Node:
        """
        Replace the node stored under `nodeId` and return the previous one.

        This is the system-level equivalent of removing and re-adding the
        node while preserving its id.
        """
        self._requireNode(nodeId)
        self._requireNodeObject(node)

        previousNode: Node = self.nodes[nodeId]
        self.nodes[nodeId] = node
        return previousNode

    def addConnectionEntry(
        self,
        connectionId: str,
        connectionEntry: ConnectionEntry,
    ) -> None:
        """Register one pre-built connection entry in the system."""
        self._requireNewConnectionId(connectionId)
        self._requireConnectionEntryObject(connectionEntry)
        self._requireNode(connectionEntry.node1Id)
        self._requireNode(connectionEntry.node2Id)
        self.connections[connectionId] = connectionEntry

    def addConnection(
        self,
        connectionId: str,
        connection: Connection,
        node1Id: str,
        node2Id: str,
    ) -> None:
        """Register one ordered connection between two existing nodes."""
        self.addConnectionEntry(
            connectionId=connectionId,
            connectionEntry=ConnectionEntry(
                connection=connection,
                node1Id=node1Id,
                node2Id=node2Id,
            ),
        )

    def removeConnection(self, connectionId: str) -> ConnectionEntry:
        """Remove one connection from the system and return it."""
        self._requireConnectionId(connectionId)
        return self.connections.pop(connectionId)

    def replaceConnectionEntry(
        self,
        connectionId: str,
        connectionEntry: ConnectionEntry,
    ) -> ConnectionEntry:
        """
        Replace the full connection entry while preserving its id.

        This is the system-level equivalent of removing and re-adding the
        connection while preserving the external id.
        """
        self._requireConnectionId(connectionId)
        self._requireConnectionEntryObject(connectionEntry)
        self._requireNode(connectionEntry.node1Id)
        self._requireNode(connectionEntry.node2Id)

        previousConnectionEntry: ConnectionEntry = self.connections[connectionId]
        self.connections[connectionId] = connectionEntry
        return previousConnectionEntry

    def replaceConnection(
        self,
        connectionId: str,
        connection: Connection,
        node1Id: str,
        node2Id: str,
    ) -> ConnectionEntry:
        """
        Replace the content of one connection while preserving its id.

        This is the most direct API when the caller wants to update the
        hydraulic element and/or its ordered endpoints together.
        """
        return self.replaceConnectionEntry(
            connectionId=connectionId,
            connectionEntry=ConnectionEntry(
                connection=connection,
                node1Id=node1Id,
                node2Id=node2Id,
            ),
        )

    def getNode(self, nodeId: str) -> Node:
        """Return the node stored under `nodeId`."""
        self._requireNode(nodeId)
        return self.nodes[nodeId]

    def getConnectionEntry(self, connectionId: str) -> ConnectionEntry:
        """Return the ordered connection entry stored under `connectionId`."""
        self._requireConnectionId(connectionId)
        return self.connections[connectionId]

    def getBoundaryNodeIds(self) -> tuple[str, ...]:
        """Return the ids of nodes with prescribed piezometric head."""
        return tuple(
            nodeId for nodeId, node in self.nodes.items() if node.isBoundary()
        )

    def getUnknownHeadNodeIds(self) -> tuple[str, ...]:
        """
        Return the ids of nodes whose head is part of the solve vector.

        The order is the dictionary insertion order. Solvers can pass an
        explicit `nodeIds` sequence when they need a different or stable
        external ordering.
        """
        return tuple(
            nodeId for nodeId, node in self.nodes.items() if not node.isBoundary()
        )

    def getNodeCount(self) -> int:
        """Return the number of nodes stored in the system."""
        return len(self.nodes)

    def getConnectionCount(self) -> int:
        """Return the number of connections stored in the system."""
        return len(self.connections)

    def getConnectedNodeIds(self) -> tuple[str, ...]:
        """Return node ids that appear in at least one connection."""
        connectedNodeIds: set[str] = set()

        for connectionEntry in self.connections.values():
            if connectionEntry.node1Id in self.nodes:
                connectedNodeIds.add(connectionEntry.node1Id)

            if connectionEntry.node2Id in self.nodes:
                connectedNodeIds.add(connectionEntry.node2Id)

        return tuple(
            nodeId for nodeId in self.nodes if nodeId in connectedNodeIds
        )

    def getIsolatedNodeIds(self) -> tuple[str, ...]:
        """Return node ids that are not connected to any stored connection."""
        connectedNodeIds: set[str] = set(self.getConnectedNodeIds())
        return tuple(
            nodeId for nodeId in self.nodes if nodeId not in connectedNodeIds
        )

    def buildAdjacencyMap(self) -> dict[str, tuple[str, ...]]:
        """
        Build a temporary undirected adjacency map from the stored topology.

        Parallel connections are allowed. The adjacency map records each
        neighboring node once because it is meant for topology checks,
        not for hydraulic residual assembly.
        """
        adjacencyLists: dict[str, list[str]] = {
            nodeId: [] for nodeId in self.nodes
        }

        for connectionEntry in self.connections.values():
            node1Id: str = connectionEntry.node1Id
            node2Id: str = connectionEntry.node2Id

            if node1Id not in adjacencyLists or node2Id not in adjacencyLists:
                continue

            if node2Id not in adjacencyLists[node1Id]:
                adjacencyLists[node1Id].append(node2Id)

            if node1Id not in adjacencyLists[node2Id]:
                adjacencyLists[node2Id].append(node1Id)

        return {
            nodeId: tuple(neighborIds)
            for nodeId, neighborIds in adjacencyLists.items()
        }

    def getConnectedComponents(self) -> tuple[tuple[str, ...], ...]:
        """
        Return connected node groups in the current undirected topology.

        Isolated nodes are returned as one-node components. Component
        order follows node insertion order.
        """
        adjacencyMap: dict[str, tuple[str, ...]] = self.buildAdjacencyMap()
        visitedNodeIds: set[str] = set()
        components: list[tuple[str, ...]] = []

        for startNodeId in self.nodes:
            if startNodeId in visitedNodeIds:
                continue

            componentNodeIds: list[str] = []
            pendingNodeIds: list[str] = [startNodeId]
            visitedNodeIds.add(startNodeId)
            pendingIndex: int = 0

            while pendingIndex < len(pendingNodeIds):
                nodeId: str = pendingNodeIds[pendingIndex]
                pendingIndex += 1
                componentNodeIds.append(nodeId)

                for neighborNodeId in adjacencyMap[nodeId]:
                    if neighborNodeId in visitedNodeIds:
                        continue

                    visitedNodeIds.add(neighborNodeId)
                    pendingNodeIds.append(neighborNodeId)

            components.append(tuple(componentNodeIds))

        return tuple(components)

    def hasSingleNetwork(self) -> bool:
        """Return whether all stored nodes belong to one connected network."""
        connectedComponents: tuple[tuple[str, ...], ...] = (
            self.getConnectedComponents()
        )
        return len(connectedComponents) == 1

    def getTopologyInfo(self) -> dict[str, object]:
        """Return a compact diagnostic summary of the stored topology."""
        connectedComponents: tuple[tuple[str, ...], ...] = (
            self.getConnectedComponents()
        )
        isolatedNodeIds: tuple[str, ...] = self.getIsolatedNodeIds()

        return {
            "nodeCount": self.getNodeCount(),
            "connectionCount": self.getConnectionCount(),
            "boundaryNodeIds": self.getBoundaryNodeIds(),
            "unknownHeadNodeIds": self.getUnknownHeadNodeIds(),
            "connectedNodeIds": self.getConnectedNodeIds(),
            "isolatedNodeIds": isolatedNodeIds,
            "connectedComponents": connectedComponents,
            "connectedComponentCount": len(connectedComponents),
            "hasIsolatedNodes": bool(isolatedNodeIds),
            "hasSingleNetwork": self.hasSingleNetwork(),
        }

    def getNodeHead(
        self,
        nodeId: str,
        headOverrides: Mapping[str, float] | None = None,
        problemScale: float = 1.0,
    ) -> float:
        """
        Return the head associated with `nodeId`.

        `headOverrides` lets a numerical method evaluate the residual
        without mutating the node objects stored in the system.

        `problemScale` scales stored node heads. Overrides are assumed
        to already be expressed in the scaled problem being evaluated.

        This distinction is important for solver callbacks: unknown
        heads usually arrive through `headOverrides`, while fixed
        boundary heads are read from the stored nodes.
        """
        problemScale = self._requireProblemScale(problemScale)
        self._requireNode(nodeId)

        if headOverrides is not None and nodeId in headOverrides:
            # Overrides are trial values from the nonlinear solver. They
            # must not be scaled again, otherwise continuation solves
            # would shrink the same unknown twice.
            return float(headOverrides[nodeId])

        return problemScale * float(self.nodes[nodeId].getPiezometricHead())

    def buildHeadVector(
        self,
        nodeIds: Sequence[str] | None = None,
        problemScale: float = 1.0,
    ) -> tuple[float, ...]:
        """
        Return the current head vector for the requested node ordering.

        When `nodeIds` is omitted, the non-boundary nodes are used in the
        dictionary insertion order.

        `problemScale` scales stored node heads so continuation solves
        can start from an easier version of the same problem.

        The returned tuple is positional: entry `i` belongs to
        `nodeIds[i]`. Keep the same ordering when converting SciPy trial
        vectors back with `buildHeadOverrides(...)`.
        """
        problemScale = self._requireProblemScale(problemScale)

        if nodeIds is None:
            nodeIds = self.getUnknownHeadNodeIds()

        return tuple(
            self.getNodeHead(nodeId, problemScale=problemScale)
            for nodeId in nodeIds
        )

    def buildHeadOverrides(
        self,
        nodeIds: Sequence[str],
        headValues: Sequence[float],
    ) -> dict[str, float]:
        """
        Convert a solver vector into a `node id -> H` mapping.

        This small helper is convenient when a SciPy callback receives
        only a dense vector but the residual evaluation works more
        naturally with named nodes.

        No scaling is applied here. The values are interpreted as the
        actual trial heads of the problem currently being evaluated.
        """
        if len(nodeIds) != len(headValues):
            raise ValueError("nodeIds and headValues must have the same length")

        return {
            nodeId: float(headValue)
            for nodeId, headValue in zip(nodeIds, headValues)
        }

    def iterConnectionsForNode(
        self,
        nodeId: str,
    ) -> Iterator[tuple[str, ConnectionEntry]]:
        """
        Yield every connection incident to `nodeId`.

        No permanent adjacency structure is stored in the system, so this
        helper performs a direct scan over the connection dictionary.
        """
        self._requireNode(nodeId)

        for connectionId, connectionEntry in self.connections.items():
            if connectionEntry.containsNode(nodeId):
                yield connectionId, connectionEntry

    def evaluateNodalBalance(
        self,
        nodeId: str,
        headOverrides: Mapping[str, float] | None = None,
        problemScale: float = 1.0,
    ) -> float:
        """
        Evaluate the continuity residual for one node.

        The sign convention is the one used in the TFG:

        - external nodal flow is positive when it leaves the node;
        - connection flow is positive when it leaves the node;
        - the continuity equation is therefore `Qi + sum(Qij) = 0`.

        `problemScale` scales stored heads and external nodal flows.
        This is useful for continuation solves where values below `1`
        represent easier intermediate problems.
        """
        problemScale = self._requireProblemScale(problemScale)
        node: Node = self.getNode(nodeId)
        nodeHead: float = self.getNodeHead(
            nodeId,
            headOverrides,
            problemScale=problemScale,
        )

        # Start from the prescribed external nodal contribution and then
        # add every hydraulic connection that leaves the node.
        nodalBalance: float = problemScale * float(node.getExternalFlow())

        for _, connectionEntry in self.iterConnectionsForNode(nodeId):
            otherNodeId: str = connectionEntry.getOtherNodeId(nodeId)
            # The other end may be another unknown node present in
            # `headOverrides`, or a boundary node read from storage.
            otherNodeHead: float = self.getNodeHead(
                otherNodeId,
                headOverrides,
                problemScale=problemScale,
            )
            nodalBalance += connectionEntry.getFlowLeavingNode(
                nodeId=nodeId,
                nodeHead=nodeHead,
                otherNodeHead=otherNodeHead,
            )

        return nodalBalance

    def buildResidualVector(
        self,
        nodeIds: Sequence[str] | None = None,
        headOverrides: Mapping[str, float] | None = None,
        problemScale: float = 1.0,
    ) -> tuple[float, ...]:
        """
        Return the continuity residuals for the requested node ordering.

        This is the most direct bridge between the canonical system data
        structure and a SciPy nonlinear solver callback.

        `problemScale` must be in `[0, 1]`. A value of `1` evaluates the
        real problem. Smaller values scale stored heads and external
        nodal flows for continuation-style solves.

        The residual tuple uses the same ordering as `nodeIds`, so it is
        safe to return directly from a SciPy callback whose input vector
        was built with the same node ordering.
        """
        problemScale = self._requireProblemScale(problemScale)

        if nodeIds is None:
            nodeIds = self.getUnknownHeadNodeIds()

        return tuple(
            self.evaluateNodalBalance(
                nodeId=nodeId,
                headOverrides=headOverrides,
                problemScale=problemScale,
            )
            for nodeId in nodeIds
        )

    def validate(
        self,
        *,
        requireConnectedNodes: bool = False,
        requireSingleNetwork: bool = False,
        requireBoundaryInEachNetwork: bool = False,
    ) -> None:
        """
        Check that the stored structure is self-consistent.

        `requireConnectedNodes` is optional because partially built
        systems may be valid during step-by-step construction.
        """
        self.validateTopology(
            requireConnectedNodes=requireConnectedNodes,
            requireSingleNetwork=requireSingleNetwork,
            requireBoundaryInEachNetwork=requireBoundaryInEachNetwork,
        )

    def validateTopology(
        self,
        *,
        requireConnectedNodes: bool = True,
        requireSingleNetwork: bool = True,
        requireBoundaryInEachNetwork: bool = True,
    ) -> None:
        """
        Check whether the stored topology is acceptable for solving.

        By default this method is stricter than `validate(...)`: it
        expects every node to be connected, all nodes to belong to one
        network, and each connected component to contain at least one
        prescribed-head boundary node.
        """
        self._validateConnectionReferences()

        isolatedNodeIds: tuple[str, ...] = self.getIsolatedNodeIds()

        if requireConnectedNodes and isolatedNodeIds:
            raise ValueError(
                "The system contains isolated nodes: "
                + ", ".join(sorted(isolatedNodeIds))
            )

        connectedComponents: tuple[tuple[str, ...], ...] = (
            self.getConnectedComponents()
        )

        if requireSingleNetwork and len(connectedComponents) != 1:
            raise ValueError(
                "The system must contain exactly one connected network; "
                f"found {len(connectedComponents)} components: "
                + self._formatNodeGroups(connectedComponents)
            )

        if not requireBoundaryInEachNetwork:
            return

        componentsWithoutBoundary: list[tuple[str, ...]] = [
            componentNodeIds
            for componentNodeIds in connectedComponents
            if not any(
                self.nodes[nodeId].isBoundary()
                for nodeId in componentNodeIds
            )
        ]

        if componentsWithoutBoundary:
            raise ValueError(
                "Each connected network must contain at least one boundary node; "
                "missing boundaries in: "
                + self._formatNodeGroups(componentsWithoutBoundary)
            )

    def _validateConnectionReferences(self) -> None:
        """Raise when any connection points to unknown nodes."""
        for connectionId, connectionEntry in self.connections.items():
            if connectionEntry.node1Id not in self.nodes:
                raise ValueError(
                    f"Connection '{connectionId}' references unknown node "
                    f"'{connectionEntry.node1Id}'"
                )

            if connectionEntry.node2Id not in self.nodes:
                raise ValueError(
                    f"Connection '{connectionId}' references unknown node "
                    f"'{connectionEntry.node2Id}'"
                )

    @staticmethod
    def _requireNodeObject(node: Node) -> None:
        """Raise an explicit error when the object is not a Node."""
        if not isinstance(node, Node):
            raise TypeError("node must be a Node object")

    @staticmethod
    def _requireConnectionEntryObject(connectionEntry: ConnectionEntry) -> None:
        """Raise an explicit error when the object is not a ConnectionEntry."""
        if not isinstance(connectionEntry, ConnectionEntry):
            raise TypeError(
                "connectionEntry must be an instance of ConnectionEntry"
            )

    def _requireNode(self, nodeId: str) -> None:
        """Raise an explicit error when the requested node does not exist."""
        if nodeId not in self.nodes:
            raise KeyError(f"Unknown node id '{nodeId}'")

    def _requireNewNodeId(self, nodeId: str) -> None:
        """Validate that a node id is usable and still free."""
        if not nodeId:
            raise ValueError("nodeId must be a non-empty string")

        if nodeId in self.nodes:
            raise ValueError(f"Node '{nodeId}' is already registered")

    def _requireConnectionId(self, connectionId: str) -> None:
        """Raise an explicit error when the requested connection is missing."""
        if connectionId not in self.connections:
            raise KeyError(f"Unknown connection id '{connectionId}'")

    def _requireNewConnectionId(self, connectionId: str) -> None:
        """Validate that a connection id is usable and still free."""
        if not connectionId:
            raise ValueError("connectionId must be a non-empty string")

        if connectionId in self.connections:
            raise ValueError(
                f"Connection '{connectionId}' is already registered"
            )

    @staticmethod
    def _requireProblemScale(problemScale: float) -> float:
        """Validate the continuation scale used for residual evaluation."""
        numericProblemScale: float = float(problemScale)

        if (
            not isfinite(numericProblemScale)
            or numericProblemScale < 0.0
            or numericProblemScale > 1.0
        ):
            raise ValueError("problemScale must be between 0 and 1")

        return numericProblemScale

    @staticmethod
    def _formatNodeGroups(nodeGroups: Sequence[Sequence[str]]) -> str:
        """Format connected components for readable diagnostics."""
        if not nodeGroups:
            return "<none>"

        return "; ".join(
            "(" + ", ".join(nodeGroup) + ")"
            for nodeGroup in nodeGroups
        )
