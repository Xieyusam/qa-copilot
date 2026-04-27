"""
飞书文档管理 API（管理员专属）。
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin, get_db as dep_get_db
from app.core.schemas import FeishuDocumentCreate, FeishuDocumentUpdate, FeishuDocumentResponse
from app.db.session import SessionLocal
from app.models.feishu_document import FeishuDocument
from app.models.document import Document
from app.models.user import User
from app.services.integrations.scheduler import get_scheduler
from app.services.observability.logger import get_logger

router = APIRouter(prefix="/api/admin/feishu", tags=["feishu"])
logger = get_logger(__name__)


def get_db():
    """获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/documents", response_model=FeishuDocumentResponse, status_code=201)
async def register_feishu_document(
    data: FeishuDocumentCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    admin: User = Depends(require_admin),
):
    """
    注册新的飞书文档（管理员专属）。

    流程：
    1. 创建 FeishuDocument 记录
    2. 立即创建 Document 记录（占位），状态为 pending
    3. 后台异步触发同步，更新 Document 内容和状态

    Args:
        data: 飞书文档配置信息（feishu_doc_type 和 title 可选，将自动检测）
        background_tasks: FastAPI 后台任务
        admin: 管理员用户
        db: 数据库会话

    Returns:
        创建的飞书文档配置
    """
    from app.services.feishu_client import FeishuClient

    feishu_client = FeishuClient()

    # 自动检测文档类型（如果未提供）
    feishu_doc_type = data.feishu_doc_type
    if feishu_doc_type is None:
        # 优先从 URL 模式检测
        feishu_doc_type = feishu_client.detect_doc_type(data.feishu_doc_url)
        # wiki URL 需要通过 API 确定类型
        if feishu_doc_type is None and "/wiki/" in data.feishu_doc_url:
            feishu_doc_type = await feishu_client.get_wiki_doc_type(data.feishu_doc_url)
        if feishu_doc_type is None:
            raise HTTPException(status_code=400, detail="无法从 URL 识别文档类型，请手动指定 feishu_doc_type")

    # 验证文档类型
    if feishu_doc_type not in ("doc", "sheet", "bitable"):
        raise HTTPException(status_code=400, detail="不支持的文档类型，仅支持 doc/sheet/bitable")

    # 自动获取文档标题（如果未提供）
    title = data.title
    if title is None:
        title = await feishu_client.get_document_title(data.feishu_doc_url)
        if title is None:
            title = "未命名文档"  # 使用默认标题

    # 创建飞书文档配置
    feishu_doc = FeishuDocument(
        feishu_doc_url=data.feishu_doc_url,
        feishu_doc_type=feishu_doc_type,
        title=title,
        kb_category_id=data.kb_category_id,
        is_active=True,
        sync_interval_hours=-1,  # 不自动同步
        last_sync_status="pending",
    )
    db.add(feishu_doc)
    db.commit()
    db.refresh(feishu_doc)

    # 立即创建 Document 记录（占位），这样用户可以立即在文档列表看到
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename=title,  # 占位文件名，后续会更新
        file_type=feishu_doc_type,
        file_size=0,  # 占位，后续会更新
        status="pending",  # 初始状态
        kb_category_id=data.kb_category_id,
        feishu_doc_id=feishu_doc.id,
    )
    db.add(doc)
    db.commit()
    logger.info("Feishu API: created placeholder document %s for feishu_doc %s", doc_id, feishu_doc.id)

    # 后台异步触发同步（使用 BackgroundTasks，不阻塞用户响应）
    background_tasks.add_task(_sync_feishu_task, feishu_doc.id, doc_id)

    return feishu_doc


async def _sync_feishu_task(feishu_doc_id: str, doc_id: str) -> None:
    """后台异步同步任务。"""
    from app.db.session import SessionLocal
    from app.services.feishu_client import FeishuClient
    from app.services.feishu_fetcher import FeishuFetcher

    db = SessionLocal()
    try:
        feishu_doc = db.get(FeishuDocument, feishu_doc_id)
        if not feishu_doc:
            logger.error("Feishu sync task: feishu_doc %s not found", feishu_doc_id)
            return

        doc = db.get(Document, doc_id)
        if not doc:
            logger.error("Feishu sync task: document %s not found", doc_id)
            return

        logger.info("Feishu sync task: starting sync for doc_id=%s", doc_id)

        # 创建飞书客户端并执行同步，传递 existing_doc_id
        fetcher = FeishuFetcher(client=FeishuClient())
        await fetcher.sync_document(feishu_doc, existing_doc_id=doc_id)
        logger.info("Feishu sync task: completed sync for doc_id=%s", doc_id)

    except Exception as exc:
        # 同步失败，更新状态
        logger.exception("Feishu sync task: failed for doc_id=%s: %s", doc_id, exc)
        try:
            doc = db.get(Document, doc_id)
            if doc:
                doc.status = "failed"
            feishu_doc = db.get(FeishuDocument, feishu_doc_id)
            if feishu_doc:
                feishu_doc.last_sync_status = "failed"
                feishu_doc.last_sync_error = str(exc)
            db.commit()
        except Exception as inner_exc:
            logger.error("Feishu sync task: failed to update error status: %s", inner_exc)
    finally:
        db.close()


