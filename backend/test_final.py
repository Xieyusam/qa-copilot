"""最终测试 - 串行意图"""
import asyncio
import sys
import os
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app.services.agents.stategraph.graph import build_agent_graph, create_initial_state
from app.services.agents.stategraph.workers.search import SearchWorker
from app.services.agents.stategraph.workers.translate import TranslateWorker
from app.services.agents.kb_tool_registry import KbToolRegistry
from app.services.llm.llm_client import LLMClient
from app.services.agents.intent_detector import IntentDetector
import time


async def test_serial():
    """测试串行意图"""
    print("\n=== 测试串行意图 ===")
    print("输入: 查询一下云测平台简介，然后翻译成英文\n")

    llm = LLMClient()
    kb_registry = KbToolRegistry()
    intent_detector = IntentDetector(llm)

    search_worker = SearchWorker(llm=llm, kb_tool_registry=kb_registry)
    translate_worker = TranslateWorker(llm=llm, kb_tool_registry=kb_registry)

    graph = build_agent_graph(
        intent_detector=intent_detector,
        search_worker=search_worker,
        jira_worker=None,
        log_worker=None,
        translate_worker=translate_worker,
    )

    initial_state = create_initial_state(
        user_input="查询一下云测平台简介，然后翻译成英文",
        intent_detector=intent_detector,
        search_worker=search_worker,
        jira_worker=None,
        log_worker=None,
        translate_worker=translate_worker,
        trace_id="test-final",
    )

    start = time.time()

    async for event in graph.astream(initial_state):
        for node_name, output in event.items():
            if output and isinstance(output, dict):
                if output.get("final_answer"):
                    answer = output["final_answer"]
                    elapsed = time.time() - start
                    print(f"最终结果 ({len(answer)} chars, 耗时: {elapsed:.1f}s):")
                    print(answer[:600] + "..." if len(answer) > 600 else answer)
                    print(f"\n[SUCCESS] 测试通过！")

asyncio.run(test_serial())
