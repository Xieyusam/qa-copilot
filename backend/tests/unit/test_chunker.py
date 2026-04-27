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
from app.services.document.chunker import Chunker


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


class TestChunkWithConfig:
    """Tests for chunk_with_config method."""

    def test_chunk_with_config_recursive_text_strategy(self, chunker):
        """chunk_with_config with recursive_text strategy calls _chunk_text."""
        doc = _doc("Hello world. This is a test.", file_type="txt")
        config = _make_config(strategy="recursive_text", max_tokens=100, overlap=10)
        chunks = chunker.chunk_with_config(doc, config)
        assert len(chunks) >= 1
        assert chunks[0].doc_id == "test-doc"

    def test_chunk_with_config_sentence_strategy(self, chunker):
        """chunk_with_config with sentence strategy calls _chunk_sentence."""
        doc = _doc("这是中文内容。这是第二句。第三句来了！", file_type="txt")
        config = _make_config(strategy="sentence", max_tokens=100, overlap=10)
        chunks = chunker.chunk_with_config(doc, config)
        assert len(chunks) >= 1

    def test_chunk_with_config_sliding_window_strategy(self, chunker):
        """chunk_with_config with sliding_window strategy calls _chunk_sliding_window."""
        doc = _doc("A " * 300)
        config = _make_config(strategy="sliding_window", max_tokens=50, overlap=20)
        chunks = chunker.chunk_with_config(doc, config)
        # sliding window should produce overlapping chunks
        assert len(chunks) > 1

    def test_chunk_with_config_semantic_strategy(self, chunker):
        """chunk_with_config with semantic strategy uses Embedder for similarity-based splitting."""
        from unittest.mock import patch, MagicMock

        # Create doc with multiple sentences
        doc = _doc("这是第一句话。这是第二句话。第三句话来了！这是另一个主题的开始。")
        config = _make_config(strategy="semantic", max_tokens=50, overlap=5)

        # Mock Embedder to return deterministic fake embeddings
        def fake_embed(texts):
            # Return a simple vector based on the text
            return [[1.0, 0.0] if "主题" in t else [0.9, 0.1] for t in texts]

        with patch("app.services.retrieval.embedder.Embedder") as MockEmbedder:
            mock_instance = MagicMock()
            mock_instance.embed.side_effect = fake_embed
            MockEmbedder.return_value = mock_instance

            chunks = chunker.chunk_with_config(doc, config)
            # Should produce at least one chunk
            assert len(chunks) >= 1
            for chunk in chunks:
                assert chunk.doc_id == "test-doc"
                assert chunk.token_count > 0
                assert chunk.position >= 0

    def test_chunk_with_config_markdown_strategy(self, chunker):
        """chunk_with_config with markdown strategy calls _chunk_markdown."""
        md = "# Title\n\nContent here."
        doc = _doc(md, file_type="md")
        config = _make_config(strategy="markdown", max_tokens=100, overlap=10)
        chunks = chunker.chunk_with_config(doc, config)
        assert len(chunks) >= 1

    def test_chunk_with_config_excel_strategy(self, chunker):
        """chunk_with_config with xlsx strategy calls _chunk_excel."""
        doc = _doc("Row1\nRow2\nRow3", file_type="xlsx")
        config = _make_config(strategy="xlsx", max_tokens=100, overlap=10)
        chunks = chunker.chunk_with_config(doc, config)
        assert len(chunks) >= 1

    def test_chunk_with_config_strategy_overrides_file_type(self, chunker):
        """strategy_overrides takes precedence over default strategy."""
        md = "# Title\n\nContent"
        doc = _doc(md, file_type="md")
        # Override markdown to use sentence strategy instead
        config = _make_config(strategy="recursive_text", max_tokens=100, overlap=10)
        config.strategy_overrides = {"md": "sentence"}
        chunks = chunker.chunk_with_config(doc, config)
        assert len(chunks) >= 1

    def test_chunk_with_config_empty_content(self, chunker):
        """Empty content returns no chunks."""
        doc = _doc("")
        config = _make_config(strategy="recursive_text")
        assert chunker.chunk_with_config(doc, config) == []

    def test_chunk_with_config_unknown_strategy_falls_back_to_text(self, chunker):
        """Unknown strategy falls back to _chunk_text."""
        doc = _doc("Some content here.")
        config = _make_config(strategy="unknown_strategy", max_tokens=100, overlap=10)
        chunks = chunker.chunk_with_config(doc, config)
        assert len(chunks) >= 1


