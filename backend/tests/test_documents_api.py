"""
Tests for documents API — Property 2: 文档列表字段完整性.
Feature: qa-copilot, Property 2: 文档列表字段完整性
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(override_auth):
    return TestClient(app)


def _make_doc(doc_id: str = "doc-1", filename: str = "test.pdf", status: str = "ready"):
    doc = MagicMock()
    doc.id = doc_id
    doc.filename = filename
    doc.file_type = "pdf"
    doc.file_size = 1024
    doc.status = status
    doc.uploaded_at = datetime(2024, 1, 15, 10, 30, 0)
    return doc


# ---------------------------------------------------------------------------
# Property 2: 文档列表字段完整性
# Validates: Requirements 1.6
# ---------------------------------------------------------------------------

def test_document_list_contains_required_fields(client):
    """GET /api/documents must return filename, uploadedAt, status for each doc."""
    mock_doc = _make_doc()
    with patch("app.api.documents.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.query.return_value.all.return_value = [mock_doc]

        response = client.get("/api/documents/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        doc = data[0]
        assert "filename" in doc
        assert "uploaded_at" in doc
        assert "status" in doc
        assert "id" in doc
        assert "file_type" in doc
        assert "file_size" in doc


def test_document_list_field_values_match_stored_data(client):
    """Field values in the response must match the stored metadata."""
    mock_doc = _make_doc(doc_id="abc-123", filename="report.pdf", status="ready")
    with patch("app.api.documents.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.query.return_value.all.return_value = [mock_doc]

        response = client.get("/api/documents/")
        doc = response.json()[0]

        assert doc["id"] == "abc-123"
        assert doc["filename"] == "report.pdf"
        assert doc["status"] == "ready"
        assert doc["uploaded_at"] == "2024-01-15T10:30:00"


def test_document_list_empty_when_no_documents(client):
    """GET /api/documents returns empty list when no documents exist."""
    with patch("app.api.documents.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.query.return_value.all.return_value = []

        response = client.get("/api/documents/")
        assert response.status_code == 200
        assert response.json() == []


def test_document_list_multiple_docs_all_have_required_fields(client):
    """All documents in the list must have required fields."""
    docs = [_make_doc(f"doc-{i}", f"file{i}.pdf", "ready") for i in range(5)]
    with patch("app.api.documents.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.query.return_value.all.return_value = docs

        response = client.get("/api/documents/")
        data = response.json()
        assert len(data) == 5
        for doc in data:
            assert "filename" in doc
            assert "uploaded_at" in doc
            assert "status" in doc


def test_upload_rejects_unsupported_format(client):
    """POST /api/documents/upload rejects unsupported file formats with 400."""
    with patch("app.api.documents._uploader") as mock_uploader:
        mock_uploader.validate_file.side_effect = ValueError("Unsupported file format")
        response = client.post(
            "/api/documents/upload",
            files={"file": ("malware.exe", b"content", "application/octet-stream")},
        )
        assert response.status_code == 400


def test_get_document_status_returns_correct_fields(client):
    """GET /api/documents/{id}/status returns id, status, error_msg."""
    mock_doc = _make_doc()
    mock_doc.error_msg = None
    with patch("app.api.documents.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = mock_doc

        response = client.get("/api/documents/doc-1/status")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert "error_msg" in data


def test_get_document_status_404_for_missing_doc(client):
    """GET /api/documents/{id}/status returns 404 for non-existent document."""
    with patch("app.api.documents.SessionLocal") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = None

        response = client.get("/api/documents/nonexistent/status")
        assert response.status_code == 404


def test_download_document_returns_file_when_resolved(client, tmp_path):
    mock_doc = _make_doc(doc_id="doc-1", filename="name-in-db.md")
    resolved_file = tmp_path / "real-name.md"
    resolved_file.write_text("body", encoding="utf-8")

    with patch("app.api.documents.SessionLocal") as mock_db_cls, \
         patch("app.api.documents._resolve_document_file_path", return_value=resolved_file):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = mock_doc
        response = client.get("/api/documents/doc-1/download")

    assert response.status_code == 200
    assert "attachment; filename=\"real-name.md\"" in response.headers.get("content-disposition", "")


def test_download_document_404_when_file_not_resolved(client):
    mock_doc = _make_doc(doc_id="doc-1", filename="missing.md")
    with patch("app.api.documents.SessionLocal") as mock_db_cls, \
         patch("app.api.documents._resolve_document_file_path", return_value=None):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = mock_doc
        response = client.get("/api/documents/doc-1/download")

    assert response.status_code == 404


def test_download_document_uses_filename_query_when_doc_missing(client, tmp_path):
    resolved_file = tmp_path / "fallback.md"
    resolved_file.write_text("body", encoding="utf-8")
    with patch("app.api.documents.SessionLocal") as mock_db_cls, \
         patch("app.api.documents._resolve_document_file_path", return_value=resolved_file) as mock_resolve:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get.return_value = None
        response = client.get("/api/documents/old-doc-id/download?filename=fallback.md")

    assert response.status_code == 200
    mock_resolve.assert_called_once_with("old-doc-id", "fallback.md")
