"""
The INDRA Network Search API

This class represents an API that executes search queries

Queries for specific searches are found in indra_network_search.query
"""
import logging
from typing import Union, Dict, Optional

from networkx import DiGraph

from depmap_analysis.network_functions.famplex_functions import \
    get_identifiers_url
from indra.explanation.pathfinding import (
    shortest_simple_paths,
    bfs_search,
    open_dijkstra_search,
)
from .data_models import *
from .pathfinding import *
from .query import *
from .query_handler import *
from .result_handler import *

__all__ = ["IndraNetworkSearchAPI"]


logger = logging.getLogger(__name__)


class IndraNetworkSearchAPI:
    """The search API class"""

    def __init__(self, unsigned_graph: DiGraph, signed_node_graph: DiGraph):
        self._digraph: DiGraph = unsigned_graph
        self._sng: DiGraph = signed_node_graph

    def get_graph(self, signed: bool = False) -> DiGraph:
        """Returns the graph used for pathfinding"""
        if signed:
            return self._sng
        else:
            return self._digraph

    def handle_query(self, rest_query: NetworkSearchQuery) -> Results:
        """Handle a NetworkSearchQuery and return the corresponding results

        Parameters
        ----------
        rest_query:
            A query from the rest api with all relevant information to
            execute path queries and other related queries. See available
            queries in indra_network_search.query

        Returns
        -------
        :
            A model containing all results from the query. For more
            information about the data structure, see
            indra_network_search.data_models
        """
        query_handler = QueryHandler(rest_query=rest_query)
        eligible_queries = query_handler.get_queries()

        # Initialize results
        results = Results(
            query_hash=rest_query.get_hash(),
            time_limit=rest_query.user_timeout,
            timed_out=False,
        )

        # Get result manager for path query
        result_managers: Dict[str, ResultManager] = {}
        path_result_manager = self.path_query(
            eligible_queries["path_query"], is_signed=query_handler.signed
        )
        # Get result manager for reverse path query if requested
        if "reverse_path_query" in eligible_queries:
            rev_path_res_mngr = self.path_query(
                eligible_queries["reverse_path_query"], is_signed=query_handler.signed
            )
        else:
            rev_path_res_mngr = None

        for alg_name, query in eligible_queries.items():
            if alg_name == "path_query":
                continue

            # Other results
            if isinstance(query, SharedTargetsQuery):
                result_managers[alg_name] = self.shared_targets(
                    query, is_signed=query_handler.signed
                )
            elif isinstance(query, SharedRegulatorsQuery):
                result_managers[alg_name] = self.shared_regulators(
                    query, is_signed=query_handler.signed
                )
            elif isinstance(query, OntologyQuery):
                result_managers[alg_name] = self.shared_parents(query)

        # Execute all get_results with the path query last, as it takes the
        # longest
        for alg_name, res_man in result_managers.items():
            try:
                assert isinstance(res_man, ResultManager)
            except AssertionError:
                logger.warning(
                    f"Object {type(res_man)} is not a " f"ResultManager, skipping..."
                )
                continue

            if alg_name == "shared_targets":
                results.shared_target_results = res_man.get_results()
            elif alg_name == "shared_regulators":
                results.shared_regulators_results = res_man.get_results()
            elif alg_name == shared_parents.__name__:
                results.ontology_results = res_man.get_results()

            if res_man.timed_out:
                results.timed_out = True
                logger.warning("Search timed out")
                break

        if not results.timed_out:
            results.path_results = path_result_manager.get_results()
            if path_result_manager.timed_out:
                results.timed_out = True
                logger.warning(f"Search timed out")

        if not results.timed_out and rev_path_res_mngr:
            results.reverse_path_results = rev_path_res_mngr.get_results()
            if rev_path_res_mngr.timed_out:
                results.timed_out = True
                logger.warning(f"Search timed out")

        return results

    def get_node(self, node_name: str) -> Union[Node, None]:
        """Returns an instance of a Node matching the input name, if it exists

        Parameters
        ----------
        node_name :
            Name of node to look up

        Returns
        -------
        :
            An instance of a node corresponding to the input name
        """
        g = self.get_graph()
        db_ns = g.nodes.get(node_name, {}).get("ns")
        db_id = g.nodes.get(node_name, {}).get("id")
        if db_id is None and db_ns is None:
            return None
        lookup = get_identifiers_url(db_name=db_ns, db_id=db_id) or ""
        if lookup:
            return Node(
                name=node_name, namespace=db_ns, identifier=db_id, lookup=lookup
            )
        else:
            return Node(name=node_name, namespace=db_ns, identifier=db_id)

    def get_node_by_ns_id(self, db_ns: str, db_id: str) -> Optional[Node]:
        g = self.get_graph()
        name = g.graph["node_by_ns_id"].get(f"{db_ns}:{db_id}")
        if name:
            lookup = get_identifiers_url(db_name=db_ns, db_id=db_id) or ""
            if lookup:
                return Node(name=name, namespace=db_ns, identifier=db_id, lookup=lookup)
            else:
                return Node(name=name, namespace=db_ns, identifier=db_id)
        else:
            return None

    def path_query(
        self, path_query: Union[Query, PathQuery], is_signed: bool
    ) -> ResultManager:
        """Wrapper for the mutually exclusive path queries

        Parameters
        ----------
        path_query :
            An instance of a Query or PathQuery
        is_signed :
            Signifies if the path query is signed or not

        Returns
        -------
        :
            A ResultManager with the path generator loaded before
            get_results() have been executed for the first time
        """
        if isinstance(path_query, ShortestSimplePathsQuery):
            return self.shortest_simple_paths(path_query, is_signed=is_signed)
        elif isinstance(path_query, DijkstraQuery):
            return self.dijkstra(path_query, is_signed=is_signed)
        elif isinstance(path_query, BreadthFirstSearchQuery):
            return self.breadth_first_search(path_query, is_signed=is_signed)
        else:
            raise ValueError(f"Unknown PathQuery of type " f"{path_query.__class__}")

    def shortest_simple_paths(
        self, shortest_simple_paths_query: ShortestSimplePathsQuery, is_signed: bool
    ) -> ShortestSimplePathsResultManager:
        """Get results from running shortest_simple_paths

        Parameters
        ----------
        shortest_simple_paths_query :
            The input query holding the options to the algorithm
        is_signed :
            Whether the query is signed or not

        Returns
        -------
        :
            An instance of the ShortestSimplePathsResultManager, holding
            results from running shortest_simple_paths_query
        """
        sspq = shortest_simple_paths_query

        graph = self.get_graph(signed=is_signed)
        path_gen = shortest_simple_paths(G=graph, **sspq.run_options(graph=graph))

        return ShortestSimplePathsResultManager(
            path_generator=path_gen, graph=graph, **sspq.result_options()
        )

    def breadth_first_search(
        self, breadth_first_search_query: BreadthFirstSearchQuery, is_signed: bool
    ) -> BreadthFirstSearchResultManager:
        """Get results from running bfs_search

        Parameters
        ----------
        breadth_first_search_query :
            The input query holding the options to the algorithm
        is_signed :
            Whether the query is signed or not

        Returns
        -------
        :
            An instance of the BreadthFirstSearchResultManager, holding
            results from running bfs_search
        """
        bfsq = breadth_first_search_query
        graph = self.get_graph(signed=is_signed)
        path_gen = bfs_search(g=graph, **bfsq.run_options(graph=graph))
        return BreadthFirstSearchResultManager(
            path_generator=path_gen, graph=graph, **bfsq.result_options()
        )

    def dijkstra(
        self, dijkstra_query: DijkstraQuery, is_signed: bool
    ) -> DijkstraResultManager:
        """Get results from running open_dijkstra_search

        Parameters
        ----------
        dijkstra_query :
            The input query holding options for open_dijkstra_search and
            DijkstraResultManager
        is_signed :
            Whether the query is signed or not

        Returns
        -------
        :
            An instance of the DijkstraResultManager, holding results from
            running open_dijkstra_search

        """
        dq = dijkstra_query
        path_gen = open_dijkstra_search(g=self.get_graph(), **dq.run_options())
        graph = self.get_graph(signed=is_signed)
        return DijkstraResultManager(
            path_generator=path_gen, graph=graph, **dq.result_options()
        )

    def shared_targets(
        self, shared_targets_query: SharedTargetsQuery, is_signed: bool
    ) -> SharedInteractorsResultManager:
        """Get results from running shared_interactors looking for targets

        Parameters
        ----------
        shared_targets_query :
            The input query holding options for shared_interactors
        is_signed :
            Whether the query is signed or not

        Returns
        -------
        :
            An instance of the SharedInteractorsResultManager, holding
            results from running shared_interactors looking for targets
        """
        stq = shared_targets_query
        graph = self.get_graph(signed=is_signed)
        path_gen = shared_interactors(graph=graph, **stq.run_options())
        return SharedInteractorsResultManager(
            path_generator=path_gen, graph=graph, **stq.result_options()
        )

    def shared_regulators(
        self, shared_regulators_query: SharedRegulatorsQuery, is_signed: bool
    ) -> SharedInteractorsResultManager:
        """Get results from running shared_interactors looking for regulators

        Parameters
        ----------
        shared_regulators_query :
            The input query holding options for shared_interactors
        is_signed :
            Whether the query is signed or not

        Returns
        -------
        :
            An instance of the SharedInteractorsResultManager, holding
            results from running shared_interactors looking for regulators
        """
        srq = shared_regulators_query
        graph = self.get_graph(signed=is_signed)
        path_gen = shared_interactors(graph=graph, **srq.run_options())
        return SharedInteractorsResultManager(
            path_generator=path_gen, graph=graph, **srq.result_options()
        )

    def shared_parents(self, ontology_query: OntologyQuery) -> OntologyResultManager:
        """Get results from running shared_parents

        Parameters
        ----------
        ontology_query :
            The input query holding options for shared_parents

        Returns
        -------
        :
            An instance of the OntologyResultManager, holding results from
            running shared_parents
        """
        oq = ontology_query
        graph = self.get_graph()
        path_gen = shared_parents(**oq.run_options(graph=graph))
        return OntologyResultManager(
            path_generator=path_gen, graph=graph, **oq.result_options()
        )

    def handle_subgraph_query(
        self, subgraph_rest_query: SubgraphRestQuery
    ) -> SubgraphResults:
        """Interface for handling queries to get_subgraph_edges

        Parameters
        ----------
        subgraph_rest_query :
            A rest query containing the list of nodes needed for
            get_subgraph_edges

        Returns
        -------
        :
            The data put together from the results of get_subgraph_edges
        """
        subgraph_query = SubgraphQuery(query=subgraph_rest_query)
        res_mngr = self.subgraph_query(query=subgraph_query)
        return res_mngr.get_results()

    def subgraph_query(self, query: SubgraphQuery) -> SubgraphResultManager:
        """Get results from running get_subgraph_edges

        Parameters
        ----------
        query :
            The input query holding the options for get_subgraph_edges

        Returns
        -------
        :
            An instance of the SubgraphResultManager, holding results from
            running get_subgraph_edges
        """
        graph = self.get_graph(signed=False)
        edge_iter = get_subgraph_edges(graph=graph, **query.run_options(graph=graph))
        return SubgraphResultManager(
            path_generator=edge_iter, graph=graph, **query.result_options()
        )

    def handle_multi_interactors_query(
        self, multi_interactors_rest_query: MultiInteractorsRestQuery
    ) -> MultiInteractorsResults:
        """Interface with pathfinding.direct_multi_interactors

        Parameters
        ----------
        multi_interactors_rest_query :
            The input query holding options for direct multi interactors

        Returns
        -------
        :
            Results holding node and edge data
        """
        mi_query = MultiInteractorsQuery(multi_interactors_rest_query)
        res_mngr = self.multi_interactors_query(query=mi_query)
        return res_mngr.get_results()

    def multi_interactors_query(
        self, query: MultiInteractorsQuery
    ) -> MultiInteractorsResultManager:
        """Run direct_multi_interactors and return the result manager

        Parameters
        ----------
        query :
            An instance of MultiInteractorsQuery, that interfaces with the
            algorithm and the result manager

        Returns
        -------
        :
            A MultiInteractorsResultManager holding the results of running
            direct_multi_interactors
        """
        graph = self.get_graph(signed=False)
        run_options = query.run_options()
        res_gen = direct_multi_interactors(graph=graph, **run_options)
        res_options = query.result_options()
        return MultiInteractorsResultManager(
            path_generator=res_gen, graph=graph, **res_options
        )
