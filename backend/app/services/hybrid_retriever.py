"""
Hybrid Retriever module — fuses VectorStore and BM25 search results with Reranking.
"""
from __future__ import annotations

import logging
from typing import Optional

from rank_bm25 import BM25Okapi

from app.core.schemas import Chunk
from app.services.embedder import Embedder
from app.services.vector_store import ChunkResult, VectorStore

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Retrieves and fuses document chunks using Vector and BM25 methods."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        similarity_threshold: float = 0.2,
    ) -> None:
        self._embedder = embedder or Embedder()
        self._vector_store = vector_store or VectorStore(embedder=self._embedder)
        self._similarity_threshold = similarity_threshold
        
        # In-memory BM25 index (in a real system, persist this or use a search engine like Elasticsearch)
        self._bm25_corpus: list[ChunkResult] = []
        self._bm25_index: Optional[BM25Okapi] = None
        self._tokenized_corpus: list[list[str]] = []

    def add_chunks_to_bm25(self, chunks: list[Chunk], filename: str) -> None:
        """Add new chunks to the in-memory BM25 index."""
        for chunk in chunks:
            chunk_result = ChunkResult(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                filename=filename,
                content=chunk.content,
                position=chunk.position,
                score=0.0,  # Default for BM25
                kb_category=chunk.kb_category,
                kb_category_id=chunk.kb_category_id,
            )
            self._bm25_corpus.append(chunk_result)
            # Simple tokenization by whitespace (in production, use jieba for Chinese)
            tokenized_doc = chunk.content.lower().split()
            self._tokenized_corpus.append(tokenized_doc)
            
        if self._tokenized_corpus:
            self._bm25_index = BM25Okapi(self._tokenized_corpus)

    def remove_doc_from_bm25(self, doc_id: str) -> None:
        """Remove a document's chunks from the BM25 index."""
        indices_to_remove = [
            i for i, c in enumerate(self._bm25_corpus) if c.doc_id == doc_id
        ]
        if not indices_to_remove:
            return
            
        for i in reversed(indices_to_remove):
            self._bm25_corpus.pop(i)
            self._tokenized_corpus.pop(i)
            
        if self._tokenized_corpus:
            self._bm25_index = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25_index = None

    async def retrieve(self, query: str, top_k: int = 5, filter: dict[str, str] | None = None) -> list[ChunkResult]:
        """Retrieve top-K chunks using hybrid search and RRF (Reciprocal Rank Fusion)."""
        # 支持 kb_category_id 和 kb_category 两种过滤方式
        kb_category_id = filter.get("kb_category_id") if filter else None
        kb_category = filter.get("kb_category") if filter else None

        vector_results = self._retrieve_vector(query, top_k=top_k * 2, kb_category=kb_category, kb_category_id=kb_category_id)
        bm25_results = self._retrieve_bm25(query, top_k=top_k * 2, kb_category=kb_category, kb_category_id=kb_category_id)
        
        # Merge and deduplicate by chunk_id using RRF
        merged_results: dict[str, ChunkResult] = {}
        rrf_scores: dict[str, float] = {}
        
        # RRF constant k, typically set to 60
        rrf_k = 60
        
        # Process vector results
        for rank, res in enumerate(vector_results):
            merged_results[res.chunk_id] = res
            rrf_scores[res.chunk_id] = 1.0 / (rrf_k + rank + 1)
            
        # Process BM25 results
        for rank, res in enumerate(bm25_results):
            if res.chunk_id not in merged_results:
                merged_results[res.chunk_id] = res
                rrf_scores[res.chunk_id] = 0.0
            rrf_scores[res.chunk_id] += 1.0 / (rrf_k + rank + 1)
                
        # Assign RRF scores for ranking, but keep the original vector score for display
        # We will sort by RRF score, but the chunk.score will reflect the absolute similarity.
        unique_results = list(merged_results.values())
        
        if not unique_results:
            return []
            
        # Filter by threshold (using absolute vector score if available)
        filtered_results = [r for r in unique_results if r.score >= self._similarity_threshold]
        
        # Sort by RRF score descending
        sorted_results = sorted(filtered_results, key=lambda x: rrf_scores.get(x.chunk_id, 0), reverse=True)
        
        return sorted_results[:top_k]

    def _retrieve_vector(self, query: str, top_k: int, kb_category: str | None = None, kb_category_id: str | None = None) -> list[ChunkResult]:
        if self._vector_store.count() == 0:
            return []
        query_embedding = self._embedder.embed_query(query)
        return self._vector_store.query(query_embedding, top_k, kb_category=kb_category, kb_category_id=kb_category_id)

    def _retrieve_bm25(self, query: str, top_k: int, kb_category: str | None = None, kb_category_id: str | None = None) -> list[ChunkResult]:
        if not self._bm25_index or not self._bm25_corpus:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)

        # Get top-k indices, optionally filtering by kb_category or kb_category_id
        scored_indices = [
            i for i, s in enumerate(scores)
            if s > 0 and (
                (kb_category_id is None or self._bm25_corpus[i].kb_category_id == kb_category_id) and
                (kb_category is None or self._bm25_corpus[i].kb_category == kb_category)
            )
        ]
        top_indices = sorted(scored_indices, key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for i in top_indices:
            if scores[i] > 0:
                chunk = self._bm25_corpus[i]
                # Create a copy with the BM25 score
                results.append(ChunkResult(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    filename=chunk.filename,
                    content=chunk.content,
                    position=chunk.position,
                    score=scores[i],
                    kb_category=chunk.kb_category,
                    kb_category_id=chunk.kb_category_id,
                ))
        return results