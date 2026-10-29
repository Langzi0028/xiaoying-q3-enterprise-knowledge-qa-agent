from enterprise_qa.chunking import build_chunks
from enterprise_qa.corpus import DOCUMENTS
from enterprise_qa.models import KnowledgeChunk
from enterprise_qa.vector_index import VectorIndex


def test_generic_reimbursement_query_diversifies_to_both_policies(tmp_path) -> None:
    index = VectorIndex.with_hash_fallback(tmp_path / "index.db")

    search = index.search("报销凭证多久提交？", build_chunks(DOCUMENTS), top_k=3)

    assert {result.document_id for result in search.results} >= {"D01", "D02"}
    assert search.mode == "hash_fallback"


def test_urgent_project_query_ranks_urgent_policy_first(tmp_path) -> None:
    index = VectorIndex.with_hash_fallback(tmp_path / "index.db")

    search = index.search("紧急项目报销凭证期限", build_chunks(DOCUMENTS), top_k=2)

    assert search.results[0].document_id == "D02"


def test_cache_rebuilds_when_embedding_fingerprint_changes(tmp_path) -> None:
    database = tmp_path / "index.db"
    chunks = build_chunks(DOCUMENTS)
    first = VectorIndex.with_hash_fallback(database, model_name="v1")
    first.search("报销", chunks)

    changed = VectorIndex.with_hash_fallback(database, model_name="v2")
    search = changed.search("报销", chunks)

    assert search.cache_status == "cache_rebuilt"


def test_cache_rebuilds_when_chunk_corpus_changes(tmp_path) -> None:
    database = tmp_path / "index.db"
    original = build_chunks(DOCUMENTS)
    index = VectorIndex.with_hash_fallback(database)
    index.search("报销", original)
    first = original[0]
    changed = [
        KnowledgeChunk(
            document_id=first.document_id,
            title=first.title,
            version=first.version,
            date=first.date,
            chunk_id=first.chunk_id,
            text=first.text + " 已更新。",
        ),
        *original[1:],
    ]

    search = index.search("报销", changed)

    assert search.cache_status == "cache_rebuilt"
