"""Utility functions for the Network Search API and Rest API"""
import inspect
import json
import logging
from os import path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import networkx as nx
from botocore.exceptions import ClientError
from depmap_analysis.scripts.dump_new_graphs import *
from depmap_analysis.util.aws import (
    DUMPS_BUCKET,
    NET_BUCKET,
    NETS_PREFIX,
    dump_json_to_s3,
    get_s3_client,
    get_s3_file_tree,
)
from depmap_analysis.util.io_functions import file_opener
from fnvhash import fnv1a_32
from indra_db.util.s3_path import S3Path

__all__ = [
    "load_indra_graph",
    "load_mesh_annotation_lookup",
    "check_existence_and_date_s3",
    "dump_result_json_to_s3",
    "dump_query_json_to_s3",
    "get_query_hash",
    "dump_query_result_to_s3",
    "get_s3_client",
    "CACHE",
    "INDRA_DG",
    "INDRA_SEG",
    "INDRA_SNG",
    "get_default_args",
    "get_mandatory_args",
    "is_weighted",
    "is_context_weighted",
    "StrNode",
    "StrEdge",
    "StrNodeSeq",
]

logger = logging.getLogger(__name__)

API_PATH = path.dirname(path.abspath(__file__))
CACHE = path.join(API_PATH, "_cache")
MESH_ANNOTATION_LOOKUP = path.join(CACHE, "mesh_annotation_lookup.pkl")

# Derived type hints
StrNode = Union[str, Tuple[str, int]]
StrEdge = Tuple[StrNode, StrNode]
StrNodeSeq = Union[List[StrNode], Set[StrEdge]]


def sorted_json_string(jsonable_dict: Dict) -> str:
    """Produce a string that is unique to a json's contents

    Parameters
    ----------
    jsonable_dict :
        A dict representation of a JSON to create a sorted string out of

    Returns
    -------
    :
        The sorted string representation of the JSON
    """
    if isinstance(jsonable_dict, str):
        return jsonable_dict
    elif isinstance(jsonable_dict, (tuple, list)):
        return "[%s]" % (",".join(sorted(sorted_json_string(s) for s in jsonable_dict)))
    elif isinstance(jsonable_dict, dict):
        return "{%s}" % (",".join(sorted(k + sorted_json_string(v) for k, v in jsonable_dict.items())))
    elif isinstance(jsonable_dict, (int, float)):
        return str(jsonable_dict)
    elif jsonable_dict is None:
        return json.dumps(jsonable_dict)
    else:
        raise TypeError("Invalid type: %s" % type(jsonable_dict))


def get_query_hash(query_json: Dict, ignore_keys: Optional[Union[Set, List]] = None) -> int:
    """Create an FNV-1a 32-bit hash from the query json

    Parameters
    ----------
    query_json :
        A json compatible query dict
    ignore_keys :
        A list or set of keys to ignore in the query_json. By default,
        no keys are ignored. Default: None.

    Returns
    -------
    :
        An FNV-1a 32-bit hash of the query json ignoring the keys in
        ignore_keys
    """
    if ignore_keys:
        if set(ignore_keys).difference(query_json.keys()):
            missing = set(ignore_keys).difference(query_json.keys())
            logger.warning(
                'Ignore key(s) "%s" are not in the provided query_json and '
                "will be skipped..." % str('", "'.join(missing))
            )
        query_json = {k: v for k, v in query_json.items() if k not in ignore_keys}
    return fnv1a_32(sorted_json_string(query_json).encode("utf-8"))


def get_latest_graphs() -> Dict[str, str]:
    """Return the s3 urls to the latest unsigned and signed graphs available

    Returns
    -------
    :
        A dict of the S3 keys of the latest unsigned and signed graphs
    """
    s3 = get_s3_client(unsigned=False)
    tree = get_s3_file_tree(s3=s3, bucket=NET_BUCKET, prefix=NETS_PREFIX, with_dt=True)
    keys = [key for key in tree.gets("key") if key[0].endswith(".pkl")]

    # Sort newest first
    keys.sort(key=lambda t: t[1], reverse=True)

    # Find latest graph of each type
    latest_graphs = {}
    for graph_type in [INDRA_DG, INDRA_SNG, INDRA_SEG]:
        for key, _ in keys:
            if graph_type in key:
                s3_url = f"s3://{NET_BUCKET}/{key}"
                latest_graphs[graph_type] = s3_url
                break
    if len(latest_graphs) == 0:
        logger.warning(f"Found no graphs at s3://{NET_BUCKET}" f"/{NETS_PREFIX}/*.pkl")
    return latest_graphs


