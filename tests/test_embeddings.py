from enterprise_qa.embeddings import EmbeddingProvider


def remove_embedding_environment(monkeypatch) -> None:
    for name in ("EMBEDDING_API_KEY", "EMBEDDING_BASE_URL", "EMBEDDING_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_missing_embedding_config_uses_hash_fallback(monkeypatch) -> None:
    remove_embedding_environment(monkeypatch)

    provider = EmbeddingProvider.from_environment()
    batch = provider.embed(["普通国内差旅报销凭证", "紧急项目报销凭证"])

    assert provider.mode == "hash_fallback"
    assert batch.mode == "hash_fallback"
    assert len(batch.vectors) == 2
    assert len(batch.vectors[0]) == len(batch.vectors[1])


def test_hash_fallback_is_deterministic() -> None:
    provider = EmbeddingProvider.hash_fallback()

    first = provider.embed(["报销凭证期限"])
    second = provider.embed(["报销凭证期限"])

    assert first.vectors == second.vectors


def test_invalid_live_embedding_response_falls_back_without_payload_leak() -> None:
    provider = EmbeddingProvider.with_test_response({"data": []})

    batch = provider.embed(["safe text"])

    assert batch.mode == "hash_fallback"
    assert batch.error_type == "ValueError"
    assert "safe text" not in str(batch.diagnostics)
