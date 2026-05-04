"""
This file contains the Query classes mapping incoming rest queries to
different algorithms used in the search api.
"""
import logging
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

import networkx as nx
from depmap_analysis.network_functions.net_functions import SIGNS_TO_INT_SIGN
from indra.explanation.pathfinding import (
    EdgeFilter,
    bfs_search,
    open_dijkstra_search,
    shortest_simple_paths,
)
from indra_db.client.readonly.mesh_ref_counts import get_mesh_ref_counts
from pydantic import BaseModel

from indra_network_search.data_models import *
from indra_network_search.pathfinding import *
from indra_network_search.rest_util import StrEdge, StrNode
from indra_network_search.util.curation_cache import CurationCache

# Constants
INT_PLUS = 0
INT_MINUS = 1

__all__ = [
    "ShortestSimplePathsQuery",
    "BreadthFirstSearchQuery",
    "DijkstraQuery",
    "SharedTargetsQuery",
    "SharedRegulatorsQuery",
    "OntologyQuery",
    "UIQuery",
    "Query",
    "PathQuery",
    "alg_func_mapping",
    "alg_name_query_mapping",
    "SubgraphQuery",
    "MultiInteractorsQuery",
    "MissingParametersError",
    "InvalidParametersError",
]


logger = logging.getLogger(__name__)


class MissingParametersError(Exception):
    """Raise for missing query parameters"""


class InvalidParametersError(Exception):
    """Raise when conflicting or otherwise invalid parameters"""


alg_func_mapping = {
    bfs_search.__name__: bfs_search,
    shortest_simple_paths.__name__: shortest_simple_paths,
    open_dijkstra_search.__name__: open_dijkstra_search,
    shared_parents.__name__: shared_parents,
    shared_interactors.__name__: shared_interactors,
    "shared_regulators": shared_interactors,
    "shared_targets": shared_interactors,
    get_subgraph_edges.__name__: get_subgraph_edges,
}


class Query:
    """Parent class to all Query classes

    The Query classes are helpers that make sure the methods of the
    IndraNetworkSearchAPI receive the data needed from a NetworkSearchQuery
    or other Rest query.
    """

    alg_name: str = NotImplemented  # String with name of algorithm function
    options = NotImplemented  # options model

    def __init__(self, query: NetworkSearchQuery):
        self.query: NetworkSearchQuery = query
        self.query_hash: str = query.get_hash()

    def _get_node_blacklist(self) -> List[Union[str, Tuple[str, int]]]:
        # If no node blacklist is provided, or the sign is None, return the node blacklist
        # Otherwise, return the node blacklist with both positive and negative signs
        if not self.query.node_blacklist or self.query.sign is None:
            return self.query.node_blacklist
        else:
            return list(product(self.query.node_blacklist, [0, 1]))

    def api_options(self) -> Dict[str, Any]:
        """These options are used when IndraNetworkSearchAPI handles the query

        The options here impact decisions on which extra search algorithms
        to include and which graph to pick

        Returns
        -------
        :
            A dict of ApiOptions
        """
        return ApiOptions(
            sign=self.query.get_int_sign(),
            fplx_expand=self.query.fplx_expand,
            user_timeout=self.query.user_timeout,
            two_way=self.query.two_way,
            shared_regulators=self.query.shared_regulators,
            format=self.query.format,
        ).dict()

    def alg_options(self) -> Dict[str, Any]:
        """Returns the options for the algorithm used"""
        raise NotImplementedError

    def run_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """Combines all options to one dict that can be sent to algorithm"""
        raise NotImplementedError

    def result_options(self) -> Dict:
        """Provide args to corresponding result class in result_handler"""
        raise NotImplementedError


