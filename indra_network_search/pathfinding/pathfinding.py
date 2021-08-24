"""
Pathfinding algorithms local to this repo
"""
import logging
from itertools import islice, product
from typing import (
    Generator,
    List,
    Union,
    Optional,
    Set,
    Iterator,
    Tuple,
    Any,
    Dict,
    Callable,
)

from networkx import DiGraph

from depmap_analysis.network_functions.famplex_functions import (
    common_parent,
    get_identifiers_url,
    ns_id_to_name,
)
from indra_network_search.rest_util import StrNode, StrNodeSeq

logger = logging.getLogger(__name__)
FilterOption = Union[List[str], List[int], float, None]

__all__ = [
    "shared_interactors",
    "shared_parents",
    "get_subgraph_edges",
    "direct_multi_interactors",
]


def shared_parents(
    source_ns: str,
    source_id: str,
    target_ns: str,
    target_id: str,
    immediate_only: bool = False,
    is_a_part_of: Optional[Set[str]] = None,
    max_paths: int = 50,
) -> Iterator[Tuple[str, Any, Any, str]]:
    """Get shared parents of (source ns, source id) and (target ns, target id)

    Parameters
    ----------
    source_ns : str
        Namespace of source
    source_id : str
        Identifier of source
    target_ns
        Namespace of target
    target_id
        Identifier of target
    immediate_only : bool
        Determines if all or just the immediate parents should be returned.
        Default: False, i.e. all parents.
    is_a_part_of : Set[str]
        If provided, the parents must be in this set of ids. The set is
        assumed to be valid ontology labels (see ontology.label()).
    max_paths : int
        Maximum number of results to return. Default: 50.

    Returns
    -------
    List[Tuple[str, str, str, str]]
    """
    sp_set = common_parent(
        id1=source_id,
        id2=target_id,
        ns1=source_ns,
        ns2=target_ns,
        immediate_only=immediate_only,
        is_a_part_of=is_a_part_of,
    )
    return islice(
        sorted(
            [
                (ns_id_to_name(n, i) or "", n, i, get_identifiers_url(n, i))
                for n, i in sp_set
                # sort on     name,  ns,  id
            ],
            key=lambda t: (t[0], t[1], t[2]),
        ),
        max_paths,
    )


