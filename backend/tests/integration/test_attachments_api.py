"""
Tests for Attachments API.
Feature: qa-copilot - Chat Multimodal Attachment Intermediary Pattern
"""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(override_auth):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def attachments_dir(tmp_path):
    """Create a temp attachments directory."""
    d = tmp_path / "attachments"
    d.mkdir()
    return d


@pytest.fixture
def mock_attachments_dir(monkeypatch, attachments_dir):
    """Mock the attachments directory to a temp path."""
    monkeypatch.setattr("app.config.settings.attachments_dir", str(attachments_dir))
    return attachments_dir


class TestUploadAttachment:
    def test_upload_single_file(self, client, mock_attachments_dir):
        """POST /api/attachments uploads a file and returns id, filename, size."""
        files = {"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
        resp = client.post("/api/attachments", files=files)

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["filename"] == "test.txt"
        assert data["size"] == 11

    def test_upload_creates_file_on_disk(self, client, mock_attachments_dir):
        """Uploaded file should be saved to attachments_dir."""
        files = {"file": ("doc.pdf", io.BytesIO(b"pdf content"), "application/pdf")}
        resp = client.post("/api/attachments", files=files)

        assert resp.status_code == 200
        att_id = resp.json()["id"]
        # File saved as {uuid}_{original_filename}
        saved_path = mock_attachments_dir / f"{att_id}_doc.pdf"
        assert saved_path.exists()

    def test_upload_missing_file(self, client):
        """POST with no file should return 422."""
        resp = client.post("/api/attachments")
        assert resp.status_code == 422

    def test_upload_file_too_large(self, client, mock_attachments_dir, monkeypatch):
        """Files exceeding max_attachment_size should be rejected."""
        monkeypatch.setattr("app.config.settings.max_attachment_size", 10)  # 10 bytes
        files = {"file": ("large.txt", io.BytesIO(b"x" * 20), "text/plain")}
        resp = client.post("/api/attachments", files=files)

        assert resp.status_code == 400
        assert "too large" in resp.json().get("detail", "").lower()


class TestGetAttachment:
    def test_get_attachment_metadata(self, client, mock_attachments_dir):
        """GET /api/attachments/{id} returns id, filename, size."""
        # Upload first
        files = {"file": ("meta.txt", io.BytesIO(b"metadata test"), "text/plain")}
        up_resp = client.post("/api/attachments", files=files)
        att_id = up_resp.json()["id"]

        # Get metadata
        resp = client.get(f"/api/attachments/{att_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == att_id
        assert data["filename"] == "meta.txt"
        assert data["size"] == 13

    def test_get_nonexistent_attachment(self, client):
        """GET /api/attachments/{nonexistent} returns 404."""
        resp = client.get("/api/attachments/nonexistent-id-12345")
        assert resp.status_code == 404


class TestDownloadAttachment:
    def test_download_attachment_content(self, client, mock_attachments_dir):
        """GET /api/attachments/{id}/download returns file content."""
        content = b"download test content"
        files = {"file": ("download.txt", io.BytesIO(content), "text/plain")}
        up_resp = client.post("/api/attachments", files=files)
        att_id = up_resp.json()["id"]

        resp = client.get(f"/api/attachments/{att_id}/download")
        assert resp.status_code == 200
        assert resp.content == content

    def test_download_nonexistent_returns_404(self, client):
        """GET /api/attachments/{id}/download for nonexistent returns 404."""
        resp = client.get("/api/attachments/nonexistent-id-99999/download")
        assert resp.status_code == 404


class TestDeleteAttachment:
    def test_delete_attachment(self, client, mock_attachments_dir):
        """DELETE /api/attachments/{id} removes file from disk."""
        files = {"file": ("delete.txt", io.BytesIO(b"delete me"), "text/plain")}
        up_resp = client.post("/api/attachments", files=files)
        att_id = up_resp.json()["id"]

        # Verify exists
        saved_path = mock_attachments_dir / f"{att_id}_delete.txt"
        assert saved_path.exists()

        # Delete
        del_resp = client.delete(f"/api/attachments/{att_id}")
        assert del_resp.status_code == 200

        # Verify gone
        assert not saved_path.exists()

    def test_delete_nonexistent_returns_404(self, client):
        """DELETE /api/attachments/{id} for nonexistent returns 404."""
        resp = client.delete("/api/attachments/nonexistent-delete-id")
        assert resp.status_code == 404
