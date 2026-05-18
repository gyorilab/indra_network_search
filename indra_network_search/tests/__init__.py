"""
Todo:
    - Move all queries related to NetworkSearch into test_query_pipeline
    - Create standalone test files for subgraph queries
"""
from copy import deepcopy

from depmap_analysis.network_functions.net_functions import (
    _weight_from_belief,
    z_sc_weight,
)
from indra.databases import get_identifiers_url

from indra_network_search.data_models import Node

__all__ = [
    "nodes",
    "edge_data",
    "more_edge_data",
    "hash_bl_edge1",
    "hash_bl_edge2",
    "_get_node",
    "mesh_annotations_dict",
]

wm = _weight_from_belief
self_corr = 11.71018407323314


_zw = z_sc_weight


nodes = {
    "BRCA1": {"ns": "HGNC", "id": "1100"},
    "BRCA2": {"ns": "HGNC", "id": "1101"},
    "CHEK1": {"ns": "HGNC", "id": "1925"},
    "AR": {"ns": "HGNC", "id": "644"},  # A
    "testosterone": {"ns": "CHEBI", "id": "17347"},  # B
    "NR2C2": {"ns": "HGNC", "id": "7972"},  # C
    "MBD2": {"ns": "HGNC", "id": "6917"},  # D
    "PATZ1": {"ns": "HGNC", "id": "13071"},  # E
    "HDAC3": {"ns": "HGNC", "id": "4854"},  # F
    "H2AZ1": {"ns": "HGNC", "id": "4741"},  # G
    "NCOA": {"ns": "FPLX", "id": "NCOA"},
    "BRCA": {"ns": "FPLX", "id": "BRCA"},
}


mesh_annotations_dict = dict(
    [
        ("MESH:D000072230", "Sustained Virologic Response"),
        ("MESH:D000067455", "No-Show Patients"),
        ("MESH:D053669", "Syndecan-2"),
        ("MESH:C535303", "Charcot-Marie-Tooth disease, X-linked recessive, 3"),
        ("MESH:D006317", "Hearing Loss, Noise-Induced"),
        ("MESH:C000648103", "Acetatifactor muris"),
        ("MESH:D015370", "Infant Equipment"),
        ("MESH:D031225", "Rorippa"),
        ("MESH:D047348", "Hydrolyzable Tannins"),
        ("MESH:D004027", "Diencephalon"),
        ("MESH:D063127", "Secondary Care"),
        ("MESH:C535273", "Presenile dementia, Kraepelin type"),
        ("MESH:C000653063", "Burkholderia pyrrocinia"),
        ("MESH:C537262", "Hereditary pancreatitis"),
        ("MESH:D000092130", "Urticaria, Solar"),
        ("MESH:D031661", "Fraxinus"),
        ("MESH:D006099", "Granuloma"),
        ("MESH:D015981", "Epidemiologic Factors"),
        ("MESH:D025601", "Adenomatous Polyposis Coli Protein"),
        ("MESH:D000089944", "Core Stability"),
        ("MESH:C531609", "Diffuse alopecia"),
        ("MESH:D005934", "Glucagon"),
        ("MESH:D014872", "Water Movements"),
        ("MESH:D050316", "Medical Order Entry Systems"),
        ("MESH:C537171", "Paraquat lung"),
        ("MESH:C123456", "(unnamed)"),  # To test IDs without names
        ("MESH:C654321", "(unnamed)"),

    ]
)


def _get_node(name: str) -> Node:
    try:
        nd = nodes[name]
        return Node(
            name=name,
            namespace=nd["ns"],
            identifier=nd["id"],
            lookup=get_identifiers_url(db_name=nd["ns"], db_id=nd["id"]),
        )
    except KeyError as err:
        raise KeyError(f"No such node: {name}") from err


