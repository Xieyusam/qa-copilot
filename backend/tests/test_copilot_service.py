import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.copilot_service import CopilotService
from app.services.vector_store import ChunkResult

def _chunk(**kwargs):
    default = {
        "chunk_id": "c1",
        "doc_id": "d1",
        "filename": "f.txt",
        "content": "abc",
        "position": 0,
        "score": 0.9,
    }
    default.update(kwargs)
    return ChunkResult(**default)

@pytest.mark.asyncio
async def test_copilot_instantiation():
    retriever = MagicMock()
    conv = MagicMock()
    llm = MagicMock()
    jira = MagicMock()
    service = CopilotService(retriever, conv, llm, jira)
    assert service is not None
