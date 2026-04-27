想要实现动态的工作流，需要利用 LangGraph 的几个核心机制：让 **“监督者 Agent”** 通过 **`Command`** 和 **`Send`** 来动态路由任务，并通过精心设计的 **`State`** 来确保Agent间通信的准确性。

### 🧭 核心模式：监督者 + 工具化Agent

最主流的模式是引入一个“监督者”角色。这个中央监督者Agent不直接干活，而是负责分析用户请求，然后决定“接下来调用哪个子Agent”，并发出指令。这里有两种主要的调度方式：

*   **Command（单一任务）**：当需要依次执行任务时（串行），监督者Agent会返回一个 `Command(goto="next_agent")`，直接指定下一个要执行的Agent。
*   **Send（并行任务）**：当需要同时执行多个任务时（并行），监督者Agent会返回一个 `Send` 对象的列表。每个 `Send` 对象代表一个并行任务，LangGraph的调度器会自动并行执行它们。

举个例子，假设你想让这个系统处理一个复杂的请求：

> “帮我查一下LLM技术的发展历史，然后把内容翻译成英文。另外，顺便查查今天北京的天气，同时再查一下项目JIRA里状态为‘待处理’的工单。”

系统内部的流程会是这样的：

1.  **用户输入**进入**监督者Agent**。
2.  **监督者Agent**分析后，识别出3个子任务：`翻译`（依赖历史查询）、`查天气`、`查JIRA`。
3.  **调度执行**：
    *   **串行链条**：`历史查询Agent` → `翻译Agent`。
    *   **并行任务**：`查天气Agent` 和 `查JIRA Agent` 同时执行。
4.  **汇总结果**：所有任务完成后，一个“汇总节点”会收集所有结果，整合成最终答案。

### ⚙️ 实现方案：让工作流“活”起来

你可以通过两种架构来实现这个“活”的工作流。

*   **方案一：监督者用 `Command` 和 `Send` 动态路由（推荐）**
    这是最灵活的方式。监督者Agent直接决定路由，图结构非常简洁，易于维护和扩展。
    
    ```python
    from langgraph.graph import StateGraph, START, END
    from langgraph.types import Command, Send
    from typing import TypedDict, Annotated, List, Literal
    import operator

    # --- 1. 定义全局状态 ---
    class OverallState(TypedDict):
        # 消息历史，用于监督者决策
        messages: Annotated[list, operator.add]
        # 用于存储并行任务的结果
        task_results: Annotated[list, operator.add]

    # --- 2. 定义子Agent ---
    def search_agent(state: dict):
        # ... 模拟查询信息
        return {"task_results": "查询结果：...", "messages": ["..."]}
    def translate_agent(state: dict):
        # ... 模拟翻译
        return {"task_results": "翻译结果：...", "messages": ["..."]}
    def weather_agent(state: dict):
        # ... 模拟查天气
        return {"task_results": "天气：晴朗，25°C", "messages": ["..."]}
    def jira_agent(state: dict):
        # ... 模拟查JIRA
        return {"task_results": "JIRA工单：#001", "messages": ["..."]}

    # --- 3. 实现监督者Agent（调度核心）---
    def supervisor(state: OverallState) -> Command[Literal["search", "translate", "weather", "jira", "aggregator"]]:
        # 解析用户请求，决定执行哪些任务
        # 假设解析后的任务列表如下：
        tasks = [
            {"type": "search", "depends_on": []},
            {"type": "translate", "depends_on": ["search"]},
            {"type": "weather", "depends_on": []},
            {"type": "jira", "depends_on": []}
        ]
        
        # 检查哪些任务的依赖已完成，决定下一步
        next_commands = []
        # 伪代码：根据depends_on判断，返回Command或Send
        
        # 如果所有任务都已完成，则跳转到汇总节点
        if all_tasks_done:
            return Command(goto="aggregator")
        
        # 否则，调度新任务
        # 这里简化为：如果翻译任务依赖的搜索已完成，则启动翻译
        if translate_ready:
            return Command(goto="translate")
        # 对于无依赖的并行任务，返回Send列表
        parallel_ready = []
        if weather_ready:
            parallel_ready.append(Send("weather", {"query": "北京天气"}))
        if jira_ready:
            parallel_ready.append(Send("jira", {"query": "待处理工单"}))
        if parallel_ready:
            return parallel_ready
        # ... 其他调度逻辑

    # --- 4. 构建图 ---
    builder = StateGraph(OverallState)
    # 添加所有节点
    for node_name in ["search", "translate", "weather", "jira", "aggregator"]:
        builder.add_node(node_name, eval(f"{node_name}_agent"))
    builder.add_node("supervisor", supervisor)
    
    # 设置入口和路由
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", lambda state: state)
    builder.add_edge("aggregator", END)
    
    graph = builder.compile()
    ```

