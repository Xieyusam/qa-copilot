"""
飞书 API 客户端 - 支持文档、表格、多维表格的拉取。
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import requests

from app.config import settings
from app.services.observability.logger import get_logger

logger = get_logger(__name__)

# 飞书 API 基础 URL
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """
    飞书 API 客户端，支持拉取文档/表格/多维表格内容。
    """

    def __init__(self, app_id: str | None = None, app_secret: str | None = None):
        self._app_id = app_id or settings.feishu_app_id
        self._app_secret = app_secret or settings.feishu_app_secret
        self._tenant_access_token: str | None = None

    def is_configured(self) -> bool:
        """检查是否已配置飞书 API 凭证。"""
        return bool(self._app_id and self._app_secret)

    async def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token。"""
        resp = await asyncio.to_thread(
            requests.post,
            f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal",
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={
                "app_id": self._app_id,
                "app_secret": self._app_secret,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise PermissionError(f"飞书 API 认证失败: {data.get('msg', 'unknown error')}")
        self._tenant_access_token = data["tenant_access_token"]
        return self._tenant_access_token

    async def _headers(self) -> dict[str, str]:
        """返回带认证的请求头。"""
        if self._tenant_access_token is None:
            await self._get_tenant_access_token()
        return {
            "Authorization": f"Bearer {self._tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _ensure_token(self) -> None:
        """确保 token 有效（简单重试机制）。"""
        if self._tenant_access_token is None:
            await self._get_tenant_access_token()

    # ------------------------------------------------------------------
    # 公共 API 方法
    # ------------------------------------------------------------------

    async def fetch_document(self, doc_url: str) -> tuple[bytes, str] | None:
        """
        拉取飞书文档（Doc）内容。

        Args:
            doc_url: 飞书文档 URL，如 https://feishu.cn/docx/xxx

        Returns:
            tuple[bytes, str] | None: (文本内容 bytes, 扩展名 "txt")
        """
        await self._ensure_token()

        # 从 URL 提取 document_id
        # 支持: /docx/xxx 或 /docs/xxx
        doc_id = self._extract_doc_id(doc_url)
        if not doc_id:
            logger.warning("FeishuClient: 无法从 URL 解析 document_id: %s", doc_url)
            return None

        # 调用飞书文档 API 获取内容
        url = f"{FEISHU_BASE_URL}/docx/v1/documents/{doc_id}"
        resp = await asyncio.to_thread(requests.get, url, headers=await self._headers(), timeout=15)
        data = resp.json()

        if data.get("code") != 0:
            # token 过期时重试
            if data.get("code") in (99991668, 99991672):
                self._tenant_access_token = None
                await self._ensure_token()
                resp = await asyncio.to_thread(requests.get, url, headers=await self._headers(), timeout=15)
                data = resp.json()

            if data.get("code") != 0:
                logger.error("FeishuClient: 获取文档失败 code=%d msg=%s", data.get("code"), data.get("msg"))
                return None

        # 提取文档文本内容
        text_content = self._extract_doc_text(data)
        return text_content.encode("utf-8"), "txt"

    async def fetch_sheet(self, sheet_url: str) -> tuple[bytes, str] | None:
        """
        拉取飞书电子表格（Sheet）内容。

        Args:
            sheet_url: 飞书表格 URL，如 https://feishu.cn/sheets/xxx

        Returns:
            tuple[bytes, str] | None: (CSV 文本 bytes, 扩展名 "csv")
        """
        await self._ensure_token()

        sheet_token = await self._extract_sheet_token(sheet_url)
        if not sheet_token:
            logger.warning("FeishuClient: 无法从 URL 解析 sheet_token: %s", sheet_url)
            return None

        # 先获取所有 sheets 的 ID
        sheets_url = f"{FEISHU_BASE_URL}/sheets/v3/spreadsheets/{sheet_token}/sheets/query"
        resp = await asyncio.to_thread(requests.get, sheets_url, headers=await self._headers(), timeout=15)
        data = resp.json()

        if data.get("code") != 0:
            logger.error("FeishuClient: 获取表格sheets列表失败 code=%d msg=%s", data.get("code"), data.get("msg"))
            return None

        sheets = data.get("data", {}).get("sheets", [])
        if not sheets:
            logger.warning("FeishuClient: 表格没有sheets: %s", sheet_url)
            return None

        # 获取每个 sheet 的数据
        all_rows: list[list[str]] = []
        for sheet in sheets:
            sheet_id = sheet.get("sheet_id")
            if not sheet_id:
                continue

            # 使用实际的行列数构建 range
            row_count = sheet.get("grid_properties", {}).get("row_count", 1000)
            col_count = sheet.get("grid_properties", {}).get("column_count", 26)
            # 将列数转换为字母（最多 26 列，即 Z）
            col_letter = chr(ord('A') + min(col_count - 1, 25))
            # 限制最多 5000 行，避免请求过大
            max_row = min(row_count, 5000)
            range_value = f"{sheet_id}!A1:{col_letter}{max_row}"

            values_url = f"{FEISHU_BASE_URL}/sheets/v2/spreadsheets/{sheet_token}/values/{range_value}"
            params = {"valueRenderOption": "ToString"}
            resp = await asyncio.to_thread(requests.get, values_url, headers=await self._headers(), params=params, timeout=30)

            if resp.status_code != 200:
                continue

            sheet_data = resp.json()
            if sheet_data.get("code") != 0:
                continue

            values = sheet_data.get("data", {}).get("valueRange", {}).get("values", [])
            if values:
                # 添加 sheet 标题作为分隔
                all_rows.append([f"=== {sheet.get('title', sheet_id)} ==="])
                all_rows.extend(values)

        if not all_rows:
            logger.warning("FeishuClient: 表格没有数据: %s", sheet_url)
            return None

        # 转换为 CSV 格式
        csv_lines: list[str] = []
        for row in all_rows:
            csv_lines.append(",".join(f'"{c}"' if isinstance(c, str) and (',' in str(c) or '"' in str(c)) else str(c) if c is not None else "" for c in row))

        return "\n".join(csv_lines).encode("utf-8"), "csv"

    async def fetch_bitable(self, bitable_url: str) -> tuple[bytes, str] | None:
        """
        拉取飞书多维表格（Bitable）内容。

        Args:
            bitable_url: 飞书多维表格 URL

        Returns:
            tuple[bytes, str] | None: (文本内容 bytes, 扩展名 "txt")
        """
        await self._ensure_token()

        app_token = self._extract_bitable_token(bitable_url)
        if not app_token:
            logger.warning("FeishuClient: 无法从 URL 解析 bitable app_token: %s", bitable_url)
            return None

        # 获取多维表格信息
        url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}"
        resp = await asyncio.to_thread(requests.get, url, headers=await self._headers(), timeout=15)
        data = resp.json()

        if data.get("code") != 0:
            if data.get("code") in (99991668, 99991672):
                self._tenant_access_token = None
                await self._ensure_token()
                resp = await asyncio.to_thread(requests.get, url, headers=await self._headers(), timeout=15)
                data = resp.json()

            if data.get("code") != 0:
                logger.error("FeishuClient: 获取多维表格失败 code=%d msg=%s", data.get("code"), data.get("msg"))
                return None

        # 获取所有表
        tables_url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables"
        tables_resp = await asyncio.to_thread(requests.get, tables_url, headers=await self._headers(), timeout=15)
        tables_data = tables_resp.json()

        lines: list[str] = []
        if tables_data.get("data"):
            for table in tables_data["data"].get("items", []):
                table_name = table.get("name", "未命名表")
                lines.append(f"## {table_name}")

                # 获取表中记录
                records_url = f"{FEISHU_BASE_URL}/bitable/v1/apps/{app_token}/tables/{table['table_id']}/records"
                records_resp = await asyncio.to_thread(requests.get, records_url, headers=await self._headers(), timeout=15)
                records_data = records_resp.json()
                if records_data.get("data"):
                    for record in records_data["data"].get("items", []):
                        fields = record.get("fields", {})
                        row_text = " | ".join(f"{k}: {v}" for k, v in fields.items() if v)
                        if row_text:
                            lines.append(row_text)
                lines.append("")

        if not lines:
            text = f"多维表格: {app_token}"
        else:
            text = "\n".join(lines)

        return text.encode("utf-8"), "txt"

    async def fetch_document_by_url(self, url: str) -> tuple[bytes, str] | None:
        """
        根据 URL 类型自动选择拉取方式（doc / sheet / bitable / wiki）。

        Args:
            url: 飞书文档 URL

        Returns:
            tuple[bytes, str] | None
        """
        # 优先处理 wiki URL（需要通过 wiki API 获取实际文档类型）
        if "/wiki/" in url:
            return await self._fetch_wiki_document(url)

        if "/sheets/" in url or "/sheet/" in url:
            return await self.fetch_sheet(url)
        elif "/bitable/" in url:
            return await self.fetch_bitable(url)
        else:
            # 默认按文档处理
            return await self.fetch_document(url)

    def detect_doc_type(self, url: str) -> str | None:
        """
        根据 URL 模式检测文档类型。

        Args:
            url: 飞书文档 URL

        Returns:
            "doc" | "sheet" | "bitable" | None
        """
        if "/sheets/" in url or "/sheet/" in url:
            return "sheet"
        elif "/bitable/" in url:
            return "bitable"
        elif "/wiki/" in url:
            # wiki 类型需要通过 API 才能确定具体类型
            return None
        elif "/docx/" in url or "/docs/" in url:
            return "doc"
        return None

    async def get_wiki_doc_type(self, wiki_url: str) -> str | None:
        """
        从 wiki URL 获取实际文档类型。

        Args:
            wiki_url: 飞书 wiki URL

        Returns:
            "doc" | "sheet" | "bitable" | None
        """
        await self._ensure_token()

        wiki_match = re.match(r"https?://[^/]+/wiki/([a-zA-Z0-9_-]+)", wiki_url)
        if not wiki_match:
            logger.warning("FeishuClient: 无法从 wiki URL 解析 node_token: %s", wiki_url)
            return None

        node_token = wiki_match.group(1)

        wiki_api_url = f"{FEISHU_BASE_URL}/wiki/v2/spaces/get_node"
        resp = await asyncio.to_thread(
            requests.get,
            wiki_api_url,
            headers=await self._headers(),
            params={"token": node_token, "obj_type": "wiki"},
            timeout=10,
        )
        data = resp.json()

        if data.get("code") != 0:
            logger.error("FeishuClient: 获取 wiki 节点类型失败 code=%d msg=%s", data.get("code"), data.get("msg"))
            return None

        node_data = data.get("data", {}).get("node", {})
        obj_type = node_data.get("obj_type")  # "docx", "sheet", "bitable", "doc"

        # 标准化类型名称
        if obj_type == "docx":
            return "doc"
        elif obj_type in ("sheet", "bitable"):
            return obj_type
        elif obj_type == "doc":
            return "doc"

        return None

    async def _fetch_wiki_document(self, wiki_url: str) -> tuple[bytes, str] | None:
        """
        从 wiki URL 获取实际文档内容。

        Args:
            wiki_url: 飞书 wiki URL

        Returns:
            tuple[bytes, str] | None
        """
        await self._ensure_token()

        # 从 wiki URL 提取 node_token（更宽松的正则匹配各种格式）
        wiki_match = re.match(r"https?://[^/]+/wiki/([a-zA-Z0-9_-]+)", wiki_url)
        if not wiki_match:
            logger.warning("FeishuClient: 无法从 wiki URL 解析 node_token: %s", wiki_url)
            return None

        node_token = wiki_match.group(1)

        # 调用 wiki API 获取节点信息（包含实际文档类型和 token）
        wiki_api_url = f"{FEISHU_BASE_URL}/wiki/v2/spaces/get_node"
        resp = await asyncio.to_thread(
            requests.get,
            wiki_api_url,
            headers=await self._headers(),
            params={"token": node_token, "obj_type": "wiki"},
            timeout=10,
        )
        data = resp.json()

        if data.get("code") != 0:
            logger.error("FeishuClient: 获取 wiki 节点失败 code=%d msg=%s", data.get("code"), data.get("msg"))
            return None

        node_data = data.get("data", {}).get("node", {})
        obj_type = node_data.get("obj_type")  # "docx", "sheet", "bitable", "doc"
        doc_token = node_data.get("obj_token")

        if not doc_token:
            logger.error("FeishuClient: wiki 节点缺少 obj_token: %s", wiki_url)
            return None

        # 根据实际文档类型构建新 URL 并拉取
        if obj_type == "sheet":
            sheet_url = f"https://feishu.cn/sheets/{doc_token}"
            return await self.fetch_sheet(sheet_url)
        elif obj_type == "bitable":
            bitable_url = f"https://feishu.cn/bitable/{doc_token}"
            return await self.fetch_bitable(bitable_url)
        elif obj_type in ("docx", "doc"):
            # 处理 "docx" 和遗留的 "doc" 类型
            docx_url = f"https://feishu.cn/docx/{doc_token}"
            return await self.fetch_document(docx_url)
        else:
            # 未知类型，明确返回 None
            logger.error("FeishuClient: 未知 wiki obj_type '%s' for node %s", obj_type, wiki_url)
            return None

    async def get_document_title(self, url: str) -> str | None:
        """获取飞书文档标题。"""
        await self._ensure_token()

        # 优先从 wiki URL 解析
        wiki_match = re.match(r"http[s]?://[^/]+/wiki/(\w+)", url)
        if wiki_match:
            node_token = wiki_match.group(1)
            wiki_url = f"{FEISHU_BASE_URL}/wiki/v2/spaces/get_node"
            resp = await asyncio.to_thread(
                requests.get,
                wiki_url,
                headers=await self._headers(),
                params={"token": node_token, "obj_type": "wiki"},
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("node", {}).get("title")

        # 尝试从 spreadsheet URL 解析 title
        sheet_token = await self._extract_sheet_token(url)
        if sheet_token:
            spreadsheet_url = f"{FEISHU_BASE_URL}/sheets/v3/spreadsheets/{sheet_token}"
            resp = await asyncio.to_thread(requests.get, spreadsheet_url, headers=await self._headers(), timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("spreadsheetTitle", "")

        return None

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _extract_doc_id(self, url: str) -> str | None:
        """从 docx URL 提取 document_id。"""
        # https://xxx.feishu.cn/docx/xxxxx 或 https://xxx.larksuite.com/docx/xxxxx
        match = re.search(r'/docx/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None

    async def _extract_sheet_token(self, url: str) -> str | None:
        """从 sheet URL 提取 spreadsheet_token（处理 wiki 重定向）。"""
        # https://xxx.feishu.cn/sheets/xxxxx
        match = re.search(r'/sheets?/([a-zA-Z0-9_-]+)', url)
        if not match:
            return None
        sheet_token = match.group(1)

        # wiki 类型的 sheet 需要额外解析
        # wiki URL: https://xxx.feishu.cn/wiki/xxxxx -> 需要获取实际的 sheet_token
        wiki_match = re.match(r"http[s]?://[^/]+/wiki/(\w+)", url)
        if wiki_match:
            node_token = wiki_match.group(1)
            wiki_url = f"{FEISHU_BASE_URL}/wiki/v2/spaces/get_node"
            resp = await asyncio.to_thread(
                requests.get,
                wiki_url,
                headers=await self._headers(),
                params={"token": node_token, "obj_type": "wiki"},
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                sheet_token = data.get("data", {}).get("node", {}).get("obj_token", sheet_token)

        return sheet_token

    def _extract_bitable_token(self, url: str) -> str | None:
        """从 bitable URL 提取 app_token。"""
        match = re.search(r'/bitable/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None

    def _extract_doc_text(self, data: dict[str, Any]) -> str:
        """从飞书文档 API 响应中提取纯文本内容。"""
        blocks = data.get("data", {}).get("document", {}).get("blocks", [])
        text_parts: list[str] = []

        for block in blocks:
            block_type = block.get("block_type")
            # 文本类 block 包含 paragraph
            paragraph = block.get("paragraph", {})
            elements = paragraph.get("elements", [])
            for elem in elements:
                text = elem.get("text_run", {}).get("content", "")
                if text:
                    text_parts.append(text)
            # 每个 block 后换行
            if text_parts and not text_parts[-1].endswith("\n"):
                text_parts.append("\n")

        return "".join(text_parts).strip()

    def _sheet_values_to_csv(self, data: dict[str, Any]) -> str:
        """将飞书表格 API 响应转换为 CSV 文本。"""
        rows: list[list[str]] = []
        value_ranges = data.get("data", {}).get("valueRanges", [])
        for value_range in value_ranges:
            for row in value_range.get("values", []):
                rows.append([str(cell) if cell is not None else "" for cell in row])

        if not rows:
            return ""

        # 简单 CSV 格式化
        lines: list[str] = []
        for row in rows:
            lines.append(",".join(f'"{c}"' if ',' in c or '"' in c else c for c in row))
        return "\n".join(lines)


# 向后兼容别名
BaseFeishuFetcher = FeishuClient

