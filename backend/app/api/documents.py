"""
Document management API routes.
Prefix is set in main.py (e.g. /api/documents).
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app.db.session import SessionLocal
from app.models.document import Document
from app.services.uploader import DocumentUploader
from app.api.dependencies import require_admin, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
_uploader: DocumentUploader | None = None


class MoveCategoryRequest(BaseModel):
    """移动文档分类请求。"""
    category_id: str

def get_uploader() -> DocumentUploader:
    global _uploader
    if _uploader is None:
        _uploader = DocumentUploader()
    return _uploader


def _resolve_document_file_path(doc_id: str, filename: str) -> Path | None:
    from app.config import settings

    configured_base = Path(settings.file_storage_path)
    backend_root = Path(__file__).resolve().parents[2]
    base_dirs = [
        configured_base,
        backend_root / configured_base,
    ]

    seen: set[Path] = set()
    for base_dir in base_dirs:
        base_dir = base_dir.resolve()
        if base_dir in seen:
            continue
        seen.add(base_dir)

        doc_dir = base_dir / doc_id
        exact_path = doc_dir / filename
        if exact_path.exists() and exact_path.is_file():
            return exact_path

        if doc_dir.exists() and doc_dir.is_dir():
            files = [p for p in doc_dir.iterdir() if p.is_file()]
            if files:
                return files[0]

        if filename:
            same_name_files = [p for p in base_dir.rglob(filename) if p.is_file()]
            if same_name_files:
                same_name_files.sort(
                    key=lambda p: p.stat().st_mtime, reverse=True
                )
                return same_name_files[0]

    return None


# ---------------------------------------------------------------------------
# POST /upload — 上传文档
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=200, dependencies=[Depends(require_admin)])
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks, kb_category: str = "default"):
    content = await file.read()
    filename = file.filename or "unknown"

    # 校验文件格式与大小
    try:
        get_uploader().validate_file(filename, len(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 保存文件并创建元数据记录
    doc = await get_uploader().save_upload(content, filename, kb_category=kb_category)

    # 后台异步处理（解析 → 切分 → 向量化）
    background_tasks.add_task(get_uploader().process_document, doc.id)

    return {"id": doc.id, "filename": doc.filename, "status": doc.status, "kb_category_id": doc.kb_category_id}


# ---------------------------------------------------------------------------
# GET / — 获取文档列表
# ---------------------------------------------------------------------------

@router.get("", dependencies=[Depends(require_admin)])
@router.get("/", dependencies=[Depends(require_admin)])
def list_documents(category_id: str | None = None):
    """获取文档列表，支持按分类筛选（管理员专属）。"""
    db = SessionLocal()
    try:
        query = db.query(Document)
        if category_id:
            query = query.filter(Document.kb_category_id == category_id)

        docs = query.all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "status": d.status,
                "kb_category_id": d.kb_category_id,
                "kb_category": d.kb_category_rel.name if d.kb_category_rel else d.kb_category_id,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in docs
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PUT /{doc_id}/category — 移动文档分类
# ---------------------------------------------------------------------------

@router.put("/{doc_id}/category", dependencies=[Depends(require_admin)])
def move_document_category(doc_id: str, data: MoveCategoryRequest):
    """移动文档到其他分类（管理员专属）。"""
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 检查目标分类是否存在
        from app.models.kb_category import KbCategory
        category = db.get(KbCategory, data.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="目标分类不存在")

        # 更新分类
        doc.kb_category_id = data.category_id
        db.commit()

        return {"id": doc.id, "kb_category_id": doc.kb_category_id}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# DELETE /{doc_id} — 删除文档
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_document(doc_id: str):
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
    finally:
        db.close()

    await get_uploader().delete_document(doc_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# GET /status — 批量查询文档处理状态
# ---------------------------------------------------------------------------

@router.get("/status", dependencies=[Depends(require_admin)])
def get_documents_status(ids: str = ""):
    """
    Get status for multiple documents.
    Args:
        ids: Comma-separated list of document IDs.
    """
    if not ids:
        return []
        
    doc_ids = [id.strip() for id in ids.split(",") if id.strip()]
    if not doc_ids:
        return []
        
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        return [
            {"id": d.id, "status": d.status, "error_msg": d.error_msg}
            for d in docs
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /{doc_id}/status — 查询单文档处理状态
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/status", dependencies=[Depends(require_admin)])
def get_document_status(doc_id: str):
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"id": doc.id, "status": doc.status, "error_msg": doc.error_msg}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /{doc_id}/download \u2014 \u4e0b\u8f7d\u6587\u6863
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/download", dependencies=[Depends(get_current_user)])
def download_document(doc_id: str, filename: str | None = None):
    """Download the original document file."""
    from fastapi.responses import FileResponse

    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc:
            file_path = _resolve_document_file_path(doc.id, doc.filename)
        else:
            file_path = _resolve_document_file_path(doc_id, filename or "")
        if file_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"Original file not found on disk for doc_id={doc_id}",
            )

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/octet-stream"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /{doc_id}/chunks — 获取文档分片列表
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/chunks", dependencies=[Depends(get_current_user)])
def get_document_chunks(doc_id: str):
    """Get all chunks of a document."""
    from app.services.vector_store import VectorStore

    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
    finally:
        db.close()

    vector_store = VectorStore()
    chunks = vector_store.get_chunks_by_doc_id(doc_id)

    return {
        "doc_id": doc_id,
        "filename": doc.filename if doc else None,
        "total_chunks": len(chunks),
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "position": c.position,
                "content": c.content,
                "kb_category": c.kb_category,
            }
            for c in chunks
        ]
    }
