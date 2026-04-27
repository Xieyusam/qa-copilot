"""智能并行支持 - 修改 state.py, graph.py, supervisor_node.py"""
import os

# 1. 修改 state.py - results 通道支持并发写入
state_content = open('app/services/agents/stategraph/state.py', 'r', encoding='utf-8').read()

if 'Annotated' not in state_content:
    # 添加 Annotated 和合并函数
    old_import = "from typing import TypedDict, Optional, Any"
    new_import = """from typing import TypedDict, Optional, Any
from typing_extensions import Annotated"""

    old_results = "    results: dict[str, AgentResult]"
    new_results = """    # 使用 Annotated + 自定义合并函数，支持并行节点并发写入
    results: Annotated[dict[str, AgentResult], _merge_dicts]"""

    state_content = state_content.replace(old_import, new_import)
    state_content = state_content.replace(old_results, new_results)

    # 在 AgentState 类之前添加合并函数
    old_class_def = "class AgentState(MessagesState):"
    merge_func = """def _merge_dicts(d1: dict, d2: dict) -> dict:
    \"\"\"合并两个字典，用于 Annotated 通道\"\"\"
    return {**d1, **d2}


"""
    state_content = state_content.replace(old_class_def, merge_func + old_class_def)

    open('app/services/agents/stategraph/state.py', 'w', encoding='utf-8').write(state_content)
    print("Fixed state.py")
else:
    print("state.py already has Annotated support")


# 2. 修改 graph.py - 支持 Send 并行
graph_content = open('app/services/agents/stategraph/graph.py', 'r', encoding='utf-8').read()

# 添加 Send 导入
if 'from langgraph.constants import Send' not in graph_content:
    old_import = "from typing import Dict"
    new_import = "from typing import Dict, List\nfrom langgraph.constants import Send"
    graph_content = graph_content.replace(old_import, new_import)
    print("Added Send import to graph.py")

# 修改 route_from_supervisor 支持并行
old_route = '''def route_from_supervisor(state: AgentState) -> str:
    """条件边路由"""
    next_node = state.get("next_node", "aggregate")
    logger.info(f"route_from_supervisor: {next_node}")
    return next_node'''

new_route = '''def route_from_supervisor(state: AgentState) -> str | List[Send]:
    """
    条件边路由 - 支持并行和串行

    返回：
    - str: 单个节点名称（串行执行）
    - List[Send]: 多个 Send 对象（并行执行）
    """
    from langgraph.constants import Send

    next_node = state.get("next_node", "aggregate")
    pending_agents = state.get("pending_agents", [])

    # 如果有待执行的多个 agent 且可以并行
    if len(pending_agents) > 1:
        can_parallel = state.get("context", {}).get("can_parallel", [])
        # 找出所有可以并行的 agent
        parallel_agents = [a for a in pending_agents if a in can_parallel]

        if len(parallel_agents) > 1:
            logger.info(f"route_from_supervisor: 并行执行 {parallel_agents}")
            # 每个 Send 只传递自己需要的 state
            def make_send(agent):
                return Send(agent, {
                    "pending_agents": [agent],
                    "results": state.get("results", {}),
                    "context": state.get("context", {}),
                    "blackboard": state.get("blackboard"),
                    "trace_id": state.get("trace_id"),
                    "user_input": state.get("user_input"),
                })
            return [make_send(agent) for agent in parallel_agents]
        elif len(pending_agents) == 1:
            # 只有一个，可以串行执行
            pass
        else:
            # 不能并行，串行执行第一个
            pass

    logger.info(f"route_from_supervisor: {next_node}")
    return next_node'''

graph_content = graph_content.replace(old_route, new_route)
open('app/services/agents/stategraph/graph.py', 'w', encoding='utf-8').write(graph_content)
print("Fixed graph.py")


# 3. 修改 supervisor_node.py - 判断依赖关系
supervisor_content = open('app/services/agents/stategraph/nodes/supervisor_node.py', 'r', encoding='utf-8').read()

# 需要添加的依赖判断逻辑
# 在检测多意图后，添加 can_parallel 判断

old_detect = '''    # 4. 多意图：第一个执行，其余加入 pending
    if len(agents_to_execute) > 1:
        first_agent = agents_to_execute[0]
        remaining = agents_to_execute[1:]
        logger.info(f"supervisor_node: 多意图检测到 {agents_to_execute}, 执行={first_agent}, pending={remaining}")

        return {
            "next_node": first_agent,
            "pending_agents": remaining,
            "context": {
                "intent_chain": agents_to_execute,
            }
        }'''

new_detect = '''    # 4. 多意图：判断依赖关系，决定并行还是串行
    if len(agents_to_execute) > 1:
        logger.info(f"supervisor_node: 多意图检测到 {agents_to_execute}")

        # 判断哪些 agent 可以并行（没有依赖的）
        can_parallel = []
        serial_agents = []

        for i, agent in enumerate(agents_to_execute):
            if i == 0:
                # 第一个 agent 一定可以执行
                can_parallel.append(agent)
            elif _agent_depends_on_previous(agent, agents_to_execute[:i]):
                # 这个 agent 依赖前一个的结果，需要串行
                serial_agents.append(agent)
            else:
                # 这个 agent 不依赖前一个，可以并行
                can_parallel.append(agent)

        logger.info(f"supervisor_node: can_parallel={can_parallel}, serial={serial_agents}")

        # 构建 pending 队列：第一个 + 串行的 + 并行的
        all_pending = []
        executed = []

        if can_parallel:
            first_agent = can_parallel[0]
            remaining_parallel = can_parallel[1:]
            all_pending = [first_agent] + serial_agents + remaining_parallel
        else:
            all_pending = serial_agents

        # 返回第一个执行，其余加入 pending
        return {
            "next_node": all_pending[0] if all_pending else agents_to_execute[0],
            "pending_agents": all_pending[1:] if len(all_pending) > 1 else [],
            "context": {
                "intent_chain": agents_to_execute,
                "can_parallel": can_parallel,
            }
        }'''

if old_detect in supervisor_content:
    supervisor_content = supervisor_content.replace(old_detect, new_detect)
    print("Fixed supervisor_node.py - intent detection")
else:
    print("supervisor_node.py intent detection pattern not found")

# 添加依赖判断函数（在文件开头）
helper_func = '''
def _agent_depends_on_previous(agent: str, previous_agents: list) -> bool:
    """
    判断 agent 是否依赖前一个 agent 的结果

    translate 依赖前一个 agent 的结果（需要前一个的结果作为待翻译文本）
    其他 agent 不依赖
    """
    if agent == "translate" and previous_agents:
        # translate 需要前一个的结果
        prev = previous_agents[-1]
        if prev in ["search", "jira", "log", "summarize"]:
            return True
    return False

'''

# 在 supervisor_node 函数之前添加
old_func_def = '''async def supervisor_node(state: AgentState) -> Dict:'''
new_func_def = helper_func + old_func_def

supervisor_content = supervisor_content.replace(old_func_def, new_func_def)

open('app/services/agents/stategraph/nodes/supervisor_node.py', 'w', encoding='utf-8').write(supervisor_content)
print("Fixed supervisor_node.py - added helper function")


print("\\nAll fixes applied!")
print("Note: graph.py may have a typo - please verify 'utf-8' is correct")
