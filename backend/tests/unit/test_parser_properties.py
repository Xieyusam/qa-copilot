"""
Property tests for DocumentParser.
Feature: internal-knowledge-base
  Property 4:  解析输出完整性
  Property 7:  解析错误状态标记
  Property 15: 解析幂等性
"""
from __future__ import annotations

import os
import tempfile

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.core.schemas import ParsedDocument
from app.services.document.parser import DocumentParser


@pytest.fixture(scope="module")
def parser() -> DocumentParser:
    return DocumentParser()


def _write_tmp(suffix: str, content: str | bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        if isinstance(content, str):
            content = content.encode("utf-8")
        os.write(fd, content)
    finally:
        os.close(fd)
    return path


# ---------------------------------------------------------------------------
# Property 4: 解析输出完整性
# Validates: Requirements 2.1, 2.5, 5.1
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 4: 解析输出完整性
@given(st.text(min_size=1, max_size=500))
@settings(max_examples=50)
def test_txt_parse_output_completeness(text: str):
    """For any non-empty text file, parse() returns a valid ParsedDocument."""
    parser = DocumentParser()
    path = _write_tmp(".txt", text)
    try:
        result = parser.parse(path, "txt")
        assert isinstance(result, ParsedDocument)
        assert result.file_type == "txt"
        assert result.doc_id  # non-empty
        assert result.filename  # non-empty
        # content should be non-empty for non-whitespace input
        if text.strip():
            assert result.content.strip()
    finally:
        os.unlink(path)


# Feature: internal-knowledge-base, Property 4: 解析输出完整性
@given(st.text(min_size=1, max_size=500))
@settings(max_examples=50)
def test_md_parse_output_completeness(text: str):
    """For any non-empty markdown file, parse() returns a valid ParsedDocument."""
    parser = DocumentParser()
    path = _write_tmp(".md", text)
    try:
        result = parser.parse(path, "md")
        assert isinstance(result, ParsedDocument)
        assert result.file_type == "md"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Property 7: 解析错误状态标记
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 7: 解析错误状态标记
@given(st.binary(min_size=1, max_size=200))
@settings(max_examples=50)
def test_corrupt_pdf_does_not_raise(data: bytes):
    """Corrupt PDF bytes should not raise — result has 'error' in metadata."""
    assume(not data.startswith(b"%PDF"))  # exclude accidentally valid PDFs
    parser = DocumentParser()
    path = _write_tmp(".pdf", data)
    try:
        result = parser.parse(path, "pdf")
        assert isinstance(result, ParsedDocument)
        # Either parsed successfully or marked with error — never raises
        # If it failed, metadata must contain 'error'
        if not result.content:
            assert "error" in result.metadata
    finally:
        os.unlink(path)


# Feature: internal-knowledge-base, Property 7: 解析错误状态标记
def test_nonexistent_file_marked_as_error():
    """Parsing a non-existent file returns ParsedDocument with error metadata."""
    parser = DocumentParser()
    result = parser.parse("/nonexistent/path/file.txt", "txt")
    assert isinstance(result, ParsedDocument)
    assert "error" in result.metadata


# ---------------------------------------------------------------------------
# Property 15: 解析幂等性
# Validates: Requirements 5.3
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 15: 解析幂等性
@given(st.text(min_size=1, max_size=300))
@settings(max_examples=50)
def test_txt_parse_idempotent(text: str):
    """Parsing the same TXT file twice yields equivalent content."""
    parser = DocumentParser()
    path = _write_tmp(".txt", text)
    try:
        result1 = parser.parse(path, "txt")
        result2 = parser.parse(path, "txt")
        assert result1.content == result2.content
        assert result1.paragraphs == result2.paragraphs
        assert result1.file_type == result2.file_type
    finally:
        os.unlink(path)


# Feature: internal-knowledge-base, Property 15: 解析幂等性
@given(st.text(min_size=1, max_size=300))
@settings(max_examples=50)
def test_md_parse_idempotent(text: str):
    """Parsing the same MD file twice yields equivalent content."""
    parser = DocumentParser()
    path = _write_tmp(".md", text)
    try:
        result1 = parser.parse(path, "md")
        result2 = parser.parse(path, "md")
        assert result1.content == result2.content
        assert result1.paragraphs == result2.paragraphs
    finally:
        os.unlink(path)