def shared_interactors(
    graph: DiGraph,
    source: StrNode,
    target: StrNode,
    allowed_ns: Optional[List[str]] = None,
    stmt_types: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    max_results: int = 50,
    regulators: bool = False,
    sign: Optional[int] = None,
    hash_blacklist: Optional[Set[str]] = None,
    node_blacklist: Optional[List[str]] = None,
    belief_cutoff: float = 0.0,
    curated_db_only: bool = False,
) -> Iterator[Tuple[List[StrNode], List[StrNode]]]:
    """Get shared regulators or targets and filter them based on sign

    Closely resembles get_st and get_sr from
    depmap_analysis.scripts.depmap_script_expl_funcs

    Parameters
    ----------
    graph : DiGraph
        The graph to perform the search in
    source : str
        Node to look for common up- or downstream neighbors from with target
    target : str
        Node to look for common up- or downstream neighbors from with source
    allowed_ns : Optional[List[str]]
        If provided, filter common nodes to these namespaces
    stmt_types : Optional[List[str]]
        If provided, filter the statements in the supporting edges to these
        statement types
    source_filter : Optional[List[str]]
        If provided, filter the statements in the supporting edges to those
        with these sources
    max_results : int
        The maximum number of results to return
    regulators : bool
        If True, do shared regulator search (upstream), otherwise do shared
        target search (downstream). Default False.
    sign : Optional[int]
        If provided, match edges to sign:
            - positive: edges must have same sign
            - negative: edges must have opposite sign
    hash_blacklist : Optional[Set[int]]
        A list of hashes to exclude from the edges
    node_blacklist : Optional[List[str]]
        A list of node names to exclude
    belief_cutoff : float
        Exclude statements that are below the cutoff. Default: 0.0 (no cutoff)
    curated_db_only : bool
        If True, exclude statements in edge support that only have readers
        in their sources. Default: False.

    Returns
    -------
    Generator
    """

    def _get_min_max_belief(node: StrNode):
        s_edge = (node, source) if regulators else (source, node)
        t_edge = (node, target) if regulators else (target, node)
        s_max: float = max([sd["belief"] for sd in graph.edges[s_edge]["statements"]])
        t_max: float = max([sd["belief"] for sd in graph.edges[t_edge]["statements"]])
        return min(s_max, t_max)

    neigh = graph.pred if regulators else graph.succ
    s_neigh: Set[StrNode] = set(neigh[source])
    t_neigh: Set[StrNode] = set(neigh[target])

    # If signed, filter sign
    # Sign is handled different here than in the depmap explanations - if
    # the caller provides a positive sign, the common nodes should be the
    # ones that are upregulated by the source & target in the case of
    # shared targets and upregulates source & target in the case of shared
    # regulators.
    if sign is not None:
        s_neigh, t_neigh = _sign_filter(
            source, s_neigh, target, t_neigh, sign, regulators
        )

    # Filter nodes
    if node_blacklist:
        s_neigh = {n for n in s_neigh if n not in node_blacklist}
        t_neigh = {n for n in t_neigh if n not in node_blacklist}

    # Filter ns
    if allowed_ns:
        s_neigh = _namespace_filter(s_neigh, graph, allowed_ns)
        t_neigh = _namespace_filter(t_neigh, graph, allowed_ns)

    # Filter statements type
    if stmt_types:
        st_args = (graph, regulators, stmt_types)
        s_neigh = _stmt_types_filter(source, s_neigh, *st_args)
        t_neigh = _stmt_types_filter(target, t_neigh, *st_args)

    # Filter curated db
    if curated_db_only:
        curated_args = (graph, regulators)
        s_neigh = _filter_curated(source, s_neigh, *curated_args)
        t_neigh = _filter_curated(target, t_neigh, *curated_args)

    # Filter hashes
    if hash_blacklist:
        hash_args = (graph, regulators, hash_blacklist)
        s_neigh = _hash_filter(source, s_neigh, *hash_args)
        t_neigh = _hash_filter(target, t_neigh, *hash_args)

    # Filter belief
    if belief_cutoff > 0:
        belief_args = (graph, regulators, belief_cutoff)
        s_neigh = _belief_filter(source, s_neigh, *belief_args)
        t_neigh = _belief_filter(target, t_neigh, *belief_args)

    # Filter source
    if source_filter:
        src_args = (graph, regulators, source_filter)
        s_neigh = _source_filter(source, s_neigh, *src_args)
        t_neigh = _source_filter(target, t_neigh, *src_args)

    intermediates = s_neigh & t_neigh

    interm_sorted = sorted(intermediates, key=_get_min_max_belief, reverse=True)

    # Return generator of edge pairs sorted by lowest highest belief of
    if regulators:
        path_gen: Generator = (([x, source], [x, target]) for x in interm_sorted)
    else:
        path_gen: Generator = (([source, x], [target, x]) for x in interm_sorted)
    return islice(path_gen, max_results)


def direct_multi_interactors(
    graph: DiGraph,
    interactor_list: List[StrNode],
    downstream: bool,
    allowed_ns: Optional[List[str]] = None,
    stmt_types: Optional[List[str]] = None,
    source_filter: Optional[List[str]] = None,
    max_results: int = 50,
    hash_blacklist: Optional[Set[str]] = None,
    node_blacklist: Optional[List[str]] = None,
    belief_cutoff: float = 0.0,
    curated_db_only: bool = False,
) -> Iterator:
    # ToDo: how to fix checking if nodes are in graph?

    reverse = not downstream
    neigh_lookup = graph.succ if downstream else graph.pred
    if not len(interactor_list):
        raise ValueError("Interactor list must contain at least one node")

    # Get neighbors
    if len(interactor_list) == 1:
        neighbors = set(neigh_lookup[interactor_list[0]])
    else:
        first_node = interactor_list[0]
        neighbors = set(neigh_lookup[first_node])
        if neighbors:
            for neigh in interactor_list[1:]:
                neighbors.intersection_update(set(neigh_lookup[neigh]))

    # Apply node filters
    if allowed_ns and neighbors:
        neighbors = list(
            _namespace_filter(graph=graph, nodes=neighbors, allowed_ns=allowed_ns)
        )
    if node_blacklist and neighbors:
        neighbors = [n for n in neighbors if n not in node_blacklist]

    # Apply edge type filters
    filter_args = (
        interactor_list,
        neighbors,
        graph,
        reverse,
    )
    if stmt_types and neighbors:
        neighbors = _run_edge_filter(
            *filter_args, filter_func=_stmt_types_filter, filter_option=stmt_types
        )

    if source_filter and neighbors:
        neighbors = _run_edge_filter(
            *filter_args, filter_func=_source_filter, filter_option=source_filter
        )

    if hash_blacklist and neighbors:
        neighbors = _run_edge_filter(
            *filter_args, filter_func=_hash_filter, filter_option=hash_blacklist
        )

    if belief_cutoff > 0 and neighbors:
        neighbors = _run_edge_filter(
            *filter_args, filter_func=_belief_filter, filter_option=belief_cutoff
        )

    if curated_db_only and neighbors:
        neighbors = _run_edge_filter(
            *filter_args, filter_func=_filter_curated, filter_option=None
        )

    # Sort by node degree
    if neighbors:
        neighbors = sorted(neighbors, key=lambda n: graph.degree(n))
        return islice(neighbors, max_results)
    return iter([])