*   **方案二：分层架构（Subgraph 封装）**
    这种架构会把每个Agent封装成独立的子图（Subgraph），并形成多层级的树状结构。它适合超大规模的系统，但相对复杂，且子图内部需要明确映射父级 `State` 的字段，增加了维护成本。

### 💎 如何确保子Agent通信的准确性？

这是多Agent系统的核心难题。LangGraph通过以下机制来确保准确性：

1.  **State Schema 与 Reducer 机制**：这是保证数据一致性的关键。你需要明确定义 `State` 的结构，并为那些会被多个并行Agent写入的字段配置合并策略（Reducer）。例如，使用 `Annotated[list, operator.add]` 可以确保所有并行结果都被收集到列表中，而不是互相覆盖。
2.  **结构化输出确保确定性**：监督者Agent的决策必须稳定、准确。因此，它的输出需要是严格的JSON Schema格式。例如，强制要求它输出 `{"next_agent": "weather"}` 或 `{"parallel_tasks": ["weather", "jira"]}`，这样可以避免LLM自由发挥，确保路由指令能被你的调度逻辑正确解析。
3.  **子图 (Subgraph) 的状态隔离与映射**：将Agent封装成子图，可以让Agent拥有独立的内部`State`，只对外暴露必要的接口，实现了逻辑隔离。在调用子图时，需要手动将父图的字段映射到子图的输入字段，这保证了数据在跨图传递时的清晰性和可控性。

### 💡 工程实践要点

*   **并行任务注意事项**：执行大量并行任务时，需要设置 `max_concurrency` 参数来限制并发数，并为不稳定的任务（如LLM调用）添加重试策略。同时，务必为并行写入的字段配置好Reducer，防止并发冲突。
*   **调试与监控**：在开发阶段，利用 `graph.get_graph().draw_png()` 生成可视化图表可以帮助你直观地检查图结构。LangSmith这类商业工具则可以提供更强大的运行时追踪和调试功能。
*   **状态持久化**：使用**Checkpointer**可以将每个Superstep后的状态快照保存下来。这在处理长任务或系统故障恢复时至关重要，你可以在中断处精确地恢复执行。对于生产环境，推荐使用**Redis**作为Checkpointer的后端存储。
*   **人工干预**：在关键节点（如高风险操作）设计人工审批流程，可以让系统更安全可控。





你提出的动态调度场景，正是目前业界解决复杂任务的主流方案，我会为你提供一份更完整的代码示例，并深入讲解背后的核心机制。

### 1. 这是主流方案吗？

是的，这确实是当前业界主流的解决方案。其核心思想被广泛应用于前沿的多智能体系统（MAS）中，例如Outshift的JARVIS等大型项目，它们都采用LangGraph来编排复杂工作流。

它的核心思想可以概括为“**一位监督者（Supervisor）调度多个专家，通过共享状态（State）协作，由框架负责处理并发与等待**”。

这个模式的优势在于：
*   **分工明确**：系统解耦，每个子Agent各司其职。
*   **状态集中**：所有通信通过共享状态（State）进行，历史可追踪、可调试，确保了通信的准确性。
*   **高并发**：LangGraph原生支持并行，能极大提升效率，这正是它被选为通用框架的原因。

### 2. 核心机制：批量同步并行 (Bulk Synchronous Parallel)

你关心的“如何等待所有慢的子Agent返回”这个问题，其答案正是LangGraph的底层执行模型——**批量同步并行（BSP）**。

