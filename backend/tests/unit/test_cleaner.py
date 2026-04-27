"""
Tests for DocumentCleaner.
"""
from __future__ import annotations

import pytest

from app.services.document.cleaner import DocumentCleaner


class TestDocumentCleaner:
    """Test suite for DocumentCleaner."""

    @pytest.fixture
    def cleaner(self) -> DocumentCleaner:
        return DocumentCleaner()

    # -------------------------------------------------------------------------
    # _remove_html tests
    # -------------------------------------------------------------------------

    def test_remove_simple_html_tags(self, cleaner):
        text = "<p>Hello <strong>World</strong></p>"
        result = cleaner._remove_html(text)
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Hello World" in result

    def test_remove_script_tags_and_content(self, cleaner):
        text = "Before <script>alert('xss')</script> After"
        result = cleaner._remove_html(text)
        assert "alert" not in result
        assert "Before" in result
        assert "After" in result

    def test_remove_style_tags_and_content(self, cleaner):
        text = "Text <style>.cls { color: red }</style> More text"
        result = cleaner._remove_html(text)
        assert ".cls" not in result
        assert "Text" in result
        assert "More text" in result

    def test_remove_html_entities(self, cleaner):
        text = "Hello&nbsp;World &lt;tag&gt; &amp; &quot;quoted&quot;"
        result = cleaner._remove_html(text)
        assert "&nbsp;" not in result
        assert "&lt;" not in result
        assert " " in result
        assert "<" in result
        assert "&" in result

    def test_remove_numeric_html_entities(self, cleaner):
        text = "&#60;script&#62; &#x3C;tag&#x3E;"
        result = cleaner._remove_html(text)
        assert "<script" in result
        assert "<tag>" in result

    # -------------------------------------------------------------------------
    # _remove_special_chars tests
    # -------------------------------------------------------------------------

    def test_remove_zero_width_space(self, cleaner):
        text = "Hello\u200bWorld"
        result = cleaner._remove_special_chars(text)
        assert "\u200b" not in result
        assert "HelloWorld" in result

    def test_remove_zero_width_joiner(self, cleaner):
        text = "Hello\u200dWorld"
        result = cleaner._remove_special_chars(text)
        assert "\u200d" not in result
        assert "HelloWorld" in result

    def test_remove_byte_order_mark(self, cleaner):
        text = "\ufeffHello World"
        result = cleaner._remove_special_chars(text)
        assert "\ufeff" not in result
        assert "Hello World" in result

    def test_remove_control_chars(self, cleaner):
        text = "Hello\x00World\x1fTest"
        result = cleaner._remove_special_chars(text)
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "HelloWorldTest" in result

    def test_preserve_newlines_and_tabs(self, cleaner):
        text = "Line1\nLine2\tLine3"
        result = cleaner._remove_special_chars(text)
        assert "\n" in result
        assert "\t" in result

    # -------------------------------------------------------------------------
    # _normalize_whitespace tests
    # -------------------------------------------------------------------------

    def test_normalize_multiple_spaces_to_one(self, cleaner):
        text = "Hello    World"
        result = cleaner._normalize_whitespace(text)
        assert "    " not in result
        assert "Hello World" in result

    def test_normalize_tabs_to_space(self, cleaner):
        text = "Hello\t\tWorld"
        result = cleaner._normalize_whitespace(text)
        assert "\t" not in result
        assert "Hello World" in result

    def test_normalize_multiple_newlines(self, cleaner):
        text = "Line1\n\n\n\nLine2"
        result = cleaner._normalize_whitespace(text)
        # 3+ newlines -> 2 newlines
        assert result.count("\n\n\n") == 0
        assert "Line1\n\nLine2" in result

    def test_normalize_trailing_spaces(self, cleaner):
        text = "Hello   \nWorld"
        result = cleaner._normalize_whitespace(text)
        assert "Hello   \n" not in result
        assert "Hello\nWorld" in result

    # -------------------------------------------------------------------------
    # _filter_noise_lines tests
    # -------------------------------------------------------------------------

    def test_filter_short_digit_lines(self, cleaner):
        text = "123456\nHello\n789"
        result = cleaner._filter_noise_lines(text)
        assert "123456" not in result
        assert "Hello" in result

    def test_filter_single_char_non_chinese(self, cleaner):
        text = "a\nHello\nb"
        result = cleaner._filter_noise_lines(text)
        assert "a\n" not in result
        assert "Hello" in result

    def test_preserve_chinese_characters(self, cleaner):
        text = "中\nHello\na"  # 中 is single Chinese char
        result = cleaner._filter_noise_lines(text)
        assert "中" in result
        assert "Hello" in result

    def test_filter_duplicate_consecutive_lines(self, cleaner):
        text = "Hello\nHello\nWorld\nWorld"
        result = cleaner._filter_noise_lines(text)
        assert result.count("Hello") == 1
        assert result.count("World") == 1

    # -------------------------------------------------------------------------
    # Integration tests (clean)
    # -------------------------------------------------------------------------

    def test_clean_full_pipeline(self, cleaner):
        dirty = """
        <html>
        <body>
            <script>bad();</script>
            <p>Hello\u200bWorld</p>
            \n\n\n
            123456\n
            <style>.cls{}</style>
            中\n
            a\n
            Test    \n
        </body>
        </html>
        """
        result = cleaner.clean(dirty)
        assert "<html>" not in result
        assert "<script>" not in result
        assert "\u200b" not in result
        assert "123456" not in result
        assert "a\n" not in result
        assert result.startswith("Hello")
        assert result.endswith("Test")

    def test_clean_preserves_meaningful_content(self, cleaner):
        text = """
        <div>这是中文内容</div>
        Some English text here.

        1234567890

        More meaningful content.
        """
        result = cleaner.clean(text)
        assert "这是中文内容" in result
        assert "Some English text here" in result
        assert "More meaningful content" in result
        assert "1234567890" in result  # 10 digits - length >= 10, so not filtered