def _sign_filter(
    source: Tuple[str, int],
    s_neigh: Set[Tuple[str, int]],
    target: Tuple[str, int],
    t_neigh: Set[Tuple[str, int]],
    sign: Optional[int],
    regulators: bool,
):
    # Check that nodes are signed
    try:
        assert isinstance(source, tuple)
        assert isinstance(target, tuple)
    except AssertionError as err:
        raise ValueError("Input nodes are not signed") from err
    # Check that signs are proper
    if sign not in {0, 1}:
        raise ValueError(f"Unknown sign {sign}")

    if regulators:
        # source and target sign match requested sign, neighbors are
        # always + signed
        try:
            assert source[1] == sign
            assert target[1] == sign
        except AssertionError as err:
            raise ValueError("Node sign does not match requested sign") from err

        # Regulators can only have + sign
        # Find regulators that upregulate both source & target
        # Find regulators that downregulate both source & target

        s_neigh: Set[str] = {s for s in s_neigh if s[1] == 0}
        t_neigh: Set[str] = {t for t in t_neigh if t[1] == 0}
    else:
        # Match target sign with requested sign
        s_neigh: Set[str] = {s for s in s_neigh if s[1] == sign}
        t_neigh: Set[str] = {t for t in t_neigh if t[1] == sign}

    return s_neigh, t_neigh


def _namespace_filter(
    nodes: StrNodeSeq, graph: DiGraph, allowed_ns: List[str]
) -> Set[StrNode]:
    return {x for x in nodes if graph.nodes[x]["ns"].lower() in allowed_ns}


def _stmt_types_filter(
    start_node: StrNode,
    neighbor_nodes: Set[StrNode],
    graph: DiGraph,
    reverse: bool,
    stmt_types: List[str],
) -> Set[StrNode]:
    # Sort to ensure edge_iter is co-ordered
    if isinstance(start_node, tuple):
        node_list = sorted(neighbor_nodes, key=lambda t: t[0])
    else:
        node_list = sorted(neighbor_nodes)

    edge_iter = (
        product(node_list, [start_node])
        if reverse
        else product([start_node], node_list)
    )

    # Check which edges have the allowed stmt types
    filtered_neighbors: Set[StrNode] = set()
    for n, edge in zip(node_list, edge_iter):
        stmt_list = graph.edges[edge]["statements"]
        if any(sd["stmt_type"].lower() in stmt_types for sd in stmt_list):
            filtered_neighbors.add(n)
    return filtered_neighbors


def _source_filter(
    start_node: StrNode,
    neighbor_nodes: Set[StrNode],
    graph: DiGraph,
    reverse: bool,
    sources: List[str],
) -> Set[StrNode]:
    # Sort to ensure edge_iter is co-ordered
    if isinstance(start_node, tuple):
        node_list = sorted(neighbor_nodes, key=lambda t: t[0])
    else:
        node_list = sorted(neighbor_nodes)

    edge_iter = (
        product(node_list, [start_node])
        if reverse
        else product([start_node], node_list)
    )

    # Check which edges have the allowed stmt types
    filtered_neighbors: Set[StrNode] = set()
    for n, edge in zip(node_list, edge_iter):
        for sd in graph.edges[edge]["statements"]:
            if isinstance(sd["source_counts"], dict) and any(
                [s.lower() in sources for s in sd["source_counts"]]
            ):
                filtered_neighbors.add(n)
                break
    return filtered_neighbors


