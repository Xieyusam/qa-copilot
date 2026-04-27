"""
DocumentUploader service for the internal knowledge base system.
Handles file validation, storage, async processing, and deletion.
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiofiles

from app.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.chunking_config import KbChunkingConfig
from app.services.document.chunker import Chunker
from app.services.document.cleaner import DocumentCleaner
from app.services.document.chunking_config import ChunkingConfigService
from app.services.retrieval.embedder import Embedder
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.observability.logger import get_logger
from app.services.document.parser import DocumentParser
from app.services.retrieval.vector_store import VectorStore

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "md", "xlsx", "xls"}


class DocumentUploader:
    """Handles document upload, processing, and deletion."""

    def __init__(
        self,
        parser: DocumentParser | None = None,
        chunker: Chunker | None = None,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        hybrid_retriever: HybridRetriever | None = None,
    ) -> None:
        self._parser = parser or DocumentParser()
        self._chunker = chunker or Chunker()
        self._embedder = embedder or Embedder()
        self._vector_store = vector_store or VectorStore()
        # Note: In a real system, the HybridRetriever should be a singleton or its BM25 
        # index should be persisted. For this MVP, we inject it or use a default one.
        self._hybrid_retriever = hybrid_retriever or HybridRetriever(
            embedder=self._embedder, vector_store=self._vector_store
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _get_dest_dir(self, doc_id: str) -> Path:
        """Get the destination directory for a document."""
        return Path(settings.file_storage_path) / doc_id

    def validate_file(self, filename: str, file_size: int) -> None:
        """
        Validate file extension and size.

        Raises:
            ValueError: If the extension is not supported or the file exceeds the size limit.
        """
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported formats: {supported}"
            )

        max_bytes = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(
                f"File size {file_size} bytes exceeds the maximum allowed size "
                f"of {settings.max_file_size_mb} MB ({max_bytes} bytes)."
            )

    async def save_upload(self, file_content: bytes, filename: str, kb_category: str = "default") -> Document:
        """
        Persist the raw file to disk and create a Document record in SQLite.

        Returns:
            The newly created Document ORM object (status='pending').
        """
        doc_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lstrip(".").lower()

        # Save file to disk asynchronously
        dest_dir = Path(settings.file_storage_path) / doc_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(file_content)

        # Create Document record in SQLite
        db = SessionLocal()
        try:
            doc = Document(
                id=doc_id,
                filename=filename,
                file_type=ext,
                file_size=len(file_content),
                status="pending",
                uploaded_at=datetime.now(timezone.utc),
                kb_category_id=kb_category,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc
        finally:
            db.close()

    async def process_document(self, doc_id: str, chunking_strategy: str | None = None) -> None:
        """
        Asynchronously parse, chunk, embed, and index a document.

        Args:
            doc_id: 文档 ID
            chunking_strategy: 覆盖默认配置的切分策略（可选）

        Updates document status through: processing → ready (or failed on error).
        """
        db = SessionLocal()
        try:
            doc = db.get(Document, doc_id)
            if doc is None:
                logger.error("process_document: document %s not found", doc_id)
                return

            # Mark as processing
            doc.status = "processing"
            db.commit()

            # Locate the file
            dest_dir = Path(settings.file_storage_path) / doc_id
            file_path = str(dest_dir / doc.filename)

            # Verify file exists before processing
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Document file not found: {file_path}")

            try:
                # Parse
                parsed = self._parser.parse(file_path, doc.file_type, doc_id=doc_id)

                # Clean
                cleaner = DocumentCleaner()
                cleaned_content = cleaner.clean(parsed.content)
                parsed.content = cleaned_content

                # Get chunking config（优先使用传入的 strategy，否则查分类配置）
                if chunking_strategy:
                    config = KbChunkingConfig(
                        id="",
                        category_id=doc.kb_category_id,
                        chunking_strategy=chunking_strategy,
                        max_tokens=512,
                        overlap=50,
                        strategy_overrides=None,
                    )
                else:
                    config_service = ChunkingConfigService()
                    config = config_service.get_config(doc.kb_category_id)

                # Chunk with config-driven strategy
                chunks = self._chunker.chunk_with_config(parsed, config)
                for chunk in chunks:
                    chunk.kb_category = doc.kb_category_rel.name if doc.kb_category_rel else doc.kb_category_id
                    chunk.kb_category_id = doc.kb_category_id

                # Embed
                texts = [c.content for c in chunks]
                embeddings = self._embedder.embed(texts) if texts else []

                # Store in vector store and BM25
                if chunks:
                    self._vector_store.add_chunks(chunks, embeddings, doc.filename)
                    self._hybrid_retriever.add_chunks_to_bm25(chunks, doc.filename)

                # Mark as ready
                doc.status = "ready"
                doc.processed_at = datetime.now(timezone.utc)
                doc.error_msg = None
                db.commit()

            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to process document %s: %s", doc_id, exc)
                db.refresh(doc)
                doc.status = "failed"
                doc.error_msg = str(exc)
                db.commit()
                raise  # Re-raise so caller knows processing failed

        finally:
            db.close()

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a document's raw files, vector data, and metadata record.
        """
        # Remove raw files from disk
        dest_dir = Path(settings.file_storage_path) / doc_id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        # Remove vectors from ChromaDB
        self._vector_store.delete_by_doc_id(doc_id)
        
        # Remove from BM25
        self._hybrid_retriever.remove_doc_from_bm25(doc_id)

        # Remove metadata from SQLite
        db = SessionLocal()
        try:
            doc = db.get(Document, doc_id)
            if doc is not None:
                db.delete(doc)
                db.commit()
        finally:
            db.close()
