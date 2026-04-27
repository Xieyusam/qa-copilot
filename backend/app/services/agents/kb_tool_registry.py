"""KB 工具注册表 - 管理所有 KB 检索工具"""
from typing import List

from app.db.session import SessionLocal
from app.models.kb_category import KbCategory
from app.services.agents.tools.kb_retriever_tool import KbRetrieverTool
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class KbToolRegistry:
    """KB 工具注册表，按类型分组"""

    def __init__(self):
        self._search_tools: dict = {}  # 非翻译 KB 工具
        self._translate_tools: dict = {}  # 翻译 KB 工具
        self._refresh()

    def _refresh(self):
        """从数据库加载所有 KB，构建工具（不存储 retriever 实例）"""
        db = SessionLocal()
        try:
            categories = db.query(KbCategory).all()
            for cat in categories:
                # 只存储 category_name，不存储 retriever（避免序列化问题）
                tool = KbRetrieverTool(
                    name=f"kb_{cat.name}",
                    description=f"{cat.name}知识库，用于查询{cat.description or cat.name}的相关问题",
                    category_id=str(cat.id),
                )
                # 按名称是否含"翻译"分组
                if "翻译" in cat.name:
                    self._translate_tools[cat.name] = tool
                    logger.info(f"KbToolRegistry: 注册翻译 KB 工具 {tool.name}")
                else:
                    self._search_tools[cat.name] = tool
                    logger.info(f"KbToolRegistry: 注册搜索 KB 工具 {tool.name}")
        except Exception as e:
            logger.error(f"KbToolRegistry 刷新失败: {e}")
        finally:
            db.close()

    def get_search_tools(self) -> List[KbRetrieverTool]:
        """获取所有搜索 KB 工具"""
        return list(self._search_tools.values())

    def get_translate_tools(self) -> List[KbRetrieverTool]:
        """获取所有翻译 KB 工具"""
        return list(self._translate_tools.values())

    def refresh(self):
        """刷新工具列表（当 KB 发生变化时调用）"""
        self._search_tools.clear()
        self._translate_tools.clear()
        self._refresh()
        logger.info("KbToolRegistry: 已刷新")