class UIQuery(Query):
    """Parent Class for all possible queries that come from the web UI"""

    def alg_options(self) -> Dict[str, Any]:
        raise NotImplementedError

    def run_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def result_options(self) -> Dict:
        raise NotImplementedError

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]] = None):
        super().__init__(query=query)
        self.hash_blacklist = hash_blacklist or set()

    def _get_source_target(self, no_sign: bool = False) -> Tuple[StrNode, StrNode]:
        """Use for source-target searches

        Parameters
        ----------
        no_sign :
            Ignore the sign of the query. Used for e.g. shared parents and the
            query is signed. If False, the sign of the query is used (+, - or
            None). If True, the sign is ignored.
        """
        if self.query.sign is not None and not no_sign:
            if self.query.get_int_sign() == 0:
                return (self.query.source, 0), (self.query.target, 0)
            elif self.query.get_int_sign() == 1:
                return (self.query.source, 0), (self.query.target, 1)
            else:
                raise ValueError(f"Unknown sign {self.query.sign}")
        else:
            return self.query.source, self.query.target


class PathQuery(UIQuery):
    """Parent Class for ShortestSimplePaths, Dijkstra and BreadthFirstSearch"""

    # Map name for mapping to edge attribute key
    _weight_map = WEIGHT_NAME_MAPPING

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]]):
        super().__init__(query, hash_blacklist=hash_blacklist)

    def _get_source_node(self) -> Tuple[Union[str, Tuple[str, int]], bool]:
        """Use for open ended path searches"""
        if self.query.source and not self.query.target:
            start_node, reverse = self.query.source, False
        elif not self.query.source and self.query.target:
            start_node, reverse = self.query.target, True
        else:
            raise InvalidParametersError(f"Cannot use {self.alg_name} with both source and target set.")
        signed_node = get_open_signed_node(node=start_node, reverse=reverse, sign=self.query.get_int_sign())
        return signed_node, reverse

    def alg_options(self) -> Dict[str, Any]:
        """Returns the options for the algorithm used, excl mesh options"""
        raise NotImplementedError

    def mesh_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """Return algorithm specific mesh options"""
        raise NotImplementedError

    def run_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """Combines all options to one dict that can be sent to algorithm"""
        return self.options(**self.alg_options(), **self.mesh_options(graph=graph)).dict()

    def result_options(self) -> Dict:
        """Provide args to corresponding result class in result_handler

        Returns
        -------
        :
            Options for the PathResult class
        """
        if self.query.source and self.query.target:
            source, target = self._get_source_target()
            reverse = False
        else:
            start, reverse = self._get_source_node()
            source = "" if reverse else start
            target = start if reverse else ""
        res_options = {
            "filter_options": self.query.get_filter_options(),
            "source": source,
            "target": target,
            "timeout": self.query.user_timeout,
        }
        if self.alg_name != shortest_simple_paths.__name__:
            res_options["reverse"] = reverse
        if self.alg_name != bfs_search.__name__:
            # hash_blacklist is considered in bfs_search
            # dijkstra & shortest_simple_paths checks it in the results
            res_options["hash_blacklist"] = self.hash_blacklist

        return res_options

    # This method is specific for PathQuery classes
    def _get_mesh_options(self, get_func: bool = True) -> Tuple[Set, Union[Callable, None]]:
        """Get the necessary mesh options"""
        if self.query.mesh_ids is None or len(self.query.mesh_ids) == 0:
            raise InvalidParametersError("No mesh ids provided, but method for getting mesh options was called")
        hash_mesh_dict: Dict[int, Dict[str, int]] = get_mesh_ref_counts(self.query.mesh_ids)
        related_hashes: Set = set(hash_mesh_dict.keys())
        ref_counts_from_hashes = _get_ref_counts_func(hash_mesh_dict) if get_func else None
        return related_hashes, ref_counts_from_hashes


