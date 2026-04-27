"""
Core data classes for the internal knowledge base system.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ========== 分类相关 Schemas ==========

class CategoryBase(BaseModel):
    """分类基础 Schema。"""
    name: str
    description: str | None = None


class CategoryCreate(CategoryBase):
    """创建分类请求 Schema。"""
    pass


class CategoryUpdate(BaseModel):
    """更新分类请求 Schema。"""
    name: str | None = None
    description: str | None = None


class CategoryResponse(CategoryBase):
    """分类响应 Schema。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime | None = None
    created_by: str | None = None


class CategoryWithCountResponse(CategoryResponse):
    """带文档数量的分类响应 Schema。"""
    document_count: int = 0


# ========== 切分配置相关 Schemas ==========

class ChunkingConfigBase(BaseModel):
    """切分配置基础 Schema。"""
    chunking_strategy: str = "recursive_text"
    max_tokens: int = 512
    overlap: int = 50
    strategy_overrides: dict | None = None


class ChunkingConfigUpdate(ChunkingConfigBase):
    """更新切分配置请求 Schema。"""
    pass


class ChunkingConfigResponse(ChunkingConfigBase):
    """切分配置响应 Schema。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_id: str
    created_at: datetime
    updated_at: datetime | None = None


# ========== 飞书文档相关 Schemas ==========

class FeishuDocumentBase(BaseModel):
    """飞书文档基础 Schema。"""
    feishu_doc_url: str
    feishu_doc_type: str | None = None  # "doc" | "sheet" | "bitable"，可选，API 将自动推断
    title: str | None = None  # 可选，API 将自动获取
    kb_category_id: str
    is_active: bool = True
    sync_interval_hours: int = 24


class FeishuDocumentCreate(FeishuDocumentBase):
    """创建飞书文档请求 Schema。"""
    pass


class FeishuDocumentUpdate(BaseModel):
    """更新飞书文档请求 Schema。"""
    feishu_doc_url: str | None = None
    feishu_doc_type: str | None = None  # "doc" | "sheet" | "bitable"
    title: str | None = None
    kb_category_id: str | None = None
    is_active: bool | None = None
    sync_interval_hours: int | None = None


class FeishuDocumentResponse(FeishuDocumentBase):
    """飞书文档响应 Schema。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    last_fetched_at: datetime | None = None
    last_sync_status: str
    last_sync_error: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


# ========== 数据类（原有） ==========


@dataclass
class ParsedDocument:
    doc_id: str
    filename: str
    file_type: str
    content: str
    paragraphs: list[str]
    metadata: dict[str, Any]
    parsed_at: datetime

    def to_json(self) -> str:
        """Serialize to JSON string; datetime fields are ISO 8601 strings."""
        data = asdict(self)
        data["parsed_at"] = self.parsed_at.isoformat()
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "ParsedDocument":
        """Deserialize from a JSON string produced by to_json()."""
        data = json.loads(json_str)
        data["parsed_at"] = datetime.fromisoformat(data["parsed_at"])
        return cls(**data)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    content: str
    token_count: int
    position: int
    kb_category: str = "default"
    kb_category_id: str = "default"  # 新增：分类 ID


@dataclass
class SourceRef:
    doc_id: str
    filename: str
    chunk_position: int
    similarity_score: float | None = None
    content: str | None = None

@dataclass
class Message:
    role: str  # user | assistant
    content: str
    timestamp: datetime
    sources: list[SourceRef] | None = None
    additional_kwargs: dict[str, Any] | None = None  # e.g., {"attachments": [...]}


@dataclass
class Session:
    session_id: str
    messages: list[Message]
    created_at: datetime
    last_active: datetime
    title: str = "新对话"
