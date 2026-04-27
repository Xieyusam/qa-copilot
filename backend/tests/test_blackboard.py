"""单元测试 - Blackboard 多 Agent 通信机制"""
import pytest
import asyncio
from app.services.agents.blackboard import (
    Blackboard,
    get_agent_query_key,
    get_agent_result_key,
    get_agent_task_key,
)


class TestBlackboard:
    """Blackboard 单元测试"""

    def test_blackboard_write_read(self):
        """测试基本写入和读取"""
        bb = Blackboard(trace_id="test-1")
        bb.write("test:key", "test_value", agent="test")
        assert bb.read("test:key") == "test_value"

    def test_blackboard_read_nonexistent(self):
        """测试读取不存在的 key 返回 None"""
        bb = Blackboard()
        assert bb.read("nonexistent") is None

    def test_blackboard_read_by_pattern(self):
        """测试按模式读取"""
        bb = Blackboard()
        bb.write("search:query", "云测平台", agent="supervisor")
        bb.write("search:result", "结果", agent="search")
        bb.write("translate:query", "翻译", agent="supervisor")

        # 匹配 search:* 的所有 key
        search_keys = bb.read_by_pattern("search:*")
        assert len(search_keys) == 2
        assert search_keys["search:query"] == "云测平台"
        assert search_keys["search:result"] == "结果"

        # 匹配 *:query 的所有 key
        query_keys = bb.read_by_pattern("*:query")
        assert len(query_keys) == 2

    def test_blackboard_to_dict(self):
        """测试转换为可序列化字典"""
        bb = Blackboard(trace_id="test-123")
        bb.write("key1", "value1", agent="test")

        d = bb.to_dict()
        assert d["trace_id"] == "test-123"
        assert d["data"]["key1"] == "value1"
        assert d["messages_count"] == 1

    def test_blackboard_messages_recorded(self):
        """测试消息记录"""
        bb = Blackboard()
        bb.write("key", "value", agent="test_agent")
        bb.read("key")

        messages = bb.get_messages()
        assert len(messages) == 2
        assert messages[0].type == "write"
        assert messages[0].agent == "test_agent"
        assert messages[1].type == "read"

    def test_blackboard_lock_unlock(self):
        """测试锁定功能"""
        bb = Blackboard()
        bb.lock()
        with pytest.raises(RuntimeError, match="locked"):
            bb.write("key", "value", agent="test")
        bb.unlock()
        bb.write("key", "value", agent="test")  # 不应抛出异常

    def test_agent_key_helpers(self):
        """测试 Agent key 辅助函数"""
        assert get_agent_query_key("search") == "search:query"
        assert get_agent_result_key("translate") == "translate:result"
        assert get_agent_task_key("jira") == "jira:task"


class TestBlackboardIntegration:
    """Blackboard 集成测试 - 模拟多 Agent 通信"""

    def test_search_then_translate_workflow(self):
        """模拟 search -> translate 串行工作流"""
        bb = Blackboard(trace_id="workflow-test")

        # Supervisor 设置任务
        bb.write(get_agent_query_key("search"), "查询云测平台", agent="supervisor")
        bb.write(get_agent_task_key("search"), "pending", agent="supervisor")
        bb.write(get_agent_query_key("translate"), "翻译成英文", agent="supervisor")
        bb.write(get_agent_task_key("translate"), "pending", agent="supervisor")

        # Search Agent 执行
        search_query = bb.read(get_agent_query_key("search"))
        assert search_query == "查询云测平台"

        search_result = "云测平台是一个测试平台..."
        bb.write(get_agent_result_key("search"), search_result, agent="search")
        bb.write(get_agent_task_key("search"), "completed", agent="search")

        # Supervisor 传递结果给 Translate
        bb.write(get_agent_result_key("search"), search_result, agent="supervisor")

        # Translate Agent 执行
        translate_query = bb.read(get_agent_query_key("translate"))
        prev_result = bb.read(get_agent_result_key("search"))

        assert translate_query == "翻译成英文"
        assert prev_result == "云测平台是一个测试平台..."

        # Translate 执行
        translate_result = "Cloud Testing Platform is a testing platform..."
        bb.write(get_agent_result_key("translate"), translate_result, agent="translate")
        bb.write(get_agent_task_key("translate"), "completed", agent="translate")

        # 验证最终结果
        assert bb.read(get_agent_result_key("translate")) == "Cloud Testing Platform is a testing platform..."

    def test_multiple_agents_parallel_read(self):
        """模拟多 Agent 并行读取（未来扩展）"""
        bb = Blackboard(trace_id="parallel-test")

        # Supervisor 同时设置多个任务
        bb.write(get_agent_query_key("search"), "查询A", agent="supervisor")
        bb.write(get_agent_query_key("jira"), "查询B", agent="supervisor")
        bb.write(get_agent_query_key("translate"), "翻译C", agent="supervisor")

        # 多个 Agent 可以并行读取自己的任务
        search_query = bb.read(get_agent_query_key("search"))
        jira_query = bb.read(get_agent_query_key("jira"))
        translate_query = bb.read(get_agent_query_key("translate"))

        assert search_query == "查询A"
        assert jira_query == "查询B"
        assert translate_query == "翻译C"

        # 各自写入结果
        bb.write(get_agent_result_key("search"), "结果A", agent="search")
        bb.write(get_agent_result_key("jira"), "结果B", agent="jira")
        bb.write(get_agent_result_key("translate"), "结果C", agent="translate")

        # 验证所有结果都正确写入
        assert bb.read_by_pattern("*:result") == {
            "search:result": "结果A",
            "jira:result": "结果B",
            "translate:result": "结果C",
        }