class ShortestSimplePathsQuery(PathQuery):
    """Check queries that will use the shortest_simple_paths algorithm"""

    alg_name: str = shortest_simple_paths.__name__
    options: ShortestSimplePathOptions = ShortestSimplePathOptions

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]] = None):
        super().__init__(query, hash_blacklist=hash_blacklist)

    def alg_options(self) -> Dict[str, Any]:
        """Match arguments of shortest_simple_paths from query

        Returns
        -------
        :
            A dict with arguments for shortest_simple_paths
        """
        source, target = self._get_source_target()
        return {
            "source": source,
            "target": target,
            "ignore_nodes": self._get_node_blacklist(),
            "weight": self._weight_map.get(self.query.weighted),
        }

    def mesh_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Union[Set, int, bool, Callable]]:
        """Match input to shortest_simple_paths

        Returns
        -------
        :
            The mesh options for shortest_simple_paths
        """
        # If any mesh ids are provided:
        if self.query.mesh_ids and len(self.query.mesh_ids) > 0:
            hashes, ref_counts_func = self._get_mesh_options()
        else:
            hashes, ref_counts_func = None, None
        return {
            "hashes": hashes,
            "ref_counts_function": ref_counts_func,
            "strict_mesh_id_filtering": self.query.strict_mesh_id_filtering,
            "const_c": self.query.const_c,
            "const_tk": self.query.const_tk,
        }


class BreadthFirstSearchQuery(PathQuery):
    """Check queries that will use the bfs_search algorithm"""

    alg_name: str = bfs_search.__name__
    options: BaseModel = BreadthFirstSearchOptions

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]] = None):
        super().__init__(query, hash_blacklist=hash_blacklist)

    def _get_edge_filter(self) -> Optional[EdgeFilter]:
        # Get edge filter function:
        # - belief (of statement)
        # - statement type
        # - hash: Only do hash blacklist, the mesh associated hashes are taken
        #         care of in mesh options
        # - curated
        belief_cutoff = self.query.belief_cutoff
        stmt_types = self.query.stmt_filter or None
        hash_blacklist = self.hash_blacklist or None
        check_curated = self.query.curated_db_only

        # Simplify function if no filters are applied
        if belief_cutoff == 0 and not stmt_types and not hash_blacklist and not check_curated:
            return None
        else:
            _edge_filter = _get_edge_filter_func(
                stmt_types=stmt_types,
                hash_blacklist=hash_blacklist,
                check_curated=check_curated,
                belief_cutoff=belief_cutoff,
            )
            return _edge_filter

    def alg_options(self) -> Dict[str, Any]:
        """Match arguments of bfs_search from query

        Returns
        -------
        :
            The argument to provide bfs_search
        """
        start_node, reverse = self._get_source_node()
        # path_length == len([node1, node2, ...])
        # depth_limit == len([(node1, node2), (node2, node3), ...])
        # ==> path_length == depth_limit + 1
        if self.query.path_length and self.query.path_length > self.query.depth_limit + 1:
            logger.warning(
                f"Resetting depth_limit from "
                f"{self.query.depth_limit} to match requested "
                f"path_length ({self.query.path_length})"
            )
            depth_limit = self.query.path_length - 1
        else:
            depth_limit = self.query.depth_limit

        edge_filter_func = self._get_edge_filter()

        return {
            "source_node": start_node,
            "reverse": reverse,
            "depth_limit": depth_limit,
            "path_limit": None,  # Sets yield limit inside algorithm
            "max_per_node": self.query.max_per_node or 5,
            "node_filter": self.query.allowed_ns,
            "node_blacklist": self._get_node_blacklist(),
            "terminal_ns": self.query.terminal_ns,
            "sign": self.query.get_int_sign(),
            "max_memory": int(2 ** 29),  # Currently not set in UI
            "edge_filter": edge_filter_func,
        }

    def mesh_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Union[Set, bool, Callable]]:
        """Get mesh options for bfs_search

        Parameters
        ----------
        graph :
            The graph

        Returns
        -------
        :
            The mesh option for bfs_search
        """
        # If any mesh ids are provided:
        if self.query.mesh_ids and len(self.query.mesh_ids) > 0:
            if not isinstance(graph, nx.DiGraph):
                raise InvalidParametersError(f"Must provide graph when running {self.alg_name} with " f"mesh options.")
            hashes, _ = self._get_mesh_options(get_func=False)
            allowed_edges = {graph.graph["edge_by_hash"][h] for h in hashes if h in graph.graph["edge_by_hash"]}
            _allow_edge_func = _get_allowed_edges_func(allowed_edges)
        else:
            hashes, _allow_edge_func = None, lambda u, v: True
        return {
            "hashes": hashes,
            "strict_mesh_id_filtering": self.query.strict_mesh_id_filtering,
            "allow_edge": _allow_edge_func,
        }


