"""
Attachment upload API for chat multimodal support.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse

from app.config import settings
from app.api.dependencies import get_current_user

router = APIRouter()


def _ensure_attachments_dir() -> Path:
    """Ensure attachments directory exists."""
    path = Path(settings.attachments_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/attachments")
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
) -> dict:
    """
    Upload an attachment file.

    Returns attachment metadata including id, filename, and size.
    """
    # Validate file size
    content = await file.read()
    size = len(content)

    if size > settings.max_attachment_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_attachment_size // (1024*1024)}MB"
        )

    # Generate unique ID and save file
    # Store as {uuid}_{original_filename} to preserve original name
    attachment_id = str(uuid.uuid4())
    original_filename = file.filename or "unknown"
    # Sanitize: replace any path separators and keep only basename
    safe_filename = Path(original_filename).name
    stored_filename = f"{attachment_id}_{safe_filename}"
    filepath = _ensure_attachments_dir() / stored_filename

    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "id": attachment_id,
        "filename": safe_filename,
        "size": size,
    }


@router.get("/attachments/{attachment_id}")
async def get_attachment(
    attachment_id: str,
    current_user: str = Depends(get_current_user),
) -> dict:
    """
    Get attachment metadata by ID.
    """
    attachments_dir = _ensure_attachments_dir()

    # Find file with this ID (pattern: {uuid}_{original_filename})
    for filepath in attachments_dir.glob(f"{attachment_id}_*"):
        original_filename = filepath.name[len(attachment_id)+1:]
        return {
            "id": attachment_id,
            "filename": original_filename,
            "size": filepath.stat().st_size,
        }

    raise HTTPException(status_code=404, detail="Attachment not found")


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    current_user: str = Depends(get_current_user),
) -> FileResponse:
    """
    Download attachment file by ID (internal use).
    """
    attachments_dir = _ensure_attachments_dir()

    # Find file with this ID (pattern: {uuid}_{original_filename})
    for filepath in attachments_dir.glob(f"{attachment_id}_*"):
        original_filename = filepath.name[len(attachment_id)+1:]
        return FileResponse(
            filepath,
            media_type="application/octet-stream",
            filename=original_filename,
        )

    raise HTTPException(status_code=404, detail="Attachment not found")


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    current_user: str = Depends(get_current_user),
) -> dict:
    """
    Delete an attachment by ID.
    """
    attachments_dir = _ensure_attachments_dir()

    # Find and delete file (pattern: {uuid}_{original_filename})
    for filepath in attachments_dir.glob(f"{attachment_id}_*"):
        filepath.unlink()
        return {"message": "Attachment deleted"}

    raise HTTPException(status_code=404, detail="Attachment not found")
