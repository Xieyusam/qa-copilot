"""测试并行意图"""
import asyncio
import sys
import os
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app.services.agents.stategraph.graph import build_agent_graph, create_initial_state
from app.services.agents.stategraph.workers.search import SearchWorker
from app.services.agents.stategraph.workers.jira import JiraWorker
from app.services.agents.stategraph.workers.translate import TranslateWorker
from app.services.agents.kb_tool_registry import KbToolRegistry
from app.services.llm.llm_client import LLMClient
from app.services.integrations.jira_client import JiraClient
from app.services.agents.intent_detector import IntentDetector
import time


async def test_parallel_search_jira():
    """测试并行意图 - search + jira（互不依赖）"""
    print("\n=== 测试并行意图 (search + jira) ===")
    print("输入: 查询云测平台，同时查一下 Jira 项目\n")

    llm = LLMClient()
    kb_registry = KbToolRegistry()
    intent_detector = IntentDetector(llm)
    jira_client = JiraClient()

    search_worker = SearchWorker(llm=llm, kb_tool_registry=kb_registry)
    jira_worker = JiraWorker(llm=llm, jira_client=jira_client)
    translate_worker = TranslateWorker(llm=llm, kb_tool_registry=kb_registry)

    graph = build_agent_graph(
        intent_detector=intent_detector,
        search_worker=search_worker,
        jira_worker=jira_worker,
        log_worker=None,
        translate_worker=translate_worker,
    )

    initial_state = create_initial_state(
        user_input="查询云测平台，同时查一下 Jira 项目",
        intent_detector=intent_detector,
        search_worker=search_worker,
        jira_worker=jira_worker,
        log_worker=None,
        translate_worker=translate_worker,
        trace_id="test-parallel-search-jira",
    )

    start = time.time()

    step = 0
    async for event in graph.astream(initial_state):
        step += 1
        elapsed = time.time() - start
        print(f"\n--- Step {step} (elapsed: {elapsed:.1f}s) ---")
        for node_name, output in event.items():
            if output is None:
                print(f"节点: {node_name} (无输出)")
                continue
            print(f"节点: {node_name}")
            if isinstance(output, dict):
                if output.get("final_answer"):
                    answer = output["final_answer"]
                    print(f"最终结果 ({len(answer)} chars):")
                    print(answer[:600] + "..." if len(answer) > 600 else answer)
                    print(f"\n[SUCCESS] 并行意图测试完成，耗时: {elapsed:.1f}s")
                elif "results" in output and output["results"]:
                    for k, v in output["results"].items():
                        if hasattr(v, 'answer'):
                            print(f"  results[{k}]: {v.answer[:100]}...")

    print("\n总耗时:", time.time() - start, "秒")


async def test_serial_search_translate():
    """测试串行意图 - search + translate（translate 依赖 search）"""
    print("\n" + "="*60)
    print("=== 测试串行意图 (search + translate) ===")
    print("输入: 查询云测平台简介，然后翻译成英文\n")

    llm = LLMClient()
    kb_registry = KbToolRegistry()
    intent_detector = IntentDetector(llm)

    search_worker = SearchWorker(llm=llm, kb_tool_registry=kb_registry)
    jira_worker = JiraWorker(llm=llm, jira_client=JiraClient())
    translate_worker = TranslateWorker(llm=llm, kb_tool_registry=kb_registry)

    graph = build_agent_graph(
        intent_detector=intent_detector,
        search_worker=search_worker,
        jira_worker=jira_worker,
        log_worker=None,
        translate_worker=translate_worker,
    )

    initial_state = create_initial_state(
        user_input="查询云测平台简介，然后翻译成英文",
        intent_detector=intent_detector,
        search_worker=search_worker,
        jira_worker=jira_worker,
        log_worker=None,
        translate_worker=translate_worker,
        trace_id="test-serial",
    )

    start = time.time()

    step = 0
    async for event in graph.astream(initial_state):
        step += 1
        elapsed = time.time() - start
        print(f"\n--- Step {step} (elapsed: {elapsed:.1f}s) ---")
        for node_name, output in event.items():
            if output is None:
                print(f"节点: {node_name} (无输出)")
                continue
            print(f"节点: {node_name}")
            if isinstance(output, dict):
                if output.get("final_answer"):
                    answer = output["final_answer"]
                    print(f"最终结果 ({len(answer)} chars):")
                    print(answer[:600] + "..." if len(answer) > 600 else answer)
                    print(f"\n[SUCCESS] 串行意图测试完成，耗时: {elapsed:.1f}s")
                elif "results" in output and output["results"]:
                    for k, v in output["results"].items():
                        if hasattr(v, 'answer'):
                            print(f"  results[{k}]: {v.answer[:100]}...")

    print("\n总耗时:", time.time() - start, "秒")


async def main():
    await test_serial_search_translate()
    await test_parallel_search_jira()

asyncio.run(main())