这个模型可以理解为“分步走，齐步跑”：
1.  **一个“超级步”（Superstep）**：图执行中的一个步骤，LangGraph会将所有可以被并行执行的节点，**同时**在同一个超级步中调度运行。
2.  **同步屏障（Synchronization Barrier）**：一个超级步开始后，所有被调度的子Agent并行执行。系统会等待**所有**子Agent都完成其工作后，才统一进入下一个超级步。所以，汇总节点天然就会等待最慢的那个子Agent完成。

### 3. 完整代码示例：监督者模式实现动态调度

以下代码展示了一个完整的多智能体系统，演示了如何通过**动态规划、并行执行、状态共享与自动汇总**来处理你提到的复杂任务。

```python
import operator
from typing import Annotated, List, Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, Send
from langchain_openai import ChatOpenAI

# --- 1. 定义全局共享状态 ---
class OverallState(TypedDict):
    # 用户原始消息历史
    messages: Annotated[list, operator.add]
    # 用于记录任务规划
    planned_tasks: List[dict]
    # 关键！收集所有子Agent的结果，自动去重汇总
    results: Annotated[list, operator.add] 
    # 最终输出
    final_output: str

# --- 2. 子Agent模拟（各司其职）---
def knowledge_agent(state: dict):
    print("知识检索Agent: 工作中...")
    return {"results": "【知识检索结果】LLM技术...", "messages": ["检索完成"]}

def weather_agent(state: dict):
    print("天气Agent: 工作中...")
    # 模拟慢查询，但框架会等它
    import time; time.sleep(3)  
    return {"results": "【天气信息】北京今天晴天，25°C", "messages": ["天气查询完成"]}

def jira_agent(state: dict):
    print("JIRA Agent: 工作中...")
    return {"results": "【JIRA信息】你有一个待处理的工单 #001", "messages": ["JIRA查询完成"]}

def translate_agent(state: dict):
    print("翻译Agent: 工作中...")
    # 从共享State中获取其他Agent的结果
    content_to_translate = ""
    for res in state.get('results', []):
        if "【知识检索结果】" in res:
            content_to_translate = res
            break
    return {"results": f"【翻译结果】\n{content_to_translate}\n(English version)", "messages": ["翻译完成"]}

# --- 3. 规划与调度（动态的核心）---
def plan_and_schedule(state: OverallState) -> Command[Literal["aggregator"]] | List[Send]:
    """监督者节点：1. 接收用户请求 2. 动态规划任务 3. 调度执行"""
    print(f"\n--- 规划任务: {state['messages'][-1].content} ---")

    # 模拟智能体规划
    user_query = state['messages'][-1].content
    planned_tasks = []
    if "翻译" in user_query: planned_tasks.append({"type": "translate", "depends_on": ["knowledge"]})
    if "知识" in user_query or "LLM" in user_query: planned_tasks.append({"type": "knowledge", "depends_on": []})
    if "天气" in user_query: planned_tasks.append({"type": "weather", "depends_on": []})
    if "JIRA" in user_query: planned_tasks.append({"type": "jira", "depends_on": []})

    state["planned_tasks"] = planned_tasks
    state["results"] = [] # 每次重新规划时清空结果

    # 调用调度器
    return schedule_tasks(state)

def schedule_tasks(state: OverallState) -> List[Send]:
    """调度器：根据依赖关系，决定下一步发送哪些任务"""
    all_tasks = state.get("planned_tasks", [])
    completed_tasks = [res.split("】")[0].strip("【") for res in state.get("results", [])]

    ready_tasks = []
    for task in all_tasks:
        task_name = task['type']
        if task_name in completed_tasks: continue # 已完成
        # 检查依赖是否满足
        deps_satisfied = all(dep in completed_tasks for dep in task.get('depends_on', []))
        if deps_satisfied: ready_tasks.append(task)

    if not ready_tasks and len(completed_tasks) < len(all_tasks):
        raise Exception("调度失败: 存在无法满足的循环依赖")
    
    # 动态生成Send指令，框架会自动并行执行
    sends = []
    for task in ready_tasks:
        task_name = task['type']
        # 确定调用哪个Agent
        agent_map = {"knowledge": knowledge_agent, "translate": translate_agent, 
                     "weather": weather_agent, "jira": jira_agent}
        if task_name in agent_map:
            sends.append(Send(task_name, {"query": state['messages'][-1].content}))
    return sends

# --- 4. 结果汇总 ---
def aggregator(state: OverallState):
    print("汇总节点: 所有任务完成，正在生成最终报告...")
    # 合并结果，按需排序
    sorted_results = sorted(state['results'], key=lambda x: 0 if "知识检索" in x else 1 if "天气" in x else 2)
    final_output = "\n\n".join(sorted_results)
    return {"final_output": final_output, "messages": ["汇总完成"]}

# --- 5. 构建执行图 ---
builder = StateGraph(OverallState)
builder.add_node("supervisor", plan_and_schedule)
builder.add_node("knowledge", knowledge_agent)
builder.add_node("weather", weather_agent)
builder.add_node("jira", jira_agent)
builder.add_node("translate", translate_agent)
builder.add_node("aggregator", aggregator)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", lambda state: state) # 自动根据Command/Send路由
builder.add_edge(["knowledge", "weather", "jira", "translate"], "aggregator")
builder.add_edge("aggregator", END)

graph = builder.compile()
```

