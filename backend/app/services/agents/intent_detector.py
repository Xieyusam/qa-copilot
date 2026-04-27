"""意图检测器 - 规则 + LLM 混合"""
import re
from typing import Optional

from app.services.observability.logger import get_logger

logger = get_logger(__name__)


# 意图类型关键词
INTENT_KEYWORDS = {
    "jira": [
        r"jira", r"\bjira\b",  # 匹配 jira 关键词
        r"项目.*bug", r"bug.*数量", r"issue", r"epic",
        r"sprint", r"story", r"proj-\d+",  # JIRA 特有术语（注意：查询会被转小写）
        r"task", r"subtask",
    ],
    "log": [
        r"日志", r"logs?", r"\blog\b",
        r"error", r"exception", r"失败", r"异常",
        r"stack", r"traceback",
    ],
    "translate": [
        r"翻译", r"translate", r"translat",
        r"译成", r"转成", r"成英文", r"成中文",
        r"翻译成", r"translate to",
    ],
    "summarize": [
        r"总结", r"摘要", r"summarize", r"概括",
        r"凝练", r"精简", r"提取要点", r"要点",
    ],
}


def detect_intent_by_rules(query: str) -> Optional[str]:
    """
    根据关键词规则检测意图类型（确定性规则）

    Returns:
        intent type string or None if no match
    """
    query_lower = query.lower()

    for intent_type, patterns in INTENT_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"规则匹配到 intent: {intent_type}, 模式: {pattern}")
                return intent_type

    return None


class IntentDetector:
    """
    意图检测器 - 规则 + LLM 混合

    策略：
    1. 先用规则匹配（确定性高、速度快）
    2. 规则无法匹配再用 LLM 兜底
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    async def detect(self, query: str) -> str:
        """
        检测单条查询的意图类型

        Args:
            query: 用户查询

        Returns:
            intent type: "search", "jira", "log", "translate", "summarize"
        """
        # Step 1: 规则匹配
        intent = detect_intent_by_rules(query)
        if intent:
            logger.info(f"规则匹配 intent: {intent} <- {query}")
            return intent

        # Step 2: LLM 兜底（默认返回 search）
        intent = await self._llm_detect(query)
        logger.info(f"LLM 检测 intent: {intent} <- {query}")
        return intent

    async def detect_multi_intent(self, user_input: str) -> list[str]:
        """
        检测用户输入中的多个意图（支持并行）

        Args:
            user_input: 用户输入，如 "查 jira 项目，同时查云测平台"

        Returns:
            intent 类型列表
        """
        # 1. 按常见分隔符拆分
        queries = self._split_queries(user_input)

        intents = []
        for q in queries:
            intent = await self.detect(q)
            intents.append(intent)

        return intents

    def _split_queries(self, user_input: str) -> list[str]:
        """
        拆分用户输入为独立查询

        支持的分隔符：同时、并且、而且、然后、,、，、、
        """
        separators = r"[,，、同时并且而且然后]"
        parts = re.split(separators, user_input)
        return [p.strip() for p in parts if p.strip()]

    async def _llm_detect(self, query: str) -> str:
        """
        使用 LLM 检测意图

        当规则无法匹配时使用
        """
        prompt = f"""分析用户查询，判断意图类型。

支持的类型：
- search: 知识库文档检索（默认类型）
- jira: JIRA 查询
- log: 日志分析
- translate: 翻译
- summarize: 总结

查询：{query}

只返回一个词：search、jira、log、translate 或 summarize"""

        try:
            response = await self.llm.chat([
                {"role": "user", "content": prompt}
            ])

            # 提取返回的意图类型
            response = response.strip().lower()

            # 验证返回的类型
            valid_types = {"search", "jira", "log", "translate", "summarize"}
            if response in valid_types:
                return response

            # 默认返回 search
            return "search"

        except Exception as e:
            logger.error(f"LLM 意图检测失败: {e}")
            return "search"