def load_mesh_annotation_lookup() -> dict[str, str]:
    """Load the mesh annotation lookup

    Returns
    -------
    :
        Returns a dict mapping mesh id curies to their name as they are set in
        `indra.ontology.bio.bio_ontology`
    """
    mesh_lookup = file_opener(MESH_ANNOTATION_LOOKUP)
    return mesh_lookup


def load_indra_graph(
    unsigned_graph: bool = True,
    unsigned_multi_graph: bool = False,
    sign_edge_graph: bool = False,
    sign_node_graph: bool = True,
    use_cache: bool = False,
) -> Tuple[Optional[nx.DiGraph], Optional[nx.MultiDiGraph], Optional[nx.DiGraph], Optional[nx.MultiDiGraph],]:
    """Return a tuple of graphs to be used in the network search API

    Parameters
    ----------
    unsigned_graph :
        Load the latest unsigned graph. Default: True.
    unsigned_multi_graph :
        Load the latest unsigned multi graph. Default: False.
    sign_node_graph :
        Load the latest signed node graph. Default: True.
    sign_edge_graph :
        Load the latest signed edge graph. Default: False.
    use_cache :
        If True, try to load files from the designated local cache

    Returns
    -------
    Tuple[nx.DiGraph, nx.MultiDiGraph, nx.MultiDiGraph, nx.DiGraph]
        Returns, as a tuple:
            - unsigned graph
            - unsigned multi graph
            - signed edge graph
            - signed node graph

        If a graph was not chosen to be loaded or wasn't found, None will be
        returned in its place in the tuple.
    """
    # Initialize graphs
    indra_dir_graph = None
    indra_multi_di_graph = None
    indra_signed_edge_graph = None
    indra_signed_node_graph = None

    if use_cache:
        indra_mdg_cache = path.join(CACHE, INDRA_MDG)
        indra_dg_cache = path.join(CACHE, INDRA_DG)
        indra_sng_cache = path.join(CACHE, INDRA_SNG)
        indra_seg_cache = path.join(CACHE, INDRA_SEG)

        # Load unsigned
        if unsigned_graph:
            if path.isfile(indra_dg_cache):
                indra_dir_graph = file_opener(indra_dg_cache)
            else:
                logger.warning(f"File {indra_dg_cache} does not exist")

        # Load multi digraph
        if unsigned_multi_graph:
            if path.isfile(indra_mdg_cache):
                indra_multi_di_graph = file_opener(indra_mdg_cache)
            else:
                logger.warning(f"File {indra_mdg_cache} does not exist")

        # Load signed node
        if sign_node_graph:
            if path.isfile(indra_sng_cache):
                indra_signed_node_graph = file_opener(indra_sng_cache)
            else:
                logger.warning(f"File {indra_sng_cache} does not exist")

        # Load signed edge
        if sign_edge_graph:
            if path.isfile(indra_seg_cache):
                indra_signed_edge_graph = file_opener(indra_seg_cache)
            else:
                logger.warning(f"File {indra_seg_cache} does not exist")

    else:
        # Load from S3
        latest_graphs = get_latest_graphs()

        if unsigned_graph:
            if latest_graphs.get(INDRA_DG):
                indra_dir_graph = file_opener(latest_graphs[INDRA_DG])
            else:
                logger.warning(f"{INDRA_DG} was not found")

        if unsigned_multi_graph:
            if latest_graphs.get(INDRA_MDG):
                indra_multi_di_graph = file_opener(latest_graphs[INDRA_MDG])
            else:
                logger.warning(f"{INDRA_MDG} was not found")

        if sign_node_graph:
            if latest_graphs.get(INDRA_SNG):
                indra_signed_node_graph = file_opener(latest_graphs[INDRA_SNG])
            else:
                logger.warning(f"{INDRA_SNG} was not found")

        if sign_edge_graph:
            if latest_graphs.get(INDRA_SEG):
                indra_signed_edge_graph = file_opener(latest_graphs[INDRA_SEG])
            else:
                logger.warning(f"{INDRA_SEG} was not found")

    return (
        indra_dir_graph,
        indra_multi_di_graph,
        indra_signed_edge_graph,
        indra_signed_node_graph,
    )


def dump_query_json_to_s3(query_hash: Union[str, int], json_obj: Dict, get_url: bool = False) -> Optional[str]:
    """Dump a query json to S3

    Parameters
    ----------
    query_hash :
        The query hash associated with the query
    json_obj :
        The json object to upload
    get_url :
        If True return the S3 url of the object. Default: False.

    Returns
    -------
    :
        Optionally return the S3 url of the json file
    """
    filename = f"{query_hash}_query.json"
    return dump_query_result_to_s3(filename, json_obj, get_url)


