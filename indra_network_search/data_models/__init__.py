"""
This file contains data models for queries, results and arguments to algorithm
functions.
"""
# todo:
#  - Use constr(to_lower=True) in appropriate places to enforce lowercase:
#     + node_blacklist
#     + allowed_ns
#     + stmt_filter (allowed statement types)
#  - Use constr(min_length=N) to enforce that str fields are not empty
#  - Figure out how to use conlist and other con* enforcers for e.g.:
#     + Enforce hashes to be int and/or str
#     + Lowercase for string filters
#  - Figure out how to do "at least one of" filters. See:
#    https://github.com/samuelcolvin/pydantic/issues/506
#    Related: Check if it's possible to apply a setting that can be set on
#    creation to allow different checks, e.g. allow either of:
#          1) source XOR target
#          2) source AND target
#  - In FilterOptions, set overall weighted based on values of weighted
#    context weighted. See here for more info:
#    https://stackoverflow.com/q/54023782/10478812
#  - Make the is_empty method also look into the children of the object?
import logging
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import parse_qsl

from depmap_analysis.network_functions.net_functions import SIGNS_TO_INT_SIGN
from indra.explanation.pathfinding.util import EdgeFilter
from networkx import DiGraph
from pydantic import (
    BaseModel,
    Extra,
    HttpUrl,
    confloat,
    conint,
    conlist,
    constr,
    root_validator,
    validator,
)

from indra_network_search.rest_util import (
    StrNode,
    get_query_hash,
    is_context_weighted,
    is_weighted,
)

try:
    # Py 3.8+
    from typing import Literal
except ImportError:
    # Py 3.7-
    from typing_extensions import Literal

__all__ = [
    "NetworkSearchQuery",
    "SubgraphRestQuery",
    "MultiInteractorsRestQuery",
    "ApiOptions",
    "ShortestSimplePathOptions",
    "BreadthFirstSearchOptions",
    "DijkstraOptions",
    "SharedInteractorsOptions",
    "OntologyOptions",
    "MultiInteractorsOptions",
    "Node",
    "StmtData",
    "EdgeData",
    "EdgeDataByHash",
    "Path",
    "PathResultData",
    "OntologyResults",
    "SharedInteractorsResults",
    "Results",
    "FilterOptions",
    "SubgraphOptions",
    "SubgraphResults",
    "MultiInteractorsResults",
    "DEFAULT_TIMEOUT",
    "MAX_TIMEOUT",
    "WEIGHT_NAME_MAPPING",
    "basemodels_equal",
    "basemodel_in_iterable",
    "StmtTypeSupport",
]


logger = logging.getLogger(__name__)


# Set defaults
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 590  # Less than timeout on the load balancer and nginx
WEIGHT_NAME_MAPPING = {
    "belief": "weight",
    "context": "context_weight",
    "z_score": "corr_weight",
    "unweighted": None,
}


# Models for API options and filtering options
class ApiOptions(BaseModel):
    """Options that determine API behaviour"""

    sign: Optional[int] = None
    fplx_expand: Optional[bool] = False
    user_timeout: Optional[Union[float, bool]] = False
    two_way: Optional[bool] = False
    shared_regulators: Optional[bool] = False
    format: Optional[str] = "json"


class FilterOptions(BaseModel):
    """Options for filtering out nodes or edges"""

    stmt_filter: List[constr(to_lower=True)] = []
    allowed_ns: List[constr(to_lower=True)] = []
    node_blacklist: List[str] = []
    path_length: Optional[int] = None
    belief_cutoff: float = 0.0
    curated_db_only: bool = False
    max_paths: int = 50
    cull_best_node: Optional[int] = None
    weighted: Optional[Literal["weight", "context_weight", "corr_weight"]] = None
    context_weighted: bool = False
    overall_weighted: bool = False

    def no_filters(self) -> bool:
        """Return True if all filter options are set to defaults"""
        return (
            len(self.stmt_filter) == 0
            and len(self.allowed_ns) == 0
            and len(self.node_blacklist) == 0
            and self.path_length is None
            and self.belief_cutoff == 0.0
            and self.curated_db_only is False
        )

    def no_stmt_filters(self):
        """Return True if the stmt filter options allow all statements"""
        return self.belief_cutoff == 0.0 and len(self.stmt_filter) == 0 and self.curated_db_only is False

    def no_node_filters(self):
        """Return True if the node filter options allow all nodes"""
        return len(self.node_blacklist) == 0 and len(self.allowed_ns) == 0


