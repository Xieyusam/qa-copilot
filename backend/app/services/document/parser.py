"""
Document parser module for the internal knowledge base system.
Supports PDF (PyMuPDF), DOCX (python-docx), TXT, and Markdown formats.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.schemas import ParsedDocument
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class DocumentParser:
    """Parses documents of various formats into a unified ParsedDocument representation."""

    def parse(
        self,
        file_path: str,
        file_type: str,
        doc_id: str | None = None,
    ) -> ParsedDocument:
        """
        Parse a document file into a ParsedDocument.

        Args:
            file_path: Absolute or relative path to the file.
            file_type: One of 'pdf', 'docx', 'txt', 'md'.
            doc_id: Optional document ID; a UUID is generated if not provided.

        Returns:
            ParsedDocument with extracted content and paragraphs.
            On empty files, returns a ParsedDocument with empty content/paragraphs.
            On parse errors, returns a ParsedDocument with error info in metadata
            rather than raising an exception.
        """
        resolved_id = doc_id or str(uuid.uuid4())
        filename = Path(file_path).name
        normalized_type = file_type.lower().lstrip(".")

        try:
            if normalized_type == "pdf":
                return self._parse_pdf(file_path, resolved_id, filename, normalized_type)
            elif normalized_type == "docx":
                return self._parse_docx(file_path, resolved_id, filename, normalized_type)
            elif normalized_type in ("txt", "md", "markdown"):
                return self._parse_text(file_path, resolved_id, filename, normalized_type)
            elif normalized_type in ("xlsx", "xls"):
                return self._parse_excel(file_path, resolved_id, filename, normalized_type)
            elif normalized_type == "csv":
                return self._parse_csv(file_path, resolved_id, filename, normalized_type)
            else:
                logger.warning("Unsupported file type: %s", file_type)
                return self._empty_document(
                    resolved_id,
                    filename,
                    normalized_type,
                    error=f"Unsupported file type: {file_type}",
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to parse document %s: %s", file_path, exc)
            return self._empty_document(
                resolved_id,
                filename,
                normalized_type,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_pdf(
        self, file_path: str, doc_id: str, filename: str, file_type: str
    ) -> ParsedDocument:
        import fitz  # PyMuPDF

        paragraphs: list[str] = []
        page_count = 0

        with fitz.open(file_path) as pdf:
            page_count = len(pdf)
            for page in pdf:
                text = page.get_text("text")
                if text:
                    # Split page text into paragraphs by double newline first,
                    # then fall back to single newline.
                    page_paragraphs = self._split_paragraphs(text)
                    paragraphs.extend(page_paragraphs)

        content = "\n\n".join(paragraphs)
        metadata: dict[str, Any] = {
            "page_count": page_count,
            "paragraph_count": len(paragraphs),
        }
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content=content,
            paragraphs=paragraphs,
            metadata=metadata,
            parsed_at=datetime.utcnow(),
        )

    def _parse_docx(
        self, file_path: str, doc_id: str, filename: str, file_type: str
    ) -> ParsedDocument:
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        content = "\n\n".join(paragraphs)
        metadata: dict[str, Any] = {
            "paragraph_count": len(paragraphs),
        }
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content=content,
            paragraphs=paragraphs,
            metadata=metadata,
            parsed_at=datetime.utcnow(),
        )

    def _parse_text(
        self, file_path: str, doc_id: str, filename: str, file_type: str
    ) -> ParsedDocument:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        paragraphs = self._split_paragraphs(text)
        content = "\n\n".join(paragraphs)
        metadata: dict[str, Any] = {
            "paragraph_count": len(paragraphs),
        }
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content=content,
            paragraphs=paragraphs,
            metadata=metadata,
            parsed_at=datetime.utcnow(),
        )

    def _parse_excel(
        self, file_path: str, doc_id: str, filename: str, file_type: str
    ) -> ParsedDocument:
        import pandas as pd
        import math

        paragraphs: list[str] = []
        try:
            # Read all sheets into a dictionary of DataFrames
            sheets = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in sheets.items():
                if df.empty:
                    continue
                
                # Fill NaNs with empty string to avoid "nan" in text
                df = df.fillna("")
                
                # Extract headers
                headers = [str(col) for col in df.columns]
                
                for index, row in df.iterrows():
                    # Skip completely empty rows
                    if all(str(val).strip() == "" for val in row.values):
                        continue
                        
                    # Format as:
                    # [表格: Sheet1]
                    # 列1: 值1
                    # 列2: 值2
                    lines = [f"[表格: {sheet_name}]"]
                    for header, val in zip(headers, row.values):
                        val_str = str(val).strip()
                        if val_str:  # Only include non-empty cells
                            lines.append(f"{header}: {val_str}")
                    
                    if len(lines) > 1: # Has at least one valid cell
                        paragraphs.append("\n".join(lines))
                        
        except Exception as e:
            logger.error(f"Error reading excel file {file_path}: {e}")
            raise e

        content = "\n\n".join(paragraphs)
        metadata: dict[str, Any] = {
            "paragraph_count": len(paragraphs),
        }
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content=content,
            paragraphs=paragraphs,
            metadata=metadata,
            parsed_at=datetime.utcnow(),
        )

    def _parse_csv(
        self, file_path: str, doc_id: str, filename: str, file_type: str
    ) -> ParsedDocument:
        import pandas as pd

        paragraphs: list[str] = []
        try:
            # Read CSV file
            df = pd.read_csv(file_path, dtype=str)
            df = df.fillna("")

            # Get headers
            headers = [str(col) for col in df.columns]

            for index, row in df.iterrows():
                # Skip completely empty rows
                if all(str(val).strip() == "" for val in row.values):
                    continue

                # Format as CSV row with header: value pairs
                lines = ["[CSV 行]"]
                for header, val in zip(headers, row.values):
                    val_str = str(val).strip()
                    if val_str:  # Only include non-empty cells
                        lines.append(f"{header}: {val_str}")

                if len(lines) > 1:  # Has at least one valid cell
                    paragraphs.append("\n".join(lines))

        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            raise e

        content = "\n\n".join(paragraphs)
        metadata: dict[str, Any] = {
            "paragraph_count": len(paragraphs),
        }
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content=content,
            paragraphs=paragraphs,
            metadata=metadata,
            parsed_at=datetime.utcnow(),
        )

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text into non-empty paragraphs, preferring double-newline boundaries."""
        if not text or not text.strip():
            return []
        # Use double-newline split if text contains double newlines
        if "\n\n" in text:
            parts = [p.strip() for p in text.split("\n\n")]
            return [p for p in parts if p]
        # Fall back to single-newline split
        parts = [p.strip() for p in text.split("\n")]
        return [p for p in parts if p]

    @staticmethod
    def _empty_document(
        doc_id: str,
        filename: str,
        file_type: str,
        error: str | None = None,
    ) -> ParsedDocument:
        metadata: dict[str, Any] = {"paragraph_count": 0}
        if error:
            metadata["error"] = error
        return ParsedDocument(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content="",
            paragraphs=[],
            metadata=metadata,
            parsed_at=datetime.utcnow(),
        )