class DijkstraQuery(PathQuery):
    """Check queries that will use the open_dijkstra_search algorithm"""

    alg_name: str = open_dijkstra_search.__name__
    options: DijkstraOptions = DijkstraOptions

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]] = None):
        super().__init__(query, hash_blacklist=hash_blacklist)

    def alg_options(self) -> Dict[str, Any]:
        """Match arguments of open_dijkstra_search from query

        Returns
        -------
        :
            A dict with arguments for open_dijkstra_search
        """
        start, reverse = self._get_source_node()
        return {
            "start": start,
            "reverse": reverse,
            "path_limit": None,  # Sets yield limit inside algorithm
            "node_filter": None,  # Unused in algorithm currently
            "ignore_nodes": self._get_node_blacklist(),
            "ignore_edges": None,  # Not provided as an option in UI
            "terminal_ns": self.query.terminal_ns,
            "weight": self._weight_map.get(self.query.weighted),
        }

    def mesh_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Union[Set, bool, Callable]]:
        """Produces mesh arguments matching open_dijkstra_search from query

        Returns
        -------
        :
            The mesh options for open_dijkstra_query
        """
        if self.query.mesh_ids and len(self.query.mesh_ids) > 0:
            hashes, ref_counts_func = self._get_mesh_options()
        else:
            hashes, ref_counts_func = None, None
        return {
            "ref_counts_function": ref_counts_func,
            "hashes": hashes,
            "const_c": self.query.const_c,
            "const_tk": self.query.const_tk,
        }


class SharedInteractorsQuery(UIQuery):
    """Parent class for shared target and shared regulator search"""

    alg_name: str = NotImplemented
    alg_alt_name: str = shared_interactors.__name__
    options: SharedInteractorsOptions = SharedInteractorsOptions
    reverse: bool = NotImplemented

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]] = None):
        super().__init__(query, hash_blacklist=hash_blacklist)

    def alg_options(self) -> Dict[str, Any]:
        """Match arguments of shared_interactors from query

        Returns
        -------
        :
            A dict with the arguments for shared_interactors
        """
        source = get_open_signed_node(node=self.query.source, reverse=self.reverse, sign=self.query.get_int_sign())
        target = get_open_signed_node(node=self.query.target, reverse=self.reverse, sign=self.query.get_int_sign())
        return {
            "source": source,
            "target": target,
            "allowed_ns": self.query.allowed_ns,
            "stmt_types": self.query.stmt_filter,
            "source_filter": None,  # Not implemented in UI
            "max_results": self.query.k_shortest,
            "regulators": self.reverse,
            "sign": self.query.get_int_sign(),
            "hash_blacklist": self.hash_blacklist,
            "node_blacklist": self._get_node_blacklist(),
            "belief_cutoff": self.query.belief_cutoff,
            "curated_db_only": self.query.curated_db_only,
        }

    def run_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """Check query options and return them"""
        return self.options(**self.alg_options()).dict()

    def result_options(self) -> Dict:
        """Provide args to SharedInteractorsResultManager in result_handler"""
        source = get_open_signed_node(node=self.query.source, reverse=self.reverse, sign=self.query.get_int_sign())
        target = get_open_signed_node(node=self.query.target, reverse=self.reverse, sign=self.query.get_int_sign())
        return {
            "filter_options": self.query.get_filter_options(),
            "is_targets_query": not self.reverse,
            "source": source,
            "target": target,
        }


