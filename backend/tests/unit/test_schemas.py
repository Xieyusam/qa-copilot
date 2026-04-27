"""
Property tests for ParsedDocument serialization (Property 14).
Feature: internal-knowledge-base, Property 14: ParsedDocument 序列化往返
"""
from __future__ import annotations

from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.schemas import ParsedDocument


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_text = st.text(min_size=0, max_size=200)
_paragraphs = st.lists(st.text(min_size=0, max_size=100), max_size=10)
_metadata = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
    values=st.one_of(st.text(max_size=50), st.integers(), st.floats(allow_nan=False)),
    max_size=5,
)
_datetime = st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2099, 12, 31))

_parsed_document = st.builds(
    ParsedDocument,
    doc_id=st.uuids().map(str),
    filename=st.text(min_size=1, max_size=50),
    file_type=st.sampled_from(["pdf", "docx", "txt", "md"]),
    content=_text,
    paragraphs=_paragraphs,
    metadata=_metadata,
    parsed_at=_datetime,
)


# ---------------------------------------------------------------------------
# Property 14: ParsedDocument 序列化往返
# ---------------------------------------------------------------------------

# Feature: internal-knowledge-base, Property 14: ParsedDocument 序列化往返
@given(_parsed_document)
@settings(max_examples=100)
def test_parsed_document_roundtrip(doc: ParsedDocument):
    """Serializing and deserializing a ParsedDocument yields an equivalent object."""
    serialized = doc.to_json()
    restored = ParsedDocument.from_json(serialized)

    assert restored.doc_id == doc.doc_id
    assert restored.filename == doc.filename
    assert restored.file_type == doc.file_type
    assert restored.content == doc.content
    assert restored.paragraphs == doc.paragraphs
    # datetime precision: ISO 8601 round-trips to microsecond
    assert restored.parsed_at == doc.parsed_at


def test_roundtrip_preserves_empty_content():
    doc = ParsedDocument(
        doc_id="abc",
        filename="test.txt",
        file_type="txt",
        content="",
        paragraphs=[],
        metadata={},
        parsed_at=datetime(2024, 1, 1, 12, 0, 0),
    )
    restored = ParsedDocument.from_json(doc.to_json())
    assert restored.content == ""
    assert restored.paragraphs == []


def test_roundtrip_preserves_unicode():
    doc = ParsedDocument(
        doc_id="xyz",
        filename="中文文档.md",
        file_type="md",
        content="这是一段中文内容 🎉",
        paragraphs=["这是一段中文内容 🎉"],
        metadata={"author": "张三"},
        parsed_at=datetime(2024, 6, 15),
    )
    restored = ParsedDocument.from_json(doc.to_json())
    assert restored.content == doc.content
    assert restored.metadata["author"] == "张三"
