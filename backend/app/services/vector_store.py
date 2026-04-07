"""
VectorStore module — wraps LangChain's Chroma vector store.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument

from app.config import settings
from app.core.schemas import Chunk
from app.services.embedder import Embedder


@dataclass
class ChunkResult:
    """A retrieved chunk with its similarity score."""
    chunk_id: str
    doc_id: str
    filename: str
    content: str
    position: int
    score: float
    kb_category: str = "default"
    kb_category_id: str = "default"  # 新增：分类 ID


class VectorStore:
    """LangChain Chroma-backed vector store for document chunks."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or Embedder()
        self.collection_name = f"documents_{settings.embedding_backend}"
        self._store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self._embedder._model,
            persist_directory=str(settings.chroma_path),
        )

    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        filename: str,
    ) -> None:
        """Store chunks with pre-computed embeddings."""
        if not chunks:
            return

        docs = [
            LCDocument(
                page_content=chunk.content,
                metadata={
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "filename": filename,
                    "position": chunk.position,
                    "kb_category": chunk.kb_category,
                    "kb_category_id": chunk.kb_category_id,  # 新增
                },
            )
            for chunk in chunks
        ]
        ids = [chunk.chunk_id for chunk in chunks]
        self._store.add_documents(documents=docs, embeddings=embeddings, ids=ids)

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        kb_category: str | None = None,
        kb_category_id: str | None = None,
    ) -> list[ChunkResult]:
        """Retrieve top-K chunks by embedding similarity.

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            kb_category: 旧版分类名称过滤（已废弃，保留兼容）
            kb_category_id: 新版分类 ID 过滤
        """
        # 优先使用 kb_category_id，否则使用 kb_category
        filter_value = kb_category_id or kb_category
        filter_dict = {"kb_category_id": filter_value} if filter_value else None

        # Note: Chroma's `similarity_search_by_vector_with_relevance_scores`
        # actually returns the raw L2 squared distance (where lower is better).
        results = self._store.similarity_search_by_vector_with_relevance_scores(
            query_embedding, k=top_k, filter=filter_dict
        )
        chunk_results = [
            ChunkResult(
                chunk_id=doc.metadata["chunk_id"],
                doc_id=doc.metadata["doc_id"],
                filename=doc.metadata["filename"],
                content=doc.page_content,
                position=int(doc.metadata["position"]),
                score=1.0 - (distance / 2.0),
                kb_category=doc.metadata.get("kb_category", "default"),
                kb_category_id=doc.metadata.get("kb_category_id", doc.metadata.get("kb_category", "default")),
            )
            for doc, distance in results
        ]
        # Sort by similarity score descending (higher is better)
        chunk_results.sort(key=lambda r: r.score, reverse=True)
        return chunk_results

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all chunks belonging to a document."""
        self._store.delete(where={"doc_id": doc_id})

    def count(self) -> int:
        """Return total number of stored chunks."""
        return self._store._collection.count()

    def get_chunk_content(self, doc_id: str, position: int, filename: str | None = None) -> str | None:
        """Get chunk text by doc_id/filename and chunk position."""
        def _extract_from_collection(
            collection: object, where_filter: dict[str, str]
        ) -> str | None:
            try:
                payload = collection.get(
                    where=where_filter,
                    include=["documents", "metadatas"],
                )
            except Exception:
                return None

            documents = payload.get("documents") or []
            metadatas = payload.get("metadatas") or []
            for meta, document in zip(metadatas, documents):
                try:
                    if int(meta.get("position", -1)) == int(position):
                        return document
                except (TypeError, ValueError):
                    continue
            return None

        primary = _extract_from_collection(self._store._collection, {"doc_id": doc_id})
        if primary:
            return primary
        if filename:
            primary_by_name = _extract_from_collection(
                self._store._collection, {"filename": filename}
            )
            if primary_by_name:
                return primary_by_name

        try:
            collections = self._store._client.list_collections()
        except Exception:
            return None

        for collection in collections:
            name = collection if isinstance(collection, str) else getattr(collection, "name", "")
            if not name or name == self.collection_name:
                continue
            if not name.startswith("documents_"):
                continue
            try:
                raw_collection = self._store._client.get_collection(name=name)
            except Exception:
                continue
            content = _extract_from_collection(raw_collection, {"doc_id": doc_id})
            if content:
                return content
            if filename:
                content_by_name = _extract_from_collection(
                    raw_collection, {"filename": filename}
                )
                if content_by_name:
                    return content_by_name

        return None

    def get_chunks_by_doc_id(self, doc_id: str) -> list[ChunkResult]:
        """Get all chunks belonging to a document."""
        try:
            payload = self._store._collection.get(
                where={"doc_id": doc_id},
                include=["documents", "metadatas"],
            )
        except Exception:
            return []

        documents = payload.get("documents") or []
        metadatas = payload.get("metadatas") or []

        chunks = []
        for doc, meta in zip(documents, metadatas):
            chunks.append(ChunkResult(
                chunk_id=meta.get("chunk_id", ""),
                doc_id=meta.get("doc_id", ""),
                filename=meta.get("filename", ""),
                content=doc,
                position=int(meta.get("position", 0)),
                score=1.0,
                kb_category=meta.get("kb_category", "default"),
            ))

        # Sort by position
        chunks.sort(key=lambda c: c.position)
        return chunks