class NetworkSearchQuery(BaseModel):
    """The query model for network searches"""

    source: constr(strip_whitespace=True) = ""
    target: constr(strip_whitespace=True) = ""
    stmt_filter: List[constr(to_lower=True, strip_whitespace=True)] = []
    filter_curated: bool = True
    allowed_ns: List[constr(to_lower=True, strip_whitespace=True)] = []
    node_blacklist: List[str] = []
    path_length: Optional[int] = None
    depth_limit: int = 2
    sign: Optional[conint(ge=0, le=1)] = None
    weighted: Literal["belief", "context", "z_score", "unweighted"] = "unweighted"
    belief_cutoff: Union[float, bool] = 0.0
    curated_db_only: bool = False
    fplx_expand: bool = False
    k_shortest: int = 50
    max_per_node: int = 5
    cull_best_node: Optional[int] = None
    mesh_ids: List[str] = []
    strict_mesh_id_filtering: bool = False
    const_c: int = 1
    const_tk: int = 10
    user_timeout: Union[float, bool] = DEFAULT_TIMEOUT
    two_way: bool = False
    shared_regulators: bool = False
    terminal_ns: List[str] = []
    format: str = "json"  # This attribute is probably obsolete now

    @validator("path_length")
    def is_positive_int(cls, pl: int):
        """Validate path_length >= 1 if given"""
        if isinstance(pl, int) and pl < 1:
            raise ValueError("path_length must be integer > 0")
        return pl

    @validator("max_per_node")
    def is_pos_int(cls, mpn: Union[int, bool]):
        """Validate max_per_node >= 1 if given"""
        if isinstance(mpn, int) and mpn < 1:
            raise ValueError("max_per_node must be integer > 0")
        return mpn

    @validator("cull_best_node")
    def is_int_gt2(cls, cbn: Optional[int]):
        """Validate cull_best_node >= 2"""
        if isinstance(cbn, int) and cbn < 2:
            raise ValueError("cull_best_node must be integer > 1 if provided")
        return cbn

    @root_validator
    def mesh_ids_required_for_context(cls, values):
        """MeSH context weighting requires at least one MeSH ID."""
        # Todo: Also validate the mesh IDs
        if values.get("weighted") != "context":
            return values
        mesh_ids = values.get("mesh_ids") or []
        if not any(isinstance(m, str) and m.strip() for m in mesh_ids):
            raise ValueError(
                "mesh_ids must contain at least one MeSH ID when weighted is 'context'"
            )
        return values

    @classmethod
    def from_share_url(cls, share_url: str):
        """Create a NetworkSearchQuery from a share URL"""
        # Parse the URL - it has the form:
        # https://network.indra.bio/#/?key1=val1&key2=val2...
        # We only need the part after #/?
        if "#/?" not in share_url:
            raise ValueError("Not a valid share URL")
        share_url_qs = share_url.split("#/?", 1)[1]

        query_dict = dict(parse_qsl(share_url_qs))
        return cls(**query_dict)

    class Config:
        allow_mutation = False  # Error for any attempt to change attributes
        extra = Extra.forbid  # Error if non-specified attributes are given

    def is_overall_weighted(self) -> bool:
        """Return True if this query is weighted

        This method is used to determine if a weighted search needs to be
        done using either of shortest_simple_paths and open_dijkstra_search.

        The exception to self.weighted not being None but still be
        unweighted is strict mesh id search.
        """
        return is_weighted(
            weighted=self.weighted in ("belief", "z_score"),
            mesh_ids=self.mesh_ids,
            strict_mesh_filtering=self.strict_mesh_id_filtering,
        )

    def is_context_weighted(self):
        """Return True if this query is context weighted"""
        return is_context_weighted(mesh_id_list=self.mesh_ids, strict_filtering=self.strict_mesh_id_filtering)

    def get_hash(self):
        """Get the corresponding query hash of the query"""
        return get_query_hash(self.dict(), ignore_keys=["format"])

    def reverse_search(self):
        """Return a copy of the query with source and target switched"""
        model_copy = self.copy(deep=True).dict(exclude={"source", "target"})
        source = self.target
        target = self.source
        return self.__class__(source=source, target=target, **model_copy)

    def get_int_sign(self) -> Optional[int]:
        """Return the integer representation of the sign"""
        if self.sign is None or self.sign == "":
            return None
        try:
            sign = int(self.sign)
            assert sign in (0, 1)
        except Exception as exc:
            logger.info(
                f"Could not convert {self.sign} of type "
                f"{type(self.sign)} to int ({str(exc)}), trying "
                f"SIGNS mapping"
            )
            sign = SIGNS_TO_INT_SIGN.get(self.sign)
        return sign

    def get_filter_options(self) -> FilterOptions:
        """Returns the filter options"""
        return FilterOptions(
            stmt_filter=self.stmt_filter,
            allowed_ns=self.allowed_ns,
            node_blacklist=self.node_blacklist,
            path_length=self.path_length,
            belief_cutoff=self.belief_cutoff,
            curated_db_only=self.curated_db_only,
            max_paths=self.k_shortest,
            cull_best_node=self.cull_best_node,
            overall_weighted=self.is_overall_weighted(),
            weighted=WEIGHT_NAME_MAPPING.get(self.weighted),
            context_weighted=is_context_weighted(
                mesh_id_list=self.mesh_ids,
                strict_filtering=self.strict_mesh_id_filtering,
            ),
        )