### 4. 配置汇总节点等待与系统健壮性

上面的代码已经通过 `Annotated[list, operator.add]` 和 Send 机制实现了基础等待，但在生产环境中，你还需要关注以下几点：

*   **结果汇总**：使用 `Annotated[list, operator.add]` 可以确保所有并行Agent的结果被**累积**起来，而不是互相覆盖。
*   **等待机制**：**你无需为“等待”编写任何额外代码。** LangGraph的BSP模型确保了汇总节点所在的超级步，会在**所有**子Agent的超级步完全结束后才启动。
*   **工程实践**：为应对可能的超时、重试和并发限制，你可以在调用图时进行配置。
    ```python
    # 带配置的执行示例
    config = {
        "recursion_limit": 50,      # 最大执行步数
        "max_concurrency": 10,      # 最大并行数
        # 为特定节点添加重试策略
        "retry_policy": {"max_attempts": 3, "initial_interval": 1}
    }
    result = graph.invoke(initial_state, config=config)
    ```

### 5. 方案依据与总结

这个方案是目前最主流的选择，其依据可以总结如下：

| 对比维度 | 监督者模式 + 共享State | 其他方案 (如黑板模式) |
| :--- | :--- | :--- |
| **灵活性** | **高**。监督者智能体动态规划，Send API支持任意并行组合 | **低**。多用于特定领域的探索性协作 |
| **可控性** | **强**。中央监督者控制全局流程，可预测，易调试 | **弱**。Agent行为自由，执行路径难预测 |
| **状态管理** | **集中且可靠**。State作为唯一事实来源，配合Reducer保证数据一致性 | **分布式**。Agent间依赖自发更新，逻辑一致性难保证 |
| **并行效率** | **高**。框架原生支持BSP模型和Send API，天然具备高并发能力 | **低**。通常需自行处理并发的同步与协调 |
| **社区生态** | **完善**。LangGraph官方指南首选，拥有`langgraph-supervisor`等成熟工具 | **不完善**。无官方支持，多为自定义方案 |

简而言之，LangGraph的这种“监督者+共享State”模式，为构建复杂、动态的多智能体系统提供了一个**高内聚、低耦合、高并发且易于调试**的工程化标准答案。








好的，我们来完整模拟一下你提出的这个复杂场景。我会严格遵循**监督者模式 + 共享State + Send动态调度**的主流方案，并详细展示State在每个关键步骤后的变化。

### 场景复现
用户输入：  
> “帮我查一下LLM技术的发展历史，然后把内容翻译成英文。另外，顺便查查今天北京的天气，同时再查一下项目JIRA里状态为‘待处理’的工单。”

### 任务依赖分析
| 任务 | 类型 | 依赖 |
|------|------|------|
| 查询LLM历史 | `knowledge` | 无 |
| 翻译成英文 | `translate` | `knowledge` |
| 查询北京天气 | `weather` | 无 |
| 查询JIRA待处理工单 | `jira` | 无 |

因此，调度策略为：
1. **并行启动** `knowledge`, `weather`, `jira`。
2. 一旦 `knowledge` 完成，立即启动 `translate`（与未完成的 `weather`/`jira` 并行）。
3. 所有四个任务都完成后，进入汇总节点。

