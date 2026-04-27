"""
DocumentCleaner - 文档清洗模块
对解析后的文本进行清洗，去除 HTML、特殊字符、噪声等。
"""
from __future__ import annotations

import re


class DocumentCleaner:
    """文档清洗器 - 清洗 HTML、特殊字符、噪声等"""

    # 零宽字符
    _ZW_CHARS = ''.join([
        chr(0x200b),  # \u200b - ZERO WIDTH SPACE
        chr(0x200c),  # \u200c - ZERO WIDTH NON-JOINER
        chr(0x200d),  # \u200d - ZERO WIDTH JOINER
        chr(0xfeff),  # \ufeff - BYTE ORDER MARK
    ])
    ZERO_WIDTH_CHARS = re.compile(rf"[{_ZW_CHARS}]")

    # 控制字符（排除换行\r\n和制表符\t）
    CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    def clean(self, text: str) -> str:
        """
        执行完整清洗流程。
        """
        text = self._remove_html(text)
        text = self._remove_special_chars(text)
        text = self._normalize_whitespace(text)
        text = self._filter_noise_lines(text)
        return text.strip()

    def _remove_html(self, text: str) -> str:
        """去除 HTML 标签、script、style 及其内容，以及 HTML 实体转义。"""
        # 使用正则去除 HTML 标签（包括多行）
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)

        # HTML 实体转义
        html_entities = {
            "&nbsp;": " ",
            "&lt;": "<",
            "&gt;": ">",
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
            "&#39;": "'",
            "&mdash;": "—",
            "&ndash;": "–",
            "&hellip;": "...",
            "&#xA0;": " ",
        }
        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        # 通用数字 HTML 实体 (&#60; 等)
        text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
        text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)

        return text

    def _remove_special_chars(self, text: str) -> str:
        """去除零宽字符和控制字符。"""
        text = self.ZERO_WIDTH_CHARS.sub("", text)
        text = self.CONTROL_CHARS.sub("", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符：多个空格/制表符合并为单空格，3+连续换行压缩为2个。"""
        # 多个空格或制表符 -> 单空格
        text = re.sub(r"[ \t]+", " ", text)
        # 3个或以上连续换行 -> 2个换行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行尾多余空格
        text = re.sub(r"[ \t]+\n", "\n", text)
        return text

    def _filter_noise_lines(self, text: str) -> str:
        """过滤噪声行：纯数字行、单字符行（除中文外）、连续重复行。"""
        lines = text.split("\n")
        filtered_lines = []
        prev_line = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 过滤纯数字行（长度<10且全是数字）
            if len(stripped) < 10 and stripped.isdigit():
                continue

            # 过滤单字符行（除中文外）
            # 中文 Unicode 范围：\u4e00-\u9fff
            if len(stripped) == 1 and not re.match(r"[\u4e00-\u9fff]", stripped):
                continue

            # 过滤连续重复行
            if stripped == prev_line:
                continue

            filtered_lines.append(line)
            prev_line = stripped

        return "\n".join(filtered_lines)