# Models for the run options
# Todo:
#  1. instead of manually setting defaults here, use introspection of
#     function and look up functions default:
#     >>> def func(par: int = 0):
#     ...     return par
#     >>> import inspect
#     >>> func_pars = inspect.signature(func).parameters
#     >>> arg = func_pars['par']
#     >>> arg.default
#  2. For "not-None" defaults: set value to default if None is provided:
#     https://stackoverflow.com/q/63616798/10478812
#     Good for e.g. max_paths
class ShortestSimplePathOptions(BaseModel):
    """Arguments for indra.explanation.pathfinding.shortest_simple_paths"""

    source: Union[str, Tuple[str, int]]
    target: Union[str, Tuple[str, int]]
    weight: Optional[str] = None
    ignore_nodes: Optional[Set[Union[str, Tuple[str, int]]]] = None
    ignore_edges: Optional[Set[Tuple[str, str]]] = None
    hashes: Optional[List[int]] = None
    ref_counts_function: Optional[Callable] = None
    strict_mesh_id_filtering: Optional[bool] = False
    const_c: Optional[int] = 1
    const_tk: Optional[int] = 10


class BreadthFirstSearchOptions(BaseModel):
    """Arguments for indra.explanation.pathfinding.bfs_search"""

    source_node: Union[str, Tuple[str, int]]
    reverse: Optional[bool] = False
    depth_limit: Optional[int] = 2
    path_limit: Optional[int] = None
    max_per_node: Optional[int] = 5
    node_filter: Optional[List[str]] = None
    node_blacklist: Optional[Set[str]] = None
    terminal_ns: Optional[List[str]] = None
    sign: Optional[int] = None
    max_memory: Optional[int] = int(2 ** 29)
    hashes: Optional[List[int]] = None
    allow_edge: Optional[Callable[[DiGraph, StrNode, StrNode], bool]] = None
    edge_filter: Optional[EdgeFilter] = None
    strict_mesh_id_filtering: Optional[bool] = False


class DijkstraOptions(BaseModel):
    """Arguments for open_dijkstra_search"""

    start: Union[str, Tuple[str, int]]
    reverse: Optional[bool] = False
    path_limit: Optional[int] = None
    # node_filter: Optional[List[str]] = None  # Currently not implemented
    hashes: Optional[List[int]] = None
    ignore_nodes: Optional[List[str]] = None
    ignore_edges: Optional[List[Tuple[str, str]]] = None
    terminal_ns: Optional[List[str]] = None
    weight: Optional[str] = None
    ref_counts_function: Optional[Callable] = None
    const_c: Optional[int] = 1
    const_tk: Optional[int] = 10


class SharedInteractorsOptions(BaseModel):
    """Arguments for indra_network_search.pathfinding.shared_interactors"""

    source: StrNode
    target: StrNode
    allowed_ns: Optional[List[str]] = None
    stmt_types: Optional[List[str]] = None
    source_filter: Optional[List[str]] = None
    max_results: Optional[int] = 50
    regulators: Optional[bool] = False
    sign: Optional[int] = None


class OntologyOptions(BaseModel):
    """Arguments for indra_network_search.pathfinding.shared_parents"""

    source_ns: str
    source_id: str
    target_ns: str
    target_id: str
    max_paths: int = 50
    immediate_only: Optional[bool] = False
    is_a_part_of: Optional[Set[str]] = None


class MultiInteractorsOptions(BaseModel):
    """Multi interactors options"""

    nodes: List[str]
    downstream: bool
    allowed_ns: Optional[List[str]] = None
    stmt_types: Optional[List[str]] = None
    source_filter: Optional[List[str]] = None
    max_results: int = 50
    hash_blacklist: Optional[Set[int]] = None
    node_blacklist: Optional[List[str]] = None
    belief_cutoff: float = 0.0
    curated_db_only: bool = False