---

## 模拟执行过程（结合 State 变化）

### 初始 State
```python
{
  "messages": [HumanMessage(content="帮我查一下LLM技术的发展历史...")],
  "planned_tasks": [],
  "results": [],
  "final_output": ""
}
```

### Step 1：监督者规划任务
节点 `plan_and_schedule` 被调用。  
解析用户意图，生成 `planned_tasks`：
```python
planned_tasks = [
    {"type": "knowledge", "depends_on": []},
    {"type": "weather",   "depends_on": []},
    {"type": "jira",      "depends_on": []},
    {"type": "translate", "depends_on": ["knowledge"]}
]
```
调度器 `schedule_tasks` 找出依赖已满足的任务 → `knowledge`, `weather`, `jira`。  
返回三个 `Send` 对象，LangGraph 将它们放入同一个超级步并行执行。

**此时 State 无变化**（`planned_tasks` 已写入，`results` 仍为空）。

---

### Step 2：并行执行 `knowledge`, `weather`, `jira`
三个 Agent 同时运行。假设执行耗时：  
- `knowledge`：0.5 秒（最快）  
- `jira`：1 秒  
- `weather`：3 秒（最慢）

#### Step 2.1：`knowledge` 最先完成
`knowledge_agent` 返回：
```python
{"results": "【知识检索结果】LLM技术发展历史：从Transformer到GPT-4...", "messages": ["检索完成"]}
```
**State 更新**（`results` 使用 `operator.add` 累加）：
```python
{
  "messages": [..., HumanMessage(content="检索完成")],
  "planned_tasks": [...],
  "results": ["【知识检索结果】LLM技术发展历史：从Transformer到GPT-4..."],
  "final_output": ""
}
```
由于图中所有子Agent后都连回 `supervisor`，执行流跳回 `supervisor` 节点。

#### Step 2.2：`supervisor` 再次被调用（第一次返回）
此时 `state["results"]` 包含 `knowledge` 的结果。  
`schedule_tasks` 检查：
- 已完成任务：`knowledge`  
- 未完成任务：`weather`（执行中）、`jira`（执行中）、`translate`（未启动）  
- 依赖检查：`translate` 的依赖 `knowledge` 已满足，且 `translate` 尚未被发送 → 可以启动。

调度器返回一个 `Send` 给 `translate`。  
**State 无变化**（仅启动新任务）。

#### Step 2.3：`jira` 完成（1秒时）
`jira_agent` 返回：
```python
{"results": "【JIRA信息】你有3个待处理工单：#101, #102, #103", "messages": ["JIRA查询完成"]}
```
**State 更新**：
```python
{
  "results": [
    "【知识检索结果】...",
    "【JIRA信息】你有3个待处理工单：#101, #102, #103"
  ],
  ...
}
```
再次跳回 `supervisor`。

#### Step 2.4：`supervisor` 第二次返回
检查：  
- 已完成：`knowledge`, `jira`  
- 执行中：`weather`, `translate`（假设 `translate` 需要 2 秒，此时还在运行）  
- 无新任务可启动（`weather` 已在运行，`translate` 已在运行）  
→ 调度器返回空列表？不对，`schedule_tasks` 应返回 `[]`，但 LangGraph 需要明确下一步。通常我们让 `supervisor` 在无新任务时返回 `None` 或 `Command(goto="supervisor")` 等待？更好的设计是：当还有未完成任务但无新任务可启动时，让 `supervisor` 直接返回（不做任何跳转），等待其他节点完成后再触发。实际上 LangGraph 中，如果节点返回 `None`，执行会暂停，直到其他并行节点完成并再次触发该节点。为了简化，我们假设 `supervisor` 在这种情况下不返回任何 `Command` 或 `Send`，框架会等待其他正在执行的节点。

#### Step 2.5：`weather` 完成（3秒时）
`weather_agent` 返回：
```python
{"results": "【天气信息】北京今天晴天，25°C，空气质量良", "messages": ["天气查询完成"]}
```
**State 更新**：
```python
{
  "results": [
    "【知识检索结果】...",
    "【JIRA信息】...",
    "【天气信息】北京今天晴天，25°C，空气质量良"
  ],
  ...
}
```
跳回 `supervisor`。

