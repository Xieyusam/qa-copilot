"""
Tests for embedder service.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.retrieval.embedder import Embedder


@pytest.fixture(autouse=True)
def reset_embedder_singleton():
    """Reset Embedder singleton before each test."""
    Embedder._instance = None
    yield
    Embedder._instance = None


class TestEmbedderEmbed:
    """Test Embedder.embed() method."""

    def test_embed_empty_list_returns_empty_list(self):
        """Empty texts list should return empty list."""
        mock_model = MagicMock()
        Embedder._instance = mock_model
        embedder = Embedder()
        result = embedder.embed([])
        assert result == []
        mock_model.embed_documents.assert_not_called()

    def test_embed_calls_underlying_model(self):
        """Non-empty texts should call embed_documents."""
        mock_model = MagicMock()
        mock_model.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        Embedder._instance = mock_model
        embedder = Embedder()
        result = embedder.embed(["hello", "world"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_model.embed_documents.assert_called_once_with(["hello", "world"])

    def test_embed_returns_list_of_lists(self):
        """embed() should return list of embedding vectors."""
        mock_model = MagicMock()
        expected = [[0.1] * 10, [0.2] * 10]
        mock_model.embed_documents.return_value = expected
        Embedder._instance = mock_model
        embedder = Embedder()
        result = embedder.embed(["text1", "text2"])
        assert len(result) == 2
        assert isinstance(result[0], list)


class TestEmbedderBuild:
    """Test Embedder._build_embeddings() with different backends."""

    def test_build_unsupported_backend_raises(self):
        """Unsupported embedding_backend raises ValueError."""
        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.embedding_backend = "unsupported_backend"
            mock_settings.embedding_api_key = None
            mock_settings.embedding_api_url = None
            mock_settings.llm_api_key = None
            mock_settings.llm_api_url = None
            mock_settings.embedding_model = "test"
            with pytest.raises(ValueError, match="Unsupported embedding_backend"):
                from app.services.retrieval.embedder import _build_embeddings
                _build_embeddings()


class TestEmbedderEmbedQuery:
    """Test Embedder.embed_query() method."""

    def test_embed_query_calls_underlying_model(self):
        """embed_query should call embed_query on the model."""
        mock_model = MagicMock()
        mock_model.embed_query.return_value = [0.1, 0.2, 0.3]
        Embedder._instance = mock_model
        embedder = Embedder()
        result = embedder.embed_query("What is AI?")
        assert result == [0.1, 0.2, 0.3]
        mock_model.embed_query.assert_called_once_with("What is AI?")

    def test_embed_query_returns_single_vector(self):
        """embed_query should return a single embedding vector."""
        mock_model = MagicMock()
        expected = [0.5] * 20
        mock_model.embed_query.return_value = expected
        Embedder._instance = mock_model
        embedder = Embedder()
        result = embedder.embed_query("test query")
        assert isinstance(result, list)
        assert len(result) == 20