edge_data = {
    ("BRCA1", "AR"): {
        "belief": 0.999999,
        "weight": wm(0.999999),
        "z_score": self_corr - 1,
        "corr_weight": _zw(self_corr - 1, self_corr),
        "statements": [
            {
                "stmt_hash": 5603789525715921,
                "stmt_type": "Activation",
                "evidence_count": 1,
                "belief": 0.999999,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": True,
                "position": None,
                "english": "BRCA1 binds AR.",
            }
        ],
    },
    ("BRCA1", "testosterone"): {
        "belief": 0.99999,
        "weight": wm(0.99999),
        "z_score": self_corr - 2,
        "corr_weight": _zw(self_corr - 2, self_corr),
        "statements": [
            {
                "stmt_hash": 5603789525715922,
                "stmt_type": "Complex",
                "evidence_count": 1,
                "belief": 0.99999,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": True,
                "position": None,
                "english": "BRCA1 binds testosterone.",
            }
        ],
    },
    ("BRCA1", "NR2C2"): {
        "belief": 0.9999,
        "weight": wm(0.9999),
        "z_score": self_corr - 3,
        "corr_weight": _zw(self_corr - 3, self_corr),
        "statements": [
            {
                "stmt_hash": 5603789525715923,
                "stmt_type": "Complex",
                "evidence_count": 1,
                "belief": 0.9999,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": True,
                "position": None,
                "english": "BRCA1 binds NR2C2.",
            }
        ],
    },
    ("BRCA1", "MBD2"): {
        "belief": 0.999,
        "weight": wm(0.999),
        "z_score": self_corr - 4,
        "corr_weight": _zw(self_corr - 4, self_corr),
        "statements": [
            {
                "stmt_hash": 5603789525715924,
                "stmt_type": "Complex",
                "evidence_count": 1,
                "belief": 0.999,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": False,
                "position": None,
                "english": "BRCA1 binds MBD2.",
            }
        ],
    },
    ("BRCA1", "PATZ1"): {
        "belief": 0.99,
        "weight": wm(0.99),
        "z_score": self_corr - 5,
        "corr_weight": _zw(self_corr - 5, self_corr),
        "statements": [
            {
                "stmt_hash": 5603789525715925,
                "stmt_type": "Complex",
                "evidence_count": 1,
                "belief": 0.99,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": False,
                "position": None,
                "english": "BRCA1 binds PATZ1.",
            }
        ],
    },
    ("AR", "CHEK1"): {
        "belief": 0.999999,
        "weight": wm(0.999999),
        "z_score": self_corr - 1,
        "corr_weight": _zw(self_corr - 1, self_corr),
        "statements": [
            {
                "stmt_hash": 915990,
                "stmt_type": "Activation",
                "evidence_count": 1,
                "belief": 0.999999,
                "source_counts": {"pc": 1},
                "residue": "T",
                "weight": 0.23572233352106983,
                "curated": True,
                "position": "3387",
                "english": "CHEK1 activates BRCA2.",
            }
        ],
    },
    ("testosterone", "CHEK1"): {
        "belief": 0.99999,
        "weight": wm(0.99999),
        "z_score": self_corr - 2,
        "corr_weight": _zw(self_corr - 2, self_corr),
        "statements": [
            {
                "stmt_hash": 915991,
                "stmt_type": "Phosphorylation",
                "evidence_count": 1,
                "belief": 0.99999,
                "source_counts": {"pc": 1},
                "residue": "T",
                "weight": 0.23572233352106983,
                "curated": True,
                "position": "3387",
                "english": "CHEK1 phosphorylates BRCA2.",
            }
        ],
    },
    ("NR2C2", "CHEK1"): {
        "belief": 0.9999,
        "weight": wm(0.9999),
        "z_score": self_corr - 3,
        "corr_weight": _zw(self_corr - 3, self_corr),
        "statements": [
            {
                "stmt_hash": 915992,
                "stmt_type": "Phosphorylation",
                "evidence_count": 1,
                "belief": 0.9999,
                "source_counts": {"pc": 1},
                "residue": "T",
                "weight": 0.23572233352106983,
                "curated": True,
                "position": "3387",
                "english": "CHEK1 phosphorylates BRCA2.",
            }
        ],
    },
    ("MBD2", "CHEK1"): {
        "belief": 0.999,
        "weight": wm(0.999),
        "z_score": self_corr - 4,
        "corr_weight": _zw(self_corr - 4, self_corr),
        "statements": [
            {
                "stmt_hash": 560370,
                "stmt_type": "Complex",
                "evidence_count": 1,
                "belief": 0.999,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": False,
                "position": None,
                "english": "MBD2 binds CHEK1.",
            }
        ],
    },
    ("PATZ1", "CHEK1"): {
        "belief": 0.99,
        "weight": wm(0.99),
        "z_score": self_corr - 5,
        "corr_weight": _zw(self_corr - 5, self_corr),
        "statements": [
            {
                "stmt_hash": 560370,
                "stmt_type": "Complex",
                "evidence_count": 1,
                "belief": 0.99,
                "source_counts": {"sparser": 1},
                "residue": None,
                "weight": 2,
                "curated": False,
                "position": None,
                "english": "PATZ1 binds HDAC3.",
            }
        ],
    },
    ("CHEK1", "BRCA2"): {
        "belief": 0.98,
        "weight": 4.1e-05,
        "z_score": self_corr - 6,
        "corr_weight": _zw(self_corr - 6, self_corr),
        "statements": [
            {
                "stmt_hash": 915993,
                "stmt_type": "Activation",
                "evidence_count": 1,
                "belief": 0.98,
                "source_counts": {"pc": 1},
                "residue": "T",
                "weight": 0.23572233352106983,
                "curated": True,
                "position": "3387",
                "english": "CHEK1 phosphorylates BRCA2.",
            }
        ],
    },
    ("CHEK1", "NCOA"): {
        "belief": 0.7,
        "weight": wm(0.7),
        "z_score": self_corr - 7,
        "corr_weight": _zw(self_corr - 7, self_corr),
        "statements": [
            {
                "stmt_hash": 915994,
                "stmt_type": "Farnesylation",
                "evidence_count": 1,
                "belief": 0.7,
                "source_counts": {"pc": 1},
                "residue": "T",
                "weight": 0.23572233352106983,
                "curated": False,
                "position": "3387",
                "english": "CHEK1 farnesylates NCOA.",
            }
        ],
    },
    ("NCOA", "BRCA2"): {
        "belief": 0.7,
        "weight": wm(0.7),
        "z_score": self_corr - 7,
        "corr_weight": _zw(self_corr - 7, self_corr),
        "statements": [
            {
                "stmt_hash": 915995,
                "stmt_type": "Acetylation",
                "evidence_count": 1,
                "belief": 0.7,
                "source_counts": {"pc": 1},
                "residue": "T",
                "weight": 0.23572233352106983,
                "curated": False,
                "position": "3387",
                "english": "NCOA acetylates BRCA2.",
            }
        ],
    },
    ("BRCA2", "BRCA1"): {
        "belief": 0.98,
        "weight": 4.1e-05,
        "z_score": self_corr - 6,
        "corr_weight": _zw(self_corr - 6, self_corr),
        "statements": [
            {
                "stmt_hash": -976543,
                "stmt_type": "Inhibition",
                "evidence_count": 1,
                "belief": 0.98,
                "source_counts": {"pc": 1},
                "residue": None,
                "weight": 0.23572233352106983,
                "curated": True,
                "position": None,
                "english": "CHEK1 inhibits BRCA2.",
            }
        ],
    },
    ("BRCA2", "BRCA"): {
        "belief": 1,
        "weight": wm(1),
        "z_score": self_corr,
        "corr_weight": _zw(self_corr, self_corr),
        "statements": [
            {
                "stmt_hash": "https://identifiers.org/fplx:BRCA",
                "stmt_type": "fplx",
                "evidence_count": 1,
                "belief": 1,
                "source_counts": {"fplx": 1},
                "residue": None,
                "weight": wm(1),
                "curated": True,
                "position": None,
                "english": "FPLX:BRCA is an ontological parent of HGNC:1101",
                "z_score": 0,
                "corr_weight": 1,
            }
        ],
    },
    ("BRCA1", "BRCA"): {
        "belief": 1,
        "weight": wm(1),
        "z_score": self_corr,
        "corr_weight": _zw(self_corr, self_corr),
        "statements": [
            {
                "stmt_hash": "https://identifiers.org/fplx:BRCA",
                "stmt_type": "fplx",
                "evidence_count": 1,
                "belief": 1,
                "source_counts": {"fplx": 1},
                "residue": None,
                "weight": wm(1),
                "curated": True,
                "position": None,
                "english": "FPLX:BRCA is an ontological parent of HGNC:1100",
                "z_score": 0,
                "corr_weight": 1,
            }
        ],
    },
}

more_edge_data = {}
for edge, v in edge_data.items():
    # Add parallel edges for BRCA1 and CHEK1, excluding BRCA fplx edges
    more_edge_data[edge] = v
    if "BRCA1" == edge[0] and edge[1] != "BRCA":
        parallel_edge = ("HDAC3", edge[1])
        vc = deepcopy(v)
        vc["statements"][0]["english"] = v["statements"][0]["english"].replace("BRCA1", "HDAC3")
        more_edge_data[parallel_edge] = v

    if "CHEK1" == edge[1] and edge[0] != "BRCA":
        parallel_edge = (edge[0], "H2AZ1")
        vc = deepcopy(v)
        vc["statements"][0]["english"] = v["statements"][0]["english"].replace("CHEK1", "H2AZ1")
        more_edge_data[parallel_edge] = v
hash_bl_edge1 = ("BRCA1", "AR")
hash_bl_edge2 = ("AR", "CHEK1")