@router.get("/documents", response_model=list[FeishuDocumentResponse])
async def list_feishu_documents(
    db: Annotated[Session, Depends(get_db)],
    admin: User = Depends(require_admin),
    category_id: str | None = None,
):
    """
    获取飞书文档列表（管理员专属）。

    Args:
        category_id: 可选，按分类 ID 过滤
        admin: 管理员用户
        db: 数据库会话

    Returns:
        飞书文档配置列表
    """
    query = db.query(FeishuDocument)

    if category_id is not None:
        query = query.filter(FeishuDocument.kb_category_id == category_id)

    feishu_docs = query.order_by(FeishuDocument.created_at.desc()).all()
    return feishu_docs


@router.put("/documents/{doc_id}", response_model=FeishuDocumentResponse)
async def update_feishu_document(
    doc_id: str,
    data: FeishuDocumentUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: User = Depends(require_admin),
):
    """
    更新飞书文档配置（管理员专属）。

    Args:
        doc_id: 飞书文档 ID
        data: 更新数据
        admin: 管理员用户
        db: 数据库会话

    Returns:
        更新后的飞书文档配置
    """
    feishu_doc = db.get(FeishuDocument, doc_id)
    if not feishu_doc:
        raise HTTPException(status_code=404, detail="飞书文档不存在")

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feishu_doc, field, value)

    db.commit()
    db.refresh(feishu_doc)

    return feishu_doc


@router.delete("/documents/{doc_id}")
async def delete_feishu_document(
    doc_id: str,
    db: Annotated[Session, Depends(get_db)],
    admin: User = Depends(require_admin),
):
    """
    删除飞书文档配置（管理员专属）。

    注意：这不会删除已同步的文档内容，仅删除同步配置。

    Args:
        doc_id: 飞书文档 ID
        admin: 管理员用户
        db: 数据库会话

    Returns:
        删除确认消息
    """
    feishu_doc = db.get(FeishuDocument, doc_id)
    if not feishu_doc:
        raise HTTPException(status_code=404, detail="飞书文档不存在")

    db.delete(feishu_doc)
    db.commit()

    return {"message": "飞书文档已删除"}


@router.post("/documents/{doc_id}/sync")
async def trigger_sync(
    doc_id: str,
    db: Annotated[Session, Depends(get_db)],
    admin: User = Depends(require_admin),
):
    """
    手动触发单个飞书文档同步（管理员专属）。

    Args:
        doc_id: 飞书文档 ID
        admin: 管理员用户
        db: 数据库会话

    Returns:
        同步状态消息
    """
    feishu_doc = db.get(FeishuDocument, doc_id)
    if not feishu_doc:
        raise HTTPException(status_code=404, detail="飞书文档不存在")

    feishu_doc.last_sync_status = "pending"
    db.commit()

    # 立即触发同步（不依赖定时器）
    sched = get_scheduler()
    if sched:
        sched.trigger_sync_now(doc_id)

    return {"message": "同步任务已触发", "doc_id": doc_id}


@router.post("/sync-all")
async def trigger_sync_all(
    db: Annotated[Session, Depends(get_db)],
    admin: User = Depends(require_admin),
):
    """
    触发所有活跃飞书文档的同步（管理员专属）。

    Args:
        admin: 管理员用户
        db: 数据库会话

    Returns:
        触发的文档数量
    """
    feishu_docs = db.query(FeishuDocument).filter(
        FeishuDocument.is_active == True
    ).all()

    sched = get_scheduler()
    for feishu_doc in feishu_docs:
        feishu_doc.last_sync_status = "pending"
        if sched:
            sched.trigger_sync_now(feishu_doc.id)

    db.commit()

    return {"message": f"已触发 {len(feishu_docs)} 个文档的同步任务"}
