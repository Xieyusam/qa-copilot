"""
Property tests for VectorStore — Property 6: 向量化存储往返.
Feature: internal-knowledge-base, Property 6: 向量化存储往返
Validates: Requirements 2.3
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.core.schemas import Chunk
from app.services.vector_store import VectorStore, ChunkResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store() -> tuple[VectorStore, MagicMock]:
    """Return a VectorStore with a mocked Chroma backend."""
    mock_chroma = MagicMock()
    with patch("app.services.vector_store.Chroma", return_value=mock_chroma):
        store = VectorStore.__new__(VectorStore)
        store._embedder = MagicMock()
        store._store = mock_chroma
    return store, mock_chroma


def _chunk(doc_id: str = "doc-1", position: int = 0, content: str = "hello") -> Chunk:
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        doc_id=doc_id,
        content=content,
        token_count=len(content.split()),
        position=position,
    )


def _embedding(dim: int = 4) -> list[float]:
    return [0.1] * dim


def _lc_doc(chunk: Chunk, filename: str = "file.txt"):
    """Build a mock LangChain Document matching what Chroma would return."""
    from langchain_core.documents import Document as LCDocument
    return LCDocument(
        page_content=chunk.content,
        metadata={
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "filename": filename,
            "position": chunk.position,
        },
    )


# ---------------------------------------------------------------------------
# Property 6: 向量化存储往返
# Validates: Requirements 2.3
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 6: 向量化存储往返 — 内容保留
@given(
    st.text(min_size=1, max_size=200),
    st.integers(min_value=0, max_value=100),
)
@settings(max_examples=50)
def test_add_then_query_preserves_content(content: str, position: int):
    """Chunks added to the store are returned with their content intact."""
    assume(content.strip())
    store, mock_chroma = _make_store()
    chunk = _chunk(content=content, position=position)
    emb = _embedding()

    mock_chroma.similarity_search_by_vector_with_relevance_scores.return_value = [
        (_lc_doc(chunk), 0.95)
    ]

    store.add_chunks([chunk], [emb], filename="file.txt")
    results = store.query(emb, top_k=1)

    assert len(results) == 1
    assert results[0].content == content
    assert results[0].position == position


# Feature: internal-knowledge-base, Property 6: 向量化存储往返 — 元数据保留
@given(
    st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"))),
    st.text(min_size=1, max_size=50),
)
@settings(max_examples=50)
def test_add_then_query_preserves_metadata(doc_id: str, filename: str):
    """doc_id and filename metadata survive the add → query round-trip."""
    assume(filename.strip())
    store, mock_chroma = _make_store()
    chunk = _chunk(doc_id=doc_id)
    emb = _embedding()

    mock_chroma.similarity_search_by_vector_with_relevance_scores.return_value = [
        (_lc_doc(chunk, filename=filename), 0.9)
    ]

    store.add_chunks([chunk], [emb], filename=filename)
    results = store.query(emb, top_k=1)

    assert results[0].doc_id == doc_id
    assert results[0].filename == filename


# Feature: internal-knowledge-base, Property 6: 向量化存储往返 — 空输入安全
def test_add_empty_chunks_is_safe():
    """add_chunks with empty list must not call Chroma and not raise."""
    store, mock_chroma = _make_store()
    store.add_chunks([], [], filename="file.txt")
    mock_chroma.add_documents.assert_not_called()


# Feature: internal-knowledge-base, Property 6: 向量化存储往返 — 结果按分数降序
@given(
    st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=2,
        max_size=5,
    )
)
@settings(max_examples=40)
def test_query_results_sorted_by_score_descending(scores: list[float]):
    """query() results must be sorted by score in descending order."""
    store, mock_chroma = _make_store()
    emb = _embedding()

    chunks = [_chunk(position=i, content=f"content {i}") for i in range(len(scores))]
    mock_chroma.similarity_search_by_vector_with_relevance_scores.return_value = [
        (_lc_doc(c), s) for c, s in zip(chunks, scores)
    ]

    results = store.query(emb, top_k=len(scores))
    result_scores = [r.score for r in results]
    assert result_scores == sorted(result_scores, reverse=True)


# Feature: internal-knowledge-base, Property 6: 向量化存储往返 — 删除后不再返回
def test_delete_by_doc_id_calls_chroma_delete():
    """delete_by_doc_id must delegate to Chroma with the correct doc_id filter."""
    store, mock_chroma = _make_store()
    store.delete_by_doc_id("doc-abc")
    mock_chroma.delete.assert_called_once_with(where={"doc_id": "doc-abc"})


# Feature: internal-knowledge-base, Property 6: 向量化存储往返 — top_k 限制
@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=30)
def test_query_respects_top_k(top_k: int):
    """query() passes top_k to Chroma and returns at most top_k results."""
    store, mock_chroma = _make_store()
    emb = _embedding()

    chunks = [_chunk(position=i, content=f"c{i}") for i in range(top_k)]
    mock_chroma.similarity_search_by_vector_with_relevance_scores.return_value = [
        (_lc_doc(c), 0.8) for c in chunks
    ]

    results = store.query(emb, top_k=top_k)
    mock_chroma.similarity_search_by_vector_with_relevance_scores.assert_called_once_with(
        emb, k=top_k, filter=None
    )
    assert len(results) <= top_k