def dump_result_json_to_s3(query_hash: Union[str, int], json_obj: Dict, get_url: bool = False) -> Optional[str]:
    """Dump a result json to S3

    Parameters
    ----------
    query_hash :
        The query hash associated with the result
    json_obj :
        The json object to upload
    get_url :
        If True return the S3 url of the object. Default: False.

    Returns
    -------
    :
        Optionally return the S3 url of the json file
    """
    filename = f"{query_hash}_result.json"
    return dump_query_result_to_s3(filename, json_obj, get_url)


def dump_query_result_to_s3(filename: str, json_obj: Dict, get_url: bool = False) -> Optional[str]:
    """Dump a result or query json from the network search to S3

    Parameters
    ----------
    filename :
        The filename to use
    json_obj :
        The json object to upload
    get_url :
        If True return the S3 url of the object. Default: False.

    Returns
    -------
    :
        Optionally return the S3 url of the json file
    """
    download_link = dump_json_to_s3(name=filename, json_obj=json_obj, public=True, get_url=get_url)
    if get_url:
        return download_link.split("?")[0]
    return None


def check_existence_and_date_s3(query_hash: Union[int, str]) -> Dict[str, str]:
    """Check if a query hash has corresponding result and query json on S3

    Parameters
    ----------
    query_hash :
        The query hash to check

    Returns
    -------
    :
        Dict with S3 key for query and corresponding result, if they exist
    """
    s3 = get_s3_client(unsigned=False)
    key_prefix = "indra_network_search/%s" % query_hash
    query_json_key = key_prefix + "_query.json"
    result_json_key = key_prefix + "_result.json"
    exists_dict = {}

    # Get query json
    try:
        query_json = s3.head_object(Bucket=DUMPS_BUCKET, Key=query_json_key)
    except ClientError:
        query_json = ""
    if query_json:
        exists_dict["query_json_key"] = S3Path.from_key_parts(DUMPS_BUCKET, query_json_key).to_string()

    # Get result json
    try:
        result_json = s3.head_object(Bucket=DUMPS_BUCKET, Key=result_json_key)
    except ClientError:
        result_json = ""
    if result_json:
        exists_dict["result_json_key"] = S3Path.from_key_parts(DUMPS_BUCKET, result_json_key).to_string()
    return exists_dict


def get_default_args(func: Callable) -> Dict[str, Any]:
    """Returns the default args of a function as a dictionary

    Returns a dictionary of {arg: default} of the arguments that have
    default values. Arguments without default values and `**kwargs` type
    arguments are excluded.

    Code copied from: https://stackoverflow.com/a/12627202/10478812

    Parameters
    ----------
    func :
        Function to find default arguments for

    Returns
    -------
    :
        A dictionary with the default values keyed by argument name
    """
    signature = inspect.signature(func)
    return {k: v.default for k, v in signature.parameters.items() if v.default is not inspect.Parameter.empty}


def get_mandatory_args(func: Callable) -> Set[str]:
    """Returns the mandatory args for a function as a set

    Returns the set of arguments names of a functions that are mandatory,
    i.e. does not have a default value. `**kwargs` type arguments are ignored.

    Parameters
    ----------
    func :
        Function to find mandatory arguments for

    Returns
    -------
    :
        The of mandatory arguments
    """
    signature = inspect.signature(func)
    return {k for k, v in signature.parameters.items() if v.default is inspect.Parameter.empty}


def is_context_weighted(mesh_id_list: List[str], strict_filtering: bool) -> bool:
    """Return True if context weighted

    Parameters
    ----------
    mesh_id_list :
        A list of mesh ids
    strict_filtering :
        whether to run strict context filtering or not

    Returns
    -------
    :
        True for the combination of mesh ids being present and unstrict
        filtering, otherwise False
    """
    if mesh_id_list and not strict_filtering:
        return True
    return False


def is_weighted(weighted: bool, mesh_ids: List[str], strict_mesh_filtering: bool) -> bool:
    """Return True if the combination is either weighted or context weighted

    Parameters
    ----------
    weighted :
        If a query is weighted or not
    mesh_ids :
        A list of mesh ids
    strict_mesh_filtering : bool
        whether to run strict context filtering or not

    Returns
    -------
    :
        True if the combination is either weighted or context weighted
    """
    if mesh_ids:
        ctx_w = is_context_weighted(mesh_id_list=mesh_ids, strict_filtering=strict_mesh_filtering)
        return weighted or ctx_w
    else:
        return weighted
