"""
The IndraNetworkSearch REST API
"""
import logging
from datetime import date
from os import environ
from typing import List, Optional

from fastapi import FastAPI, Query as RestQuery

from indra.databases import get_identifiers_url
from indra_network_search.data_models.rest_models import Health, ServerStatus
from indra_network_search.rest_util import load_indra_graph
from indra_network_search.data_models import (
    Results,
    NetworkSearchQuery,
    SubgraphRestQuery,
    SubgraphResults,
    Node,
    MultiInteractorsRestQuery,
    MultiInteractorsResults,
)
from indra_network_search.autocomplete import NodesTrie, Prefixes
from indra_network_search.search_api import IndraNetworkSearchAPI
from depmap_analysis.network_functions.net_functions import bio_ontology


app = FastAPI()

logger = logging.getLogger(__name__)

DEBUG = environ.get("API_DEBUG") == "1"
USE_CACHE = environ.get("USE_CACHE") == "1"
HEALTH = Health(status="booting")
STATUS = ServerStatus(status="booting", graph_date='2021-08-09')


@app.get("/xrefs", response_model=List[List[str]])
def get_xrefs(ns: str, id: str) -> List[List[str]]:
    """Get all cross-refs given a namespace and ID

    Parameters
    ----------
    ns :
        The namespace of the entity to find cross-refs for
    id :
        The identifier of the entity to find cross-regs for

    Returns
    -------
    :
        A list of tuples containing namespace, identifier, lookup url to
        identifiers.org
    """
    # Todo: offload util features and capabilities, such as this one, to a new
    #  UtilApi class
    xrefs = bio_ontology.get_mappings(ns=ns, id=id)
    xrefs_w_lookup = [[n, i, get_identifiers_url(n, i)] for n, i in xrefs]
    return xrefs_w_lookup


@app.get("/node-name-in-graph", response_model=Optional[Node])
def node_name_in_graph(
    node_name: str = RestQuery(..., min_length=1, alias="node-name")
) -> Optional[Node]:
    """Check if node by provided name (case sensitive) exists in graph

    Parameters
    ----------
    node_name :
        The name of the node to check

    Returns
    -------
    :
        When a match is found, the full information of the node is returned
    """
    node = network_search_api.get_node(node_name)
    if node:
        return node


@app.get("/node-id-in-graph", response_model=Optional[Node])
def node_id_in_graph(
    db_name: str = RestQuery(..., min_length=2, alias="db-name"),
    db_id: str = RestQuery(..., min_length=1, alias="db-id"),
) -> Optional[Node]:
    """Check if a node by provided db name and db id exists

    Parameters
    ----------
    db_name :
        The database name, e.g. hgnc, chebi or up
    db_id :
        The identifier for the entity in the given database, e.g. 11018

    Returns
    -------
    :
        When a match is found, the full information of the node is returned
    """
    node = network_search_api.get_node_by_ns_id(db_ns=db_name, db_id=db_id)
    if node:
        return node


@app.get("/autocomplete", response_model=Prefixes)
def get_prefix_autocomplete(
    prefix: str = RestQuery(..., min_length=1),
    max_res: int = RestQuery(100, alias="max-results"),
) -> Prefixes:
    """Get the case-insensitive node names with (ns, id) starting in prefix

    Parameters
    ----------
    prefix :
        The prefix of a node name to search for. Note: for prefixes of
        1 and 2 characters, only exact matches are returned. For 3+
        characters, prefix matching is done. If the prefix contains ':',
        an namspace:id search is done.
    max_res :
        The top ranked (by node degree) results will be returned, cut off at
        this many results.

    Returns
    -------
    :
        A list of tuples of (node name, namespace, identifier)
    """
    # Catch very short entity names
    if 1 <= len(prefix) <= 2 and ":" not in prefix:
        logger.info("Got short node name lookup")
        # Loop all combinations of upper and lowercase
        if len(prefix) == 1:
            nodes = []
            upper_match = network_search_api.get_node(prefix.upper())
            lower_match = network_search_api.get_node(prefix.lower())
            if upper_match:
                nodes.append(
                    [upper_match.name, upper_match.namespace, upper_match.identifier]
                )
            if lower_match:
                nodes.append(
                    [lower_match.name, lower_match.namespace, lower_match.identifier]
                )
        else:
            nodes = []
            n1 = prefix.upper()
            n2 = prefix[0].lower() + prefix.upper()[1]
            n3 = prefix[0].upper() + prefix.lower()[1]
            n4 = prefix.lower()
            for p in [n1, n2, n3, n4]:
                m = network_search_api.get_node(p)
                if m:
                    nodes.append([m.name, m.namespace, m.identifier])
    # Look up ns:id searches
    elif ":" in prefix:
        logger.info("Got ns:id prefix check")
        nodes = nsid_trie.case_items(prefix=prefix, top_n=max_res)
    else:
        logger.info("Got name prefix check")
        nodes = nodes_trie.case_items(prefix=prefix, top_n=max_res)
    logger.info(f"Prefix query resolved with {len(nodes)} suggestions")
    return nodes