class SharedRegulatorsQuery(SharedInteractorsQuery):
    """Check queries that will use shared_interactors(regulators=True)"""

    alg_name = "shared_regulators"
    reverse = True

    def __init__(self, query: NetworkSearchQuery, hash_blacklist: Optional[Set[int]] = None):
        # bool(shared_regulators) == bool(reverse)
        if query.shared_regulators != self.reverse:
            # shared regulators must not be requested if
            # query.shared_regulators == False
            raise InvalidParametersError(
                "Request for shared regulators in query does not match class attribute reverse"
            )

        super().__init__(query=query, hash_blacklist=hash_blacklist)


class SharedTargetsQuery(SharedInteractorsQuery):
    """Check queries that will use shared_interactors(regulators=False)"""

    alg_name = "shared_targets"
    reverse = False


class OntologyQuery(UIQuery):
    """Check queries that will use shared_parents"""

    alg_name = shared_parents.__name__
    options: OntologyOptions = OntologyOptions

    def __init__(self, query: NetworkSearchQuery):
        super().__init__(query, hash_blacklist=None)

    @staticmethod
    def _get_ns_id(graph: nx.DiGraph, node_name: str) -> Tuple[str, str]:
        return (
            graph.nodes.get(node_name, {}).get("ns"),
            graph.nodes.get(node_name, {}).get("id"),
        )

    def _get_ontology_options(self, graph: nx.DiGraph):
        source_ns, source_id = self._get_ns_id(graph=graph, node_name=self.query.source)
        target_ns, target_id = self._get_ns_id(graph=graph, node_name=self.query.target)
        return {
            "source_ns": source_ns,
            "source_id": source_id,
            "target_ns": target_ns,
            "target_id": target_id,
        }

    def alg_options(self) -> Dict[str, Any]:
        """Match arguments of shared_parents from query

        Returns
        -------
        :
            A dict with arguments for shared_parents
        """
        return {
            "immediate_only": False,
            "is_a_part_of": None,
            "max_paths": self.query.k_shortest,
        }

    def run_options(self, graph: Optional[nx.DiGraph] = None) -> Dict[str, Any]:
        """Check query options and return them for shared_parents

        Parameters
        ----------
        graph :
            The graph used in the search. Must contain node attributes 'ns'
            and 'id' for each node.

        Returns
        -------
        :
            The options for shared_parents
        """
        ontology_options: Dict[str, str] = self._get_ontology_options(graph)
        return self.options(**ontology_options, **self.alg_options()).dict()

    def result_options(self) -> Dict:
        """Provide args to OntologyResultManager in result_handler

        Returns
        -------
        :
            The arguments for the Ontology Result manger
        """
        source, target = self._get_source_target(no_sign=True)
        return {
            "filter_options": self.query.get_filter_options(),
            "source": source,
            "target": target,
        }


