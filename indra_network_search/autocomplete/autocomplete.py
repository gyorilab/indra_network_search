"""
An API wrapping SortedStringTrie from pytrie (see
https://github.com/gsakkis/pytrie)
"""
from itertools import islice
from typing import List, Optional, Tuple, Union

from networkx import DiGraph, MultiDiGraph
from pytrie import SortedStringTrie

# Derived types
Prefixes = List[Tuple[str, str, str]]
DirGraph = Union[DiGraph, MultiDiGraph]

__all__ = ["NodesTrie", "Prefixes"]


class NodesTrie(SortedStringTrie):
    """A Trie structure that has case insensitive search methods"""

    @classmethod
    def from_node_names(cls, graph: DirGraph) -> "NodesTrie":
        """Produce a NodesTrie instance from a graph with node names as keys

        Parameters
        ----------
        graph:
            Graph from which nodes should be searchable. It is assumed the
            nodes are all keyed by strings

        Returns
        -------
        :
            An instance of a NodesTrie containing the node names of the
            graph as keys and the corresponding (name, ns, id, node degree)
            tuple as values
        """
        _is_str_nodes(graph)
        name_indexing = {}
        for node in graph.nodes:
            # Get node name in lowercase
            node_name = node.lower()
            if node_name in name_indexing:
                ix = 1
                node_name += f"_{ix}"
                # Increase index until no key is not present
                while node_name in name_indexing:
                    ix += 1
                    node_name = node.lower() + f"_{ix}"
            name_indexing[node_name] = (
                node,
                graph.nodes[node]["ns"],
                graph.nodes[node]["id"],
                graph.degree(node),
            )

        return cls(**name_indexing)

    @classmethod
    def from_node_ns_id(cls, graph: DirGraph) -> "NodesTrie":
        """Produce a NodesTrie instance from a graph using ns:id as key

        Parameters
        ----------
        graph:
            Graph from which nodes should be searchable. It is assumed the
            nodes have the attributes 'ns' and 'id' accessible via
            g.nodes[node]['ns'] and g.nodes[node]['id']

        Returns
        -------
        :
            An instance of a NodesTrie containing ns:id of each node of the
            graph as keys and the corresponding (name, ns, id, node degree)
            tuple as values
        """
        _is_str_nodes(graph)
        return cls(
            **{
                f'{graph.nodes[n]["ns"]}:{graph.nodes[n]["id"]}'.lower(): (
                    n,
                    graph.nodes[n]["ns"],
                    graph.nodes[n]["id"],
                    graph.degree(n),
                )
                for n in graph.nodes
            }
        )

    def case_keys(self, prefix: Optional[str] = None, top_n: Optional[int] = 100) -> List[str]:
        """Case insensitive wrapper around NodeTrie.keys()

        Parameters
        ----------
        prefix :
            The prefix to search
        top_n :
            The top ranked entities (by node degree)

        Returns
        -------
        List[str]
            Return a list of this trie's keys
        """
        res = [(w, deg) for _, (w, _, _, deg) in self.items(prefix.lower())]
        return [w for (w, _) in islice(sorted(res, key=lambda t: (t[1], t[0]), reverse=True), top_n)]

    def case_items(self, prefix: Optional[str] = None, top_n: int = 100) -> Prefixes:
        """Case insensitive wrapper around NodeTrie.items()

        Parameters
        ----------
        prefix :
            The prefix to search

        Returns
        -------
        :
            Return a list of (name, namespace, id) tuples
        """
        res = [t for _, t in self.items(prefix.lower())]
        return [(w, ns, _id) for w, ns, _id, _ in islice(sorted(res, key=lambda t: (t[3], t[0]), reverse=True), top_n)]


def _is_str_nodes(g: DirGraph):
    node = list(islice(g.nodes, 1))[0]
    if not isinstance(node, str):
        raise ValueError("Graph nodes are not str, cannot create NodesTrie instance")