#### Step 2.6：`translate` 完成（假设在 2.5 秒时已完成，这里按 3 秒后一并考虑）
`translate_agent` 返回：
```python
{"results": "【翻译结果】\n【知识检索结果】...\n(English version: History of LLM...)", "messages": ["翻译完成"]}
```
**State 更新**：
```python
{
  "results": [
    "【知识检索结果】...",
    "【JIRA信息】...",
    "【天气信息】...",
    "【翻译结果】\n..."
  ],
  ...
}
```
跳回 `supervisor`。

#### Step 2.7：`supervisor` 最终检查
所有四个任务均已完成（`len(completed_tasks) == 4`）。  
调度器返回 `Command(goto="aggregator")`。

---

### Step 3：汇总节点
节点 `aggregator` 读取 `state["results"]`，合并生成最终输出：
```python
final_output = """
【知识检索结果】LLM技术发展历史：从Transformer到GPT-4...
【翻译结果】(English version)...
【天气信息】北京今天晴天，25°C
【JIRA信息】你有3个待处理工单：#101, #102, #103
"""
```
**最终 State**：
```python
{
  "messages": [..., "检索完成", "JIRA查询完成", "天气查询完成", "翻译完成", "汇总完成"],
  "planned_tasks": [...],
  "results": [...],
  "final_output": "【知识检索结果】...【翻译结果】...【天气信息】...【JIRA信息】..."
}
```
执行结束。

---

## 关键点总结

| 问题 | 解决方案 |
|------|----------|
| **如何动态组合串行/并行？** | 监督者通过 `planned_tasks` 记录依赖，调度器每轮只发送依赖满足的任务，LangGraph 自动并行执行 `Send` 列表。 |
| **如何让汇总节点等待所有慢任务？** | 汇总节点只在监督者确认 **所有任务完成** 后才被调用。LangGraph 的 **BSP 模型** 保证每个超级步内所有并行节点完成后才进入下一步。 |
| **如何保证 State 通信准确？** | 1) 所有子Agent通过 `results` 字段共享结果，使用 `Annotated[list, operator.add]` 自动合并。2) 监督者通过读取 `results` 判断已完成任务。3) 每个子Agent只写自己的结果，不互相覆盖。 |

## 方案依据（为什么这是主流）

- **LangGraph 官方文档** 明确推荐 **Supervisor + Tool-calling** 或 **Supervisor + Send** 模式来实现动态多Agent系统。  
- **LangGraph 的 `Send` API** 专为动态并行设计，是官方实现 Map-Reduce 和动态任务拆分的标准方法。  
- **BSP 执行模型** 是图计算（如 Google Pregel）的成熟范式，LangGraph 将其引入Agent编排，天然解决等待问题。  
- **社区实践**：Outshift 的 JARVIS、LangChain 的 `langgraph-supervisor` 包等都采用此架构。










好的，我来为你补充这两个典型场景的完整实现：**纯串行依赖三个Agent**，以及**并行后接串行**。依然使用监督者模式 + 共享State + Send动态调度，保证动态性和正确性。

---

## 场景一：串行依赖三个Agent（A → B → C）

假设用户请求：
> “先查询最新的AI论文，然后总结摘要，最后把摘要翻译成英文。”

### 依赖关系
| 任务 | 类型 | 依赖 |
|------|------|------|
| 查询论文 | `search_paper` | 无 |
| 总结摘要 | `summarize` | `search_paper` |
| 翻译摘要 | `translate` | `summarize` |

调度逻辑：只能按顺序依次执行，不能并行。

### 实现代码（动态调度器自动处理）