@app.get("/health", response_model=Health)
async def health():
    """Returns health status

    Returns
    -------
    Health
    """
    logger.info("Got health check")
    return HEALTH


@app.get("/status", response_model=ServerStatus)
async def server_status():
    """Returns the status of the server and some info about the loaded graphs

    Returns
    -------
    :
    """
    logger.info("Got status check")
    return STATUS


@app.post("/query", response_model=Results)
def query(search_query: NetworkSearchQuery):
    """Interface with IndraNetworkSearchAPI.handle_query

    Parameters
    ----------
    search_query : NetworkSearchQuery
        Query to the NetworkSearchQuery

    Returns
    -------
    Results
    """
    logger.info(f"Got NetworkSearchQuery: {search_query.dict()}")
    results = network_search_api.handle_query(rest_query=search_query)
    return results


@app.post("/multi_interactors", response_model=MultiInteractorsResults)
def multi_interactors(search_query: MultiInteractorsRestQuery):
    logger.info(f"Got multi interactors query with {len(search_query.nodes)} nodes")
    results = network_search_api.handle_multi_interactors_query(
        multi_interactors_rest_query=search_query
    )
    logger.info("Multi interactors query resolved")
    return results


@app.post("/subgraph", response_model=SubgraphResults)
def sub_graph(search_query: SubgraphRestQuery):
    """Interface with IndraNetworkSearchAPI.handle_subgraph_query

    Parameters
    ----------
    search_query: SubgraphRestQuery
        Query to for IndraNetworkSearchAPI.handle_subgraph_query

    Returns
    -------
    SubgraphResults
    """
    logger.info(f"Got subgraph query with {len(search_query.nodes)} nodes")
    subgraph_results = network_search_api.handle_subgraph_query(
        subgraph_rest_query=search_query
    )
    logger.info("Subgraph query resolved")
    return subgraph_results


# Todo: figure out how to do all the loading async so the server is
#  available to respond to health checks while it's loading
#  See:
#  - https://fastapi.tiangolo.com/advanced/events/#startup-event
#  - https://www.starlette.io/events/
if DEBUG:
    from indra_network_search.tests.util import _setup_graph, _setup_signed_node_graph

    dir_graph = _setup_graph()
    sign_node_graph = _setup_signed_node_graph(False)
else:
    dir_graph, _, sign_node_graph, _ = load_indra_graph(
        unsigned_graph=True,
        unsigned_multi_graph=False,
        sign_node_graph=True,
        sign_edge_graph=False,
        use_cache=USE_CACHE,
    )

    bio_ontology.initialize()

# Get a Trie for autocomplete
logger.info("Loading Trie structure with unsigned graph nodes")
nodes_trie = NodesTrie.from_node_names(graph=dir_graph)
nsid_trie = NodesTrie.from_node_ns_id(graph=dir_graph)

# Set numbers for server status
STATUS.unsigned_nodes = len(dir_graph.nodes)
STATUS.unsigned_edges = len(dir_graph.edges)
STATUS.signed_nodes = len(sign_node_graph.nodes)
STATUS.signed_edges = len(sign_node_graph.edges)
dt = dir_graph.graph.get('date')
STATUS.graph_date = date.fromisoformat(dt) if dt else None

# Setup search API
logger.info("Setting up IndraNetworkSearchAPI with signed and unsigned " "graphs")
network_search_api = IndraNetworkSearchAPI(
    unsigned_graph=dir_graph, signed_node_graph=sign_node_graph
)
logger.info("Service is available")
STATUS.status = "available"
HEALTH.status = "available"