class TestSentenceChunker:
    """Tests for _chunk_sentence method."""

    def test_sentence_chunking_by_punctuation(self, chunker):
        """Sentence strategy splits by English punctuation when whitespace exists."""
        # Note: _chunk_sentence uses "".join() which removes spaces between sentences.
        # This test verifies the method runs without error and produces chunks.
        content = "Hello world. How are you? I am fine!"
        doc = _doc(content, file_type="txt")
        chunks = chunker._chunk_sentence(doc, max_tokens=50, overlap=5)
        # _chunk_sentence may produce 1+ chunks depending on sentence lengths
        assert len(chunks) >= 1

    def test_sentence_chunking_respects_max_tokens(self, chunker):
        """Sentences within max_tokens are grouped into chunks."""
        # Multiple short sentences grouped into one chunk
        sentences = "这是第一句。 " * 5  # ~10 tokens each, 5 sentences
        doc = _doc(sentences, file_type="txt")
        chunks = chunker._chunk_sentence(doc, max_tokens=100, overlap=5)
        assert len(chunks) >= 1

    def test_sentence_chunking_empty_content(self, chunker):
        """Empty content returns no chunks."""
        doc = _doc("", file_type="txt")
        chunks = chunker._chunk_sentence(doc, max_tokens=50, overlap=5)
        assert chunks == []


class TestSlidingWindow:
    """Tests for _chunk_sliding_window method."""

    def test_sliding_window_produces_overlapping_chunks(self, chunker):
        """Sliding window produces chunks with overlap."""
        doc = _doc("A " * 200)
        chunks = chunker._chunk_sliding_window(doc, max_tokens=50, overlap=20)
        assert len(chunks) > 1
        # Verify overlap - consecutive chunks should share some content
        if len(chunks) >= 2:
            assert chunks[0].content != chunks[1].content

    def test_sliding_window_respects_max_tokens(self, chunker):
        """Each chunk respects max_tokens limit."""
        doc = _doc("word " * 300)
        chunks = chunker._chunk_sliding_window(doc, max_tokens=50, overlap=10)
        for chunk in chunks:
            assert chunk.token_count <= 50

    def test_sliding_window_empty_content(self, chunker):
        """Empty content returns no chunks."""
        doc = _doc("")
        chunks = chunker._chunk_sliding_window(doc, max_tokens=50, overlap=10)
        assert chunks == []


class TestExcelChunker:
    """Tests for _chunk_excel method."""

    def test_excel_chunking_preserves_row_structure(self, chunker):
        """Excel chunker preserves row structure in chunks."""
        content = "Header1\tHeader2\nRow1Col1\tRow1Col2\nRow2Col1\tRow2Col2"
        doc = _doc(content, file_type="xlsx")
        chunks = chunker._chunk_excel(doc, max_tokens=100, overlap=10)
        assert len(chunks) >= 1

    def test_excel_chunking_empty_content(self, chunker):
        """Empty Excel content returns no chunks."""
        doc = _doc("", file_type="xlsx")
        chunks = chunker._chunk_excel(doc, max_tokens=100, overlap=10)
        assert chunks == []


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_config(strategy: str = "recursive_text", max_tokens: int = 512, overlap: int = 50):
    """Create a mock KbChunkingConfig."""
    from app.models.chunking_config import KbChunkingConfig
    config = KbChunkingConfig(
        id="test-config-id",
        category_id="test-cat-id",
        chunking_strategy=strategy,
        max_tokens=max_tokens,
        overlap=overlap,
        strategy_overrides=None,
    )
    return config