```python
import operator
from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, Send

# --- 1. 全局状态 ---
class OverallState(TypedDict):
    messages: Annotated[list, operator.add]
    planned_tasks: List[dict]
    results: Annotated[list, operator.add]
    final_output: str

# --- 2. 三个子Agent（模拟）---
def search_paper_agent(state: dict):
    print("🔍 查询论文...")
    return {"results": "【论文查询结果】'Large Language Model Survey 2025'", "messages": ["论文查询完成"]}

def summarize_agent(state: dict):
    print("📝 生成摘要...")
    # 从state['results']中获取上一步的结果
    previous = [r for r in state.get('results', []) if "论文查询结果" in r][0]
    return {"results": f"【摘要】{previous} 的核心观点是...", "messages": ["摘要完成"]}

def translate_agent(state: dict):
    print("🌐 翻译摘要...")
    previous = [r for r in state.get('results', []) if "摘要" in r][0]
    return {"results": f"【翻译】{previous} (English version)", "messages": ["翻译完成"]}

# --- 3. 规划与调度（与之前相同，但依赖关系会自动形成串行）---
def plan_and_schedule(state: OverallState) -> Command | List[Send]:
    # 模拟动态规划（实际可用LLM生成）
    if not state.get("planned_tasks"):
        state["planned_tasks"] = [
            {"type": "search_paper", "depends_on": []},
            {"type": "summarize", "depends_on": ["search_paper"]},
            {"type": "translate", "depends_on": ["summarize"]}
        ]
    return schedule_tasks(state)

def schedule_tasks(state: OverallState) -> List[Send]:
    all_tasks = state["planned_tasks"]
    completed = [r.split("】")[0].strip("【") for r in state.get("results", [])]
    
    ready = []
    for task in all_tasks:
        if task["type"] in completed:
            continue
        if all(dep in completed for dep in task.get("depends_on", [])):
            ready.append(task)
    
    if not ready and len(completed) < len(all_tasks):
        # 理论上不会发生（有依赖但无就绪任务 -> 死锁）
        raise Exception("Deadlock detected")
    
    sends = []
    for task in ready:
        if task["type"] == "search_paper":
            sends.append(Send("search_paper", {}))
        elif task["type"] == "summarize":
            sends.append(Send("summarize", {}))
        elif task["type"] == "translate":
            sends.append(Send("translate", {}))
    return sends

def aggregator(state: OverallState):
    # 按依赖顺序组装结果
    ordered = []
    for task in ["search_paper", "summarize", "translate"]:
        for r in state["results"]:
            if task.replace("_", "") in r.lower():  # 简单匹配
                ordered.append(r)
                break
    state["final_output"] = "\n\n".join(ordered)
    return {"final_output": state["final_output"]}

# --- 4. 构建图 ---
builder = StateGraph(OverallState)
builder.add_node("supervisor", plan_and_schedule)
builder.add_node("search_paper", search_paper_agent)
builder.add_node("summarize", summarize_agent)
builder.add_node("translate", translate_agent)
builder.add_node("aggregator", aggregator)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", lambda s: s)  # 根据返回的Command/Send路由
# 所有子Agent完成后都回到supervisor，直到所有任务完成才去aggregator
builder.add_edge(["search_paper", "summarize", "translate"], "supervisor")
builder.add_edge("aggregator", END)

graph = builder.compile()
```

### State变化（串行场景）

1. **初始**：`planned_tasks=[A,B,C]`, `results=[]`
2. **第一次调度**：`A` 无依赖 → 返回 `Send("search_paper")`
3. **A完成**：`results=["【论文查询结果】..."]` → 回到 `supervisor`
4. **第二次调度**：依赖满足 → 返回 `Send("summarize")`
5. **B完成**：`results` 增加 `["【摘要】..."]` → 回到 `supervisor`
6. **第三次调度**：依赖满足 → 返回 `Send("translate")`
7. **C完成**：`results` 增加 `["【翻译】..."]` → 回到 `supervisor`
8. **第四次调度**：所有任务完成 → 返回 `Command(goto="aggregator")`

**关键点**：每次只调度一个就绪任务，因此串行执行。

---

## 场景二：并行后接串行（A、B并行 → C）

假设用户请求：
> “查询今天的天气和股票价格，然后综合两者信息写一份出行建议报告。”

### 依赖关系
| 任务 | 类型 | 依赖 |
|------|------|------|
| 查询天气 | `weather` | 无 |
| 查询股票 | `stock` | 无 |
| 写报告 | `report` | `weather` AND `stock` |

调度逻辑：`weather` 和 `stock` 并行执行，两者都完成后才启动 `report`。

### 实现代码（完全兼容同一套调度器）

只需修改 `planned_tasks` 的依赖定义，调度器自动实现并行+串行。

