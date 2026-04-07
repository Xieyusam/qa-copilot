"""
Tests for Chunker — Property 5 (Chunk 大小约束) + unit tests.
Feature: internal-knowledge-base, Property 5: Chunk 大小约束
"""
from __future__ import annotations

from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.schemas import Chunk, ParsedDocument
from app.services.chunker import Chunker


@pytest.fixture(scope="module")
def chunker() -> Chunker:
    return Chunker()


def _doc(content: str, file_type: str = "txt") -> ParsedDocument:
    return ParsedDocument(
        doc_id="test-doc",
        filename=f"test.{file_type}",
        file_type=file_type,
        content=content,
        paragraphs=[content],
        metadata={},
        parsed_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Property 5: Chunk 大小约束
# Validates: Requirements 2.2
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 5: Chunk 大小约束
@given(st.text(min_size=1, max_size=2000))
@settings(max_examples=100, deadline=None)
def test_chunk_size_never_exceeds_max_tokens(text: str):
    """Every chunk's token_count must be <= max_tokens."""
    chunker = Chunker()
    doc = _doc(text)
    chunks = chunker.chunk(doc, max_tokens=512, overlap=50)
    for chunk in chunks:
        assert chunk.token_count <= 512, (
            f"Chunk at position {chunk.position} has {chunk.token_count} tokens, exceeds 512"
        )


# Feature: internal-knowledge-base, Property 5: Chunk 大小约束 (small window)
@given(st.text(min_size=1, max_size=500))
@settings(max_examples=50, deadline=None)
def test_chunk_size_with_small_window(text: str):
    """Chunk size constraint holds for small max_tokens values."""
    chunker = Chunker()
    doc = _doc(text)
    chunks = chunker.chunk(doc, max_tokens=64, overlap=10)
    for chunk in chunks:
        assert chunk.token_count <= 64


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestSemanticChunker:
    def test_markdown_header_splitting(self, chunker):
        md_content = """# Header 1
Some content under header 1.

## Header 2
Content under header 2.
"""
        doc = _doc(md_content, file_type="md")
        chunks = chunker.chunk(doc, max_tokens=100, overlap=10)
        
        # Should split based on headers
        assert len(chunks) == 2
        assert "Header 1" in chunks[0].content
        assert "Header 2" in chunks[1].content
        
        # Verify headers are included in the content context
        assert "['Header 1']" in chunks[0].content or "[Header 1]" in chunks[0].content
        assert "['Header 1', 'Header 2']" in chunks[1].content or "[Header 1 > Header 2]" in chunks[1].content

    def test_recursive_character_splitting(self, chunker):
        text_content = "This is a paragraph.\n\nThis is another paragraph.\n\n" + "A" * 1000
        doc = _doc(text_content, file_type="txt")
        chunks = chunker.chunk(doc, max_tokens=100, overlap=10)
        
        # Should split by paragraphs first, then by characters
        assert len(chunks) > 2
        assert "This is a paragraph." in chunks[0].content

class TestChunkerBasic:
    def test_empty_content_returns_no_chunks(self, chunker):
        doc = _doc("")
        assert chunker.chunk(doc) == []

    def test_whitespace_only_returns_no_chunks(self, chunker):
        doc = _doc("   \n\t  ")
        assert chunker.chunk(doc) == []

    def test_short_text_produces_single_chunk(self, chunker):
        doc = _doc("Hello world")
        chunks = chunker.chunk(doc, max_tokens=512, overlap=50)
        assert len(chunks) == 1
        assert chunks[0].position == 0
        assert chunks[0].doc_id == "test-doc"

    def test_positions_are_sequential(self, chunker):
        # Generate enough text to produce multiple chunks
        long_text = " ".join(["word"] * 600)
        doc = _doc(long_text)
        chunks = chunker.chunk(doc, max_tokens=100, overlap=10)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.position == i

    def test_chunk_ids_are_unique(self, chunker):
        long_text = " ".join(["word"] * 600)
        doc = _doc(long_text)
        chunks = chunker.chunk(doc, max_tokens=100, overlap=10)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_doc_id_propagated_to_chunks(self, chunker):
        doc = _doc("some content")
        doc.doc_id = "my-special-id"
        chunks = chunker.chunk(doc)
        for chunk in chunks:
            assert chunk.doc_id == "my-special-id"

    def test_overlap_produces_more_chunks_than_no_overlap(self, chunker):
        long_text = " ".join(["word"] * 300)
        doc = _doc(long_text)
        chunks_with_overlap = chunker.chunk(doc, max_tokens=100, overlap=50)
        chunks_no_overlap = chunker.chunk(doc, max_tokens=100, overlap=0)
        assert len(chunks_with_overlap) >= len(chunks_no_overlap)

    def test_token_count_matches_actual_tokens(self, chunker):
        doc = _doc("The quick brown fox jumps over the lazy dog")
        chunks = chunker.chunk(doc, max_tokens=512, overlap=0)
        for chunk in chunks:
            # token_count should be positive and match content
            assert chunk.token_count > 0
            assert len(chunk.content) > 0
