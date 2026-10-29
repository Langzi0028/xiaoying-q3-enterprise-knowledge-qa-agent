from enterprise_qa.chunking import CLAUSE_BRIDGE_VERSION, build_chunks, corpus_fingerprint
from enterprise_qa.corpus import DOCUMENTS


def test_urgent_policy_chunk_keeps_scope_and_deadline_together() -> None:
    chunks = build_chunks(DOCUMENTS)

    target = next(chunk for chunk in chunks if "15" in chunk.text)

    assert "紧急项目" in target.text
    assert "15" in target.text
    assert target.title == "Urgent Project Expense Addendum"


def test_chunk_ids_are_stable_for_unchanged_corpus() -> None:
    first = build_chunks(DOCUMENTS)
    second = build_chunks(DOCUMENTS)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert corpus_fingerprint(DOCUMENTS) == corpus_fingerprint(DOCUMENTS)
    assert CLAUSE_BRIDGE_VERSION
