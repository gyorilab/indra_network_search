from pydantic import ValidationError
from indra_network_search.data_models import StmtData, NetworkSearchQuery


def test_stmt_data():
    stmt_dict = {
        "stmt_type": "fplx",
        "evidence_count": 1,
        "source_counts": {"fplx": 1},
        "stmt_hash": "https://identifiers.org/fplx:FANC",
        "belief": 1.0,
        "weight": 1e-15,
        "curated": True,
        "english": "FPLX:FANC is an ontological parent of HGNC:1100",
        "corr_weight": 1,
    }
    stmt_data = StmtData(db_url_hash=stmt_dict["stmt_hash"], **stmt_dict)
    assert stmt_data.source_counts == {"fplx": 1}


def test_network_search_query_mesh():
    # Test the mesh option validation
    nsq = NetworkSearchQuery(source="A", weighted="context", mesh_ids=["D000001", "D000002"])
    try:
        NetworkSearchQuery(source="A", weighted="context")
    except Exception as e:
        assert "mesh_ids must contain at least one MeSH ID" in str(e)
        assert isinstance(e, ValidationError)


def test_network_search_query_cull_best_node():
    nsq = NetworkSearchQuery(source="A", cull_best_node=2)
    try:
        NetworkSearchQuery(source="A", cull_best_node=1)
    except Exception as e:
        assert "cull_best_node must be integer > 1" in str(e)
        assert isinstance(e, ValidationError)


def test_network_search_query_max_per_node():
    nsq = NetworkSearchQuery(source="A", max_per_node=2)
    try:
        NetworkSearchQuery(source="A", max_per_node=0)
    except Exception as e:
        assert "max_per_node must be integer > 0" in str(e)
        assert isinstance(e, ValidationError)


def test_network_search_query_path_length():
    nsq = NetworkSearchQuery(source="A", path_length=2)
    try:
        NetworkSearchQuery(source="A", path_length=0)
    except Exception as e:
        assert "path_length must be integer > 0" in str(e)
        assert isinstance(e, ValidationError)
