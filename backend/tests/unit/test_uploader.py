"""
Tests for DocumentUploader — Property 1, Property 3, unit tests.
Feature: internal-knowledge-base
  Property 1: 文件格式校验完备性
  Property 3: 删除一致性
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.document.uploader import DocumentUploader, SUPPORTED_EXTENSIONS


@pytest.fixture
def uploader() -> DocumentUploader:
    """Uploader with mocked dependencies."""
    parser = MagicMock()
    chunker = MagicMock()
    embedder = MagicMock()
    vector_store = MagicMock()
    return DocumentUploader(
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
    )


# ---------------------------------------------------------------------------
# Property 1: 文件格式校验完备性
# Validates: Requirements 1.2, 1.3
# ---------------------------------------------------------------------------

SUPPORTED = {"pdf", "docx", "txt", "md", "xlsx", "xls"}

# Feature: internal-knowledge-base, Property 1: 文件格式校验完备性
@given(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll", "Lu"))))
@settings(max_examples=100)
def test_format_validation_accepts_only_supported(ext: str):
    """validate_file accepts iff extension is in SUPPORTED_EXTENSIONS."""
    uploader = DocumentUploader.__new__(DocumentUploader)
    filename = f"file.{ext.lower()}"
    if ext.lower() in SUPPORTED:
        # Should not raise
        try:
            uploader.validate_file(filename, 100)
        except ValueError as e:
            if "format" in str(e).lower():
                pytest.fail(f"Supported extension '{ext}' was rejected: {e}")
    else:
        with pytest.raises(ValueError) as exc_info:
            uploader.validate_file(filename, 100)
        # Error message must mention supported formats
        assert any(fmt in str(exc_info.value) for fmt in SUPPORTED)


def test_validate_accepts_pdf(uploader):
    uploader.validate_file("doc.pdf", 1024)  # no exception


def test_validate_accepts_docx(uploader):
    uploader.validate_file("doc.docx", 1024)


def test_validate_accepts_txt(uploader):
    uploader.validate_file("doc.txt", 1024)


def test_validate_accepts_md(uploader):
    uploader.validate_file("doc.md", 1024)


def test_validate_accepts_xlsx(uploader):
    uploader.validate_file("doc.xlsx", 1024)


def test_validate_rejects_exe(uploader):
    with pytest.raises(ValueError, match="Unsupported"):
        uploader.validate_file("malware.exe", 1024)


def test_validate_rejects_zip(uploader):
    with pytest.raises(ValueError):
        uploader.validate_file("archive.zip", 1024)


def test_validate_error_message_lists_supported_formats(uploader):
    with pytest.raises(ValueError) as exc_info:
        uploader.validate_file("file.xyz", 100)
    msg = str(exc_info.value)
    for fmt in SUPPORTED:
        assert fmt in msg


# ---------------------------------------------------------------------------
# Unit test: 100MB size limit (Requirement 1.4)
# ---------------------------------------------------------------------------

def test_validate_rejects_file_over_100mb(uploader):
    """Files larger than 100MB must be rejected."""
    over_limit = 101 * 1024 * 1024  # 101 MB
    with pytest.raises(ValueError, match="exceeds"):
        uploader.validate_file("big.pdf", over_limit)


def test_validate_accepts_file_exactly_100mb(uploader):
    """Files exactly at 100MB should be accepted."""
    exactly_100mb = 100 * 1024 * 1024
    uploader.validate_file("big.pdf", exactly_100mb)  # no exception


def test_validate_accepts_file_just_under_100mb(uploader):
    just_under = 100 * 1024 * 1024 - 1
    uploader.validate_file("file.pdf", just_under)  # no exception


def test_validate_rejects_file_one_byte_over_100mb(uploader):
    one_over = 100 * 1024 * 1024 + 1
    with pytest.raises(ValueError):
        uploader.validate_file("file.pdf", one_over)


# ---------------------------------------------------------------------------
# Property 3: 删除一致性
# Validates: Requirements 1.7, 2.6
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_removes_vector_data():
    """delete_document must call vector_store.delete_by_doc_id."""
    vector_store = MagicMock()
    uploader = DocumentUploader(
        parser=MagicMock(),
        chunker=MagicMock(),
        embedder=MagicMock(),
        vector_store=vector_store,
    )
    doc_id = "test-doc-123"
    # Patch DB and file system operations
    with patch("app.services.document.uploader.SessionLocal") as mock_db_cls, \
         patch("app.services.document.uploader.shutil") as mock_shutil, \
         patch("app.services.document.uploader.Path") as mock_path:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.get.return_value = None

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        await uploader.delete_document(doc_id)

    vector_store.delete_by_doc_id.assert_called_once_with(doc_id)


@pytest.mark.asyncio
async def test_delete_removes_file_from_disk(tmp_path):
    """delete_document must remove the file directory from disk."""
    vector_store = MagicMock()
    uploader = DocumentUploader(
        parser=MagicMock(),
        chunker=MagicMock(),
        embedder=MagicMock(),
        vector_store=vector_store,
    )
    doc_id = "doc-to-delete"
    doc_dir = tmp_path / doc_id
    doc_dir.mkdir()
    (doc_dir / "file.txt").write_text("content")

    with patch("app.services.document.uploader.settings") as mock_settings, \
         patch("app.services.document.uploader.SessionLocal") as mock_db_cls:
        mock_settings.file_storage_path = str(tmp_path)
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = None

        await uploader.delete_document(doc_id)

    assert not doc_dir.exists()