class SubgraphQuery:
    """Check queries that gets the subgraph"""

    # todo: subclass from Query and abstract Query more. Make a new class
    #  NetworkSearchQuery as a subclass to Query, that is parent class for
    #  all queries derived from NetworkSearchQuery
    alg_name: str = get_subgraph_edges.__name__
    options: SubgraphOptions = SubgraphOptions

    def __init__(self, query: SubgraphRestQuery):
        self.query: SubgraphRestQuery = query
        self._nodes_in_graph: List[Node] = []
        self._not_in_graph: List[Node] = []

    def _check_nodes(self, graph: nx.DiGraph):
        """Filter out nodes based on their availability in graph

        1. Check if ns/id of node is in mapping: Yes: valid node, No: go to 2.
        2. If a node name is provided in node and it is in the graph, check
           the graph ns/id of the name and overwrite the ns/id of the node.
        3. If not, set node as not in graph
        """
        ns_id2node = graph.graph["node_by_ns_id"]
        for node in self.query.nodes:

            # See if node is in mapping
            mapped_name = ns_id2node.get((node.namespace, node.identifier))
            if mapped_name is not None and mapped_name in graph.nodes:
                proper_node = Node(
                    name=mapped_name,
                    namespace=node.namespace,
                    identifier=node.identifier,
                )

                # Append to existing nodes
                self._nodes_in_graph.append(proper_node)

            # See if node name, if provided, is among nodes
            elif node.name and node.name in graph.nodes:
                # Check if ns/id are proper
                if node.namespace != graph.nodes[node.name]["ns"] or node.identifier != graph.nodes[node.name]["id"]:
                    proper_node = Node(
                        name=node.name,
                        namespace=graph.nodes[node.name]["ns"],
                        identifier=graph.nodes[node.name]["id"],
                    )
                else:
                    proper_node = node

                # Append to existing nodes
                self._nodes_in_graph.append(proper_node)

            # Append to nodes not in graph
            else:
                self._not_in_graph.append(node)

    def alg_options(self, graph: nx.DiGraph) -> Dict[str, List[Node]]:
        """Match arguments of get_subgraph_edges

        Parameters
        ----------
        graph :
            The graph the search will be performed with

        Returns
        -------
        :
            A dict with the arguments for get_subgraph_edges
        """
        if not self._nodes_in_graph and not self._not_in_graph:
            self._check_nodes(graph=graph)
        return {"nodes": self._nodes_in_graph}

    def run_options(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Return options needed for get_subgraph_edges

        Parameters
        ----------
        graph :
            The graph the search will be performed with

        Returns
        -------
        :
            A dict with the arguments for get_subgraph_edges
        """
        return self.options(**self.alg_options(graph)).dict()

    def result_options(self) -> Dict[str, Any]:
        """Return options needed for SubgraphResultManager

        Returns
        -------
        :
            A dict with options for the SubgraphResultManager
        """
        return {
            "filter_options": FilterOptions(),
            "original_nodes": self.query.nodes,
            "nodes_in_graph": self._nodes_in_graph,
            "not_in_graph": self._not_in_graph,
            "timeout": self.query.timeout
        }


class MultiInteractorsQuery:
    """Check queries that will use pathfinding.direct_multi_interactors"""

    alg_name: str = direct_multi_interactors.__name__
    options: Type[MultiInteractorsOptions] = MultiInteractorsOptions

    def __init__(self, rest_query: MultiInteractorsRestQuery):
        self.query = rest_query

    def _alg_options(self) -> Dict[str, Any]:
        # Add blacklisted hashes to the query
        cc = CurationCache()
        hash_blacklist: Set[int] = cc.get_all_hashes()
        query_dict = self.query.dict(exclude_defaults=True, exclude_unset=True)
        query_dict["hash_blacklist"] = hash_blacklist
        return query_dict

    def run_options(self) -> Dict[str, Any]:
        """Return options needed for direct_multi_interactors

        Returns
        -------
        :
            The options needed for direct_multi_interactors
        """
        return self.options(**self._alg_options()).dict()

    def result_options(self) -> Dict[str, Any]:
        """Return a dict with options for the MultiInteractorsResultManager

        Returns
        -------
        :
            A dict with the options for the MultiInteractorsResultManager
        """
        return {
            "input_nodes": self.query.nodes,
            "filter_options": FilterOptions(),  # All filters are in results
            "downstream": self.query.downstream,
            "timeout": self.query.timeout,
        }


def get_open_signed_node(node: str, reverse: bool, sign: Optional[int] = None) -> StrNode:
    """Given sign and direction, return a node

    Assign the correct sign to the source node:
    If search is downstream, source is the first node and the search must
    always start with + as node sign. The leaf node sign (i.e. the end of
    the path) in this case will then be determined by the requested sign.

    If reversed search, the source is the last node and can have
    + or - as node sign depending on the requested sign.

    Parameters
    ----------
    node :
        Starting node
    reverse :
        Direction of search:
        reverse == False -> downstream search
        reverse == True -> upstream search
    sign :
        The requested sign of the search

    Returns
    -------
    :
        A node or signed node
    """
    if sign is None:
        return node
    else:
        # Upstream: return asked sign
        if reverse:
            return node, SIGNS_TO_INT_SIGN.get(sign)
        # Downstream: return positive node
        else:
            return node, INT_PLUS


def _get_ref_counts_func(hash_mesh_dict: Dict):
    def _func(graph: nx.DiGraph, u: str, v: str):
        # Get hashes for edge
        hashes = [d["stmt_hash"] for d in graph[u][v]["statements"]]

        # Get all relevant mesh counts
        dicts: List[Dict] = [hash_mesh_dict.get(h, {"": 0, "total": 1}) for h in hashes]

        # Count references
        total = 1
        ref_counts = 0
        max_ratio = 0
        for d in dicts:
            rc_sum = sum(v for k, v in d.items() if k != "total")
            tot = d["total"] or 1
            if rc_sum / tot > max_ratio:
                max_ratio = rc_sum / tot
                ref_counts = rc_sum
                total = tot

        return ref_counts, total

    return _func


def _get_allowed_edges_func(
    allowed_edges: Set[StrEdge],
) -> Callable[[StrNode, StrNode], bool]:
    def _allow_edge_func(u: StrNode, v: StrNode):
        return (u, v) in allowed_edges

    return _allow_edge_func


def _get_edge_filter_func(
    stmt_types: Optional[List[str]] = None,
    hash_blacklist: Optional[List[int]] = None,
    check_curated: Optional[bool] = False,
    belief_cutoff: Optional[float] = 0.0,
) -> EdgeFilter:
    def _edge_filter(g: nx.DiGraph, u: StrNode, v: StrNode) -> bool:
        for edge_stmt in g.edges[(u, v)]["statements"]:
            if pass_stmt(
                stmt_dict=edge_stmt,
                stmt_types=stmt_types,
                hash_blacklist=hash_blacklist,
                check_curated=check_curated,
                belief_cutoff=belief_cutoff,
            ):
                return True
        return False

    return _edge_filter


def pass_stmt(
    stmt_dict: Dict[str, Any],
    stmt_types: Optional[List[str]] = None,
    hash_blacklist: Optional[List[int]] = None,
    check_curated: bool = False,
    belief_cutoff: float = 0,
) -> bool:
    """Checks and edge statement dict against several filters

    Parameters
    ----------
    stmt_dict :
        The statement dict to check
    stmt_types :
        A list of statement types. If provided, specifies which types are
        allowed. If no list is provided or the list is empty, all types are
        allowed. Default: All statement types are allowed.
    hash_blacklist :
        A list of hashes that are not allowed as supporting statements for
        an edge. Default: all statements are allowed.
    check_curated :
        If True, check if the statement is curated
    belief_cutoff :
        The cutoff for belief scores

    Returns
    -------
    :
        True if statement passes, False otherwise
    """
    # Pass if type is in allowed types
    if stmt_types and stmt_dict["stmt_type"].lower() not in stmt_types:
        return False

    # Pass if hash is not in blacklist
    if hash_blacklist and stmt_dict["stmt_hash"] in hash_blacklist:
        return False

    # Pass if statement is curated
    if check_curated and not stmt_dict["curated"]:
        return False

    # Pass if belief score is above cutoff
    if belief_cutoff > 0 and stmt_dict["belief"] < belief_cutoff:
        return False

    return True


alg_name_query_mapping = {
    bfs_search.__name__: BreadthFirstSearchQuery,
    shortest_simple_paths.__name__: ShortestSimplePathsQuery,
    open_dijkstra_search.__name__: DijkstraQuery,
    shared_parents.__name__: OntologyQuery,
    "shared_regulators": SharedRegulatorsQuery,
    "shared_targets": SharedTargetsQuery,
    get_subgraph_edges.__name__: SubgraphQuery,
    direct_multi_interactors.__name__: MultiInteractorsQuery,
}