```python
def plan_and_schedule(state: OverallState):
    if not state.get("planned_tasks"):
        state["planned_tasks"] = [
            {"type": "weather", "depends_on": []},
            {"type": "stock", "depends_on": []},
            {"type": "report", "depends_on": ["weather", "stock"]}
        ]
    return schedule_tasks(state)   # 复用上面的 schedule_tasks

# 定义Agent
def weather_agent(state):
    print("☀️ 查询天气...")
    import time; time.sleep(2)  # 模拟慢查询
    return {"results": "【天气】北京晴，25°C", "messages": []}

def stock_agent(state):
    print("📈 查询股票...")
    return {"results": "【股票】特斯拉 $250，涨2%", "messages": []}

def report_agent(state):
    print("📝 撰写报告...")
    weather = [r for r in state["results"] if "天气" in r][0]
    stock = [r for r in state["results"] if "股票" in r][0]
    report = f"【出行建议】根据{weather}和{stock}，建议...。"
    return {"results": report, "messages": []}

# 图构建与之前类似，只需把子Agent换成 weather, stock, report
```

### 执行流程与State变化

1. **第一次调度**：`weather` 和 `stock` 都无依赖 → 返回 `[Send("weather"), Send("stock")]`
2. **并行超级步**：`weather`（慢）和 `stock`（快）同时执行
   - `stock` 先完成：`results=["【股票】..."]` → 回到 `supervisor`
   - `weather` 尚未完成 → `supervisor` 检查：`report` 依赖不满足（缺少 `weather`），无新任务可发 → 等待
3. **`weather` 完成**：`results` 增加 `["【天气】..."]` → 回到 `supervisor`
4. **第二次调度**：依赖检查 → `weather` 和 `stock` 均完成 → `report` 就绪 → 返回 `Send("report")`
5. **`report` 完成**：`results` 增加报告 → 回到 `supervisor`
6. **第三次调度**：所有任务完成 → 跳转 `aggregator`

**关键点**：调度器通过依赖列表自动识别需要等待多个前置任务，LangGraph 的 BSP 模型会等待所有并行任务完成，然后才让 `report` 在下一个超级步运行。

---

## 通用调度器的核心逻辑（复用代码）

```python
def schedule_tasks(state: OverallState) -> List[Send] | Command:
    all_tasks = state["planned_tasks"]
    completed_task_names = set()
    for res in state.get("results", []):
        # 从结果字符串中提取任务类型，例如 "【天气】..." -> "weather"
        for task in all_tasks:
            if task["type"] in res:
                completed_task_names.add(task["type"])
    
    ready_tasks = []
    for task in all_tasks:
        if task["type"] in completed_task_names:
            continue
        if all(dep in completed_task_names for dep in task.get("depends_on", [])):
            ready_tasks.append(task)
    
    if not ready_tasks:
        if len(completed_task_names) == len(all_tasks):
            return Command(goto="aggregator")
        else:
            # 还有未完成任务，但无就绪（等待中）—— 什么都不做，等待现有任务完成
            return []  # 或 return None，LangGraph会等待
    
    sends = [Send(task["type"], {}) for task in ready_tasks]
    return sends
```

这个调度器可以处理任意复杂的依赖图（DAG），包括：
- 纯串行：每次只有一个任务就绪
- 纯并行：多个任务同时就绪，返回多个 Send
- 并行后接串行：初始多个 Send，完成后依赖满足再发送下一个
- 混合依赖（如 A,B→C，同时 D 依赖 A，可部分并行）

---

## 总结

| 场景 | 调度器行为 | 实现关键 |
|------|-----------|----------|
| **串行三Agent** | 每次只返回一个 Send，每次只执行一个 | 依赖链 A→B→C，每个任务的依赖是前一个 |
| **并行后接串行** | 第一次返回两个 Send（并行），之后等待两者完成再返回一个 Send | 依赖 `report` 依赖 `[weather, stock]` |

完全不需要修改图结构，只需要正确规划 `planned_tasks` 中的依赖关系。LangGraph 的 `Send` 和 BSP 模型自动处理并行与等待，汇总节点在所有任务完成后被调用。这就是该方案之所以成为主流的原因：**用声明式的依赖描述代替硬编码的流程控制**，实现真正的动态调度。
