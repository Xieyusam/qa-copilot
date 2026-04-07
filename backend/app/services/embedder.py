"""
Embedder module — wraps LangChain embedding models.
Supports sentence-transformers (local) and OpenAI-compatible backends.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from app.config import settings


def _build_embeddings() -> Embeddings:
    """Instantiate the configured LangChain Embeddings object (lazy, called once)."""
    backend = settings.embedding_backend.lower()
    
    api_key = settings.embedding_api_key or settings.llm_api_key
    api_url = settings.embedding_api_url or settings.llm_api_url
    
    if backend == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=api_key,
            base_url=api_url,
        )
    elif backend == "hunyuan":
        from langchain_openai import OpenAIEmbeddings
        # 腾讯混元等模型不支持 OpenAI 的 `encoding_format` 和某些额外参数，
        # 并且要求 input 为字符串或数组，因此需要通过 check_embedding_ctx_length 和其他参数做妥协
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=api_key,
            base_url=api_url,
            check_embedding_ctx_length=False,  # 关闭本地的 token 长度检查，防止使用 tiktoken 时报错
            tiktoken_enabled=False,            # 混元不是基于 tiktoken 的，必须关闭
        )
    elif backend == "sentence-transformers":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=settings.embedding_model)
    else:
        raise ValueError(
            f"Unsupported embedding_backend: '{settings.embedding_backend}'. "
            "Choose 'openai' or 'sentence-transformers'."
        )


class Embedder:
    """Thin wrapper around a LangChain Embeddings model."""

    # Use a class-level variable to store the singleton instance
    _instance: Embeddings | None = None

    def __init__(self) -> None:
        pass

    @property
    def _model(self) -> Embeddings:
        if Embedder._instance is None:
            Embedder._instance = _build_embeddings()
        return Embedder._instance

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for *texts* (empty list → empty list)."""
        if not texts:
            return []
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Return a single query embedding (used by Retriever)."""
        return self._model.embed_query(text)