def _filter_curated(
    start_node: StrNode,
    neighbor_nodes: Set[StrNode],
    graph: DiGraph,
    reverse: bool,
) -> Set[StrNode]:
    # Sort to ensure edge_iter is co-ordered
    if isinstance(start_node, tuple):
        # If signed, order on name, not sign
        node_list = sorted(neighbor_nodes, key=lambda t: t[0])
    else:
        node_list = sorted(neighbor_nodes)

    edge_iter = (
        product(node_list, [start_node])
        if reverse
        else product([start_node], node_list)
    )

    # Filter out edges without support from databases
    filtered_neighbors = set()
    for n, edge in zip(node_list, edge_iter):
        stmt_list = graph.edges[edge]["statements"]
        if any(sd["curated"] for sd in stmt_list):
            filtered_neighbors.add(n)
    return filtered_neighbors


def _hash_filter(
    start_node: StrNode,
    neighbor_nodes: Set[StrNode],
    graph: DiGraph,
    reverse: bool,
    hashes: List[int],
) -> Set[StrNode]:
    # Sort to ensure edge_iter is co-ordered
    if isinstance(start_node, tuple):
        # If signed, order on name, not sign
        node_list = sorted(neighbor_nodes, key=lambda t: t[0])
    else:
        node_list = sorted(neighbor_nodes)

    edge_iter = (
        product(node_list, [start_node])
        if reverse
        else product([start_node], node_list)
    )

    # Filter out edges without support from databases
    filtered_neighbors = set()
    for n, edge in zip(node_list, edge_iter):
        stmt_list = graph.edges[edge]["statements"]

        # Add node if *any* hash is *not* in blacklist
        for sd in stmt_list:
            if sd["stmt_hash"] not in hashes:
                filtered_neighbors.add(n)
                break
    return filtered_neighbors


def _belief_filter(
    start_node: StrNode,
    neighbor_nodes: Set[StrNode],
    graph: DiGraph,
    reverse: bool,
    belief_cutoff: float,
) -> Set[StrNode]:
    # Sort to ensure edge_iter is co-ordered
    if isinstance(start_node, tuple):
        # If signed, order on name, not sign
        node_list = sorted(neighbor_nodes, key=lambda t: t[0])
    else:
        node_list = sorted(neighbor_nodes)

    edge_iter = (
        product(node_list, [start_node])
        if reverse
        else product([start_node], node_list)
    )

    # Filter out edges with belief below the cutoff
    filtered_neighbors = set()
    for n, edge in zip(node_list, edge_iter):
        stmt_list = graph.edges[edge]["statements"]

        # Add node if *any* belief score is *above* cutoff
        for sd in stmt_list:
            if sd["belief"] > belief_cutoff:
                filtered_neighbors.add(n)
                break
    return filtered_neighbors


def _run_edge_filter(
    start_nodes: StrNodeSeq,
    neighbor_nodes: Set[StrNode],
    g: DiGraph,
    rev: bool,
    filter_option: FilterOption,
    filter_func: Callable[[StrNode, Set[StrNode], DiGraph, bool, ...], Set[StrNode]],
):
    for start_node in start_nodes:
        if not neighbor_nodes:
            return neighbor_nodes
        if filter_option is None:
            neighbor_nodes = filter_func(start_node, neighbor_nodes, g, rev)
        else:
            neighbor_nodes = filter_func(
                start_node, neighbor_nodes, g, rev, filter_option
            )

    return neighbor_nodes


def get_subgraph_edges(
    graph: DiGraph, nodes: List[Dict[str, str]]
) -> Iterator[Tuple[str, str]]:
    """Get the subgraph connecting the provided nodes

    Parameters
    ----------
    graph : DiGraph
        Graph to look for in and out edges in
    nodes : List[Dict[str, str]]
        List of dicts of Node instances to look for neighbors in

    Returns
    -------
    Dict[str, Dict[str, List[Tuple[str, str]]]
        A dict keyed by each of the input node names that were present in
        the graph. For each node, two lists are provided for in-edges
        and out-edges respectively
    """
    node_names = [n["name"] for n in nodes]
    subgraph = graph.subgraph(nodes=node_names)
    return iter(subgraph.edges)