# Models and sub-models for the Results
class Node(BaseModel):
    """Data for a node"""

    name: Optional[constr(min_length=1)]
    namespace: constr(min_length=1)
    identifier: constr(min_length=1)
    lookup: Optional[constr(min_length=1)]
    sign: Optional[conint(ge=0, le=1)]

    def get_unsigned_node(self):
        """Get unsigned version of this node instance"""
        return self.__class__(**self.dict(exclude={"sign"}, exclude_defaults=True))

    def signed_node_tuple(self) -> Tuple[str, int]:
        """Get a signed node tuple of node name and node sign

        Returns
        -------
        :
            A name, sign tuple

        Raises
        ------
        TypeError
            If sign is not defined, a TypeError
        """
        if self.sign is None:
            raise TypeError("Node is unsigned, unable to produce a signed node tuple")
        return self.name, self.sign


class StmtData(BaseModel):
    """Data for one statement supporting an edge"""

    stmt_type: str
    evidence_count: conint(ge=1)
    stmt_hash: Union[int, HttpUrl]
    source_counts: Dict[str, int]
    belief: confloat(ge=0.0, le=1.0)
    curated: bool
    english: str
    weight: Optional[float] = None
    residue: Optional[str] = ""
    position: Optional[str] = ""
    initial_sign: Optional[conint(ge=0, le=1)] = None
    db_url_hash: str  # Linkout to hash-level


class StmtTypeSupport(BaseModel):
    """Data per statement type"""

    stmt_type: str
    source_counts: Dict[str, int] = {}
    statements: List[StmtData]

    def set_source_counts(self):
        """Updates the source count field from the set statement data"""
        self.source_counts = sum([Counter(**sd.source_counts) for sd in self.statements], Counter())


class EdgeData(BaseModel):
    """Data for one single edge"""

    edge: List[Node]  # Edge supported by statements
    statements: Dict[str, StmtTypeSupport]  # key by stmt_type
    belief: confloat(ge=0, le=1)  # Aggregated belief
    weight: confloat(ge=0)  # Weight corresponding to aggregated belief weight
    context_weight: Union[str, confloat(gt=0), Literal["N/A"]] = "N/A"  # Set for context
    z_score: Optional[float] = None  # z-score
    logp: Optional[float] = None  # log p-value
    corr_weight: Optional[confloat(gt=0.0)] = None  # Weight from z-score or logp
    sign: Optional[conint(ge=0, le=1)]  # Used for signed paths
    db_url_edge: str  # Linkout to subj-obj level
    source_counts: Dict[str, int] = {}

    def is_empty(self) -> bool:
        """Return True if len(statements) == 0"""
        return len(self.statements) == 0

    def set_source_counts(self):
        """Updates the source count from the contained data in self.statements"""
        self.source_counts = sum(
            [Counter(**sts.source_counts) for sts in self.statements.values()],
            Counter(),
        )


class EdgeDataByHash(BaseModel):
    """Data for one single edge, with data keyed by hash"""

    edge: List[Node]
    stmts: Dict[int, StmtData]  # Hash remain as int for JSON
    belief: float
    weight: float
    db_url_edge: str  # Linkout to subj-obj level
    url_by_type: Dict[str, str]  # Linkout per statement type
    # sign: Optional[int]  # Used for signed paths
    # context_weight: Union[str, float] = 'N/A'  # Set for context search


class Path(BaseModel):
    """Results for a single path"""

    # The entries are assumed to be co-ordered
    # path = [a, b, c]
    # edge_data = [EdgeData(a, b), EdgeData(b, c)]
    path: List[Node]  # Contains the path
    edge_data: List[EdgeData]  # Contains supporting data, same order as path

    def is_empty(self) -> bool:
        """Return True if len(path) == 0 or len(edge_data) == 0"""
        return len(self.path) == 0 or len(self.edge_data) == 0


class PathResultData(BaseModel):
    """Results for any of the path algorithms"""

    # Results for bfs_search, shortest_simple_paths and open_dijkstra_search
    # It is assumed that at least one of source or target will be set
    source: Optional[Node] = None
    target: Optional[Node] = None
    paths: Dict[int, List[Path]]  # keyed by node count

    def is_empty(self) -> bool:
        """Return True if paths list is empty"""
        return len(self.paths) == 0


class OntologyResults(BaseModel):
    """Results for shared_parents"""

    source: Node
    target: Node
    parents: List[Node]

    def is_empty(self) -> bool:
        """Return True if parents list is empty"""
        return len(self.parents) == 0


class SharedInteractorsResults(BaseModel):
    """Results for shared targets and shared regulators"""

    # s->x; t->x
    source_data: List[EdgeData]
    target_data: List[EdgeData]
    downstream: bool

    def is_empty(self):
        """Return True if both source and target data is empty"""
        return len(self.source_data) == 0 and len(self.target_data) == 0


