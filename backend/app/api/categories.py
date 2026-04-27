"""
知识库分类管理 API（管理员专属）。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithCountResponse,
    ChunkingConfigUpdate,
    ChunkingConfigResponse,
)
from app.db.session import SessionLocal
from app.models.kb_category import KbCategory
from app.models.document import Document
from app.models.user import User
from app.models.chunking_config import KbChunkingConfig
from app.services.document.chunking_config import ChunkingConfigService

router = APIRouter(prefix="/api/admin/categories", tags=["categories"])


def get_db():
    """获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[CategoryWithCountResponse])
async def list_categories(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取所有分类列表（管理员专属）。"""
    # 查询分类及其文档数量
    categories = db.query(KbCategory).all()

    result = []
    for cat in categories:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.kb_category_id == cat.id
        ).scalar()

        result.append(CategoryWithCountResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            created_by=cat.created_by,
            document_count=doc_count,
        ))

    return result


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建新分类（管理员专属）。"""
    # 检查名称是否已存在
    existing = db.query(KbCategory).filter(KbCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="分类名称已存在")

    # 检查分类数量上限
    count = db.query(KbCategory).count()
    if count >= 20:
        raise HTTPException(status_code=400, detail="分类数量已达上限（20个）")

    # 创建分类
    category = KbCategory(
        name=data.name,
        description=data.description,
        created_by=admin.id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    return CategoryResponse.model_validate(category)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新分类（管理员专属）。"""
    category = db.get(KbCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 检查名称是否与其他分类重复
    if data.name and data.name != category.name:
        existing = db.query(KbCategory).filter(KbCategory.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="分类名称已存在")

    # 更新字段
    if data.name:
        category.name = data.name
    if data.description is not None:
        category.description = data.description

    db.commit()
    db.refresh(category)

    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除空分类（管理员专属）。"""
    category = db.get(KbCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 检查分类下是否有文档
    doc_count = db.query(func.count(Document.id)).filter(
        Document.kb_category_id == category_id
    ).scalar()

    if doc_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"分类下仍有 {doc_count} 个文档，请先迁移或删除文档"
        )

    # 删除分类
    db.delete(category)
    db.commit()

    return {"message": "分类已删除"}


@router.get("/{category_id}/chunking-config", response_model=ChunkingConfigResponse)
async def get_chunking_config(
    category_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取分类的切分配置（管理员专属）。"""
    # 检查分类是否存在
    category = db.get(KbCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    service = ChunkingConfigService()
    config = service.get_config(category_id)

    return ChunkingConfigResponse(
        id=config.id if hasattr(config, "id") else "",
        category_id=category_id,
        chunking_strategy=config.chunking_strategy,
        max_tokens=config.max_tokens,
        overlap=config.overlap,
        strategy_overrides=config.strategy_overrides,
        created_at=config.created_at if hasattr(config, "created_at") else category.created_at,
        updated_at=config.updated_at if hasattr(config, "updated_at") else None,
    )


@router.put("/{category_id}/chunking-config", response_model=ChunkingConfigResponse)
async def upsert_chunking_config(
    category_id: str,
    data: ChunkingConfigUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建或更新分类的切分配置（管理员专属）。"""
    # 检查分类是否存在
    category = db.get(KbCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    service = ChunkingConfigService()
    config = service.upsert_config(
        category_id=category_id,
        strategy=data.chunking_strategy,
        max_tokens=data.max_tokens,
        overlap=data.overlap,
        overrides=data.strategy_overrides,
    )

    return ChunkingConfigResponse.model_validate(config)