class SubgraphResults(BaseModel):
    """Results for get_subgraph_edges"""

    input_nodes: List[Node]
    not_in_graph: List[Node]
    available_nodes: List[Node]
    edges: List[EdgeDataByHash]


class MultiInteractorsResults(BaseModel):
    """Results post direct_multi_interactors"""

    targets: List[Node]
    regulators: List[Node]
    edge_data: List[EdgeData] = []


class Results(BaseModel):
    """The model wrapping all results from the NetworkSearchQuery"""

    query_hash: str
    time_limit: float
    timed_out: bool
    hashes: List[str] = []  # Cast as string for JavaScript
    path_results: Optional[PathResultData] = None
    reverse_path_results: Optional[PathResultData] = None
    ontology_results: Optional[OntologyResults] = None
    shared_target_results: Optional[SharedInteractorsResults] = None
    shared_regulators_results: Optional[SharedInteractorsResults] = None


class MultiInteractorsRestQuery(BaseModel):
    """Multi interactors rest query"""

    nodes: List[str]
    downstream: bool
    allowed_ns: Optional[List[constr(strip_whitespace=True, to_lower=True, min_length=1)]] = None
    stmt_types: Optional[List[constr(strip_whitespace=True, to_lower=True, min_length=1)]] = None
    source_filter: Optional[List[constr(strip_whitespace=True, to_lower=True, min_length=1)]] = None
    max_results: int = 50
    node_blacklist: Optional[List[str]] = None
    belief_cutoff: float = 0.0
    curated_db_only: bool = False
    timeout: confloat(ge=5.0, le=120.0) = DEFAULT_TIMEOUT


class SubgraphRestQuery(BaseModel):
    """Subgraph query"""

    nodes: conlist(item_type=Node, min_items=1, max_items=4000)
    timeout: confloat(ge=1, le=MAX_TIMEOUT) = MAX_TIMEOUT


class SubgraphOptions(BaseModel):
    """Argument for indra_network_search.pathfinding.get_subgraph_edges"""

    nodes: List[Node]


def basemodels_equal(
    basemodel: BaseModel,
    other_basemodel: BaseModel,
    any_item: bool,
    exclude: Optional[Set[str]] = None,
) -> bool:
    """Wrapper to test two basemodels for equality, can exclude irrelevant keys

    Parameters
    ----------
    basemodel :
        BaseModel to test against other_basemodel
    other_basemodel :
        BaseModel to test against basemodel
    any_item :
        If True, use any() when testing collections for equality, otherwise
        use all(), i.e. the collections must match exactly
    exclude :
        A set of field names to exclude from the basemodels

    Returns
    -------
    :
        True if the two models are equal
    """
    b1d = basemodel.dict(exclude=exclude)
    b2d = other_basemodel.dict(exclude=exclude)
    qual_func = any if any_item else all
    return qual_func(_equals(b1d[k1], b2d[k2], any_item) for k1, k2 in zip(b1d, b2d))


def _equals(
    d1: Union[str, int, float, List, Set, Tuple, Dict],
    d2: Union[str, int, float, List, Set, Tuple, Dict],
    any_item: bool,
) -> bool:
    qual_func = any if any_item else all
    if d1 is None:
        return d2 is None
    elif isinstance(d1, (str, int, float)):
        return d1 == d2
    elif isinstance(d1, (list, tuple)):
        return qual_func(_equals(e1, e2, any_item) for e1, e2 in zip(d1, d2))
    elif isinstance(d1, set):
        return d1 == d2
    elif isinstance(d1, dict):
        return qual_func(_equals(d1[k1], d2[k2], False) for k1, k2 in zip(d1, d2))
    else:
        raise TypeError(f"Unable to do comparison of type {type(d1)}")


def basemodel_in_iterable(
    basemodel: BaseModel,
    iterable: Iterable,
    any_item: bool,
    exclude: Optional[Set[str]] = None,
) -> bool:
    """Test if a basemodel object is part of a collection

    Parameters
    ----------
    basemodel :
        A BaseModel to test membership in iterable for
    iterable :
        An iterable that contains objects to test for equality with basemodel
    any_item :
        If True, use any() when testing collections for equality, otherwise
        use all(), i.e. the collections must match exactly
    exclude :
        A set of field names to exclude from the basemodels

    Returns
    -------
    :
        True if basemodel is found in the collection
    """
    return any(
        [
            basemodels_equal(
                basemodel=basemodel,
                other_basemodel=ob,
                any_item=any_item,
                exclude=exclude,
            )
            for ob in iterable
        ]
    )
