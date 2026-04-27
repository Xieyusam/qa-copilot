接下来我需要进行一些功能优化：
1. 我发现对话无法识别符合意图，比如说“帮我总结一下这个文档说了什么，然后翻译成英文”，请调研一下方案，或者用我这个参考方案：

## 场景分析

用户输入：*“帮我查一下xxx资料，然后将这个结果翻译成英文”*

这是一个**顺序依赖型复合意图**：
1. 先执行**查询**（资料检索）
2. 再将查询结果**翻译**成英文

需要设计一个工作流，能够识别这种前后关系并依次执行。

---

## 推荐方案：基于 LangGraph 的“计划-执行”模式

手写 `StateGraph`，设计三个阶段节点：
- **意图解析节点**：将复合意图解析为有序步骤列表
- **循环执行节点**：依次执行每个步骤，支持步骤间数据传递
- **结束节点**

---

## 完整实现代码

### 1. 定义状态结构

```python
from typing import TypedDict, List, Any, Literal
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]       # 原始对话
    user_input: str                   # 当前用户输入
    plan: List[str]                   # 任务计划，如 ["search", "translate"]
    current_step: int                 # 当前执行到第几步
    intermediate_data: dict           # 存储中间结果，如 {"search_result": "..."}
    final_answer: str | None
```

### 2. 意图解析节点（将复合意图拆解为计划）

使用 LLM 结构化输出来生成计划：

```python
from pydantic import BaseModel
from typing import List

class TaskPlan(BaseModel):
    steps: List[str]  # 可取值: "search", "translate", "jira", "log", "qa"...

def plan_node(state: AgentState):
    """将用户输入解析为有序步骤"""
    prompt = f"""
    分析用户需求，给出一个有序的步骤列表。
    可选步骤：search（资料查询）, translate（翻译）, jira（JIRA查询）, log（日志分析）, qa（普通问答）
    只返回步骤列表，不要额外解释。
    用户输入：{state["user_input"]}
    """
    # 方式1: 结构化输出
    llm_with_structure = llm.with_structured_output(TaskPlan)
    plan = llm_with_structure.invoke([HumanMessage(content=prompt)])
    
    # 方式2: 简单关键词匹配（快速但不灵活，示例略）
    
    return {
        "plan": plan.steps,
        "current_step": 0,
        "intermediate_data": {}
    }
```

### 3. 各功能节点实现

```python
def search_node(state: AgentState):
    """资料查询节点"""
    query = state["user_input"]
    # 假设调用 RAG 或搜索引擎
    result = rag_chain.invoke(query)
    return {
        "intermediate_data": {**state["intermediate_data"], "search_result": result}
    }

def translate_node(state: AgentState):
    """翻译节点，依赖 search_result"""
    text_to_translate = state["intermediate_data"].get("search_result", "")
    if not text_to_translate:
        text_to_translate = state["user_input"]  # fallback
    translated = translate_chain.invoke({"text": text_to_translate, "target": "English"})
    return {
        "intermediate_data": {**state["intermediate_data"], "translated": translated},
        "final_answer": translated  # 如果是最后一步，直接设最终答案
    }

def jira_node(state): ...
def log_node(state): ...
```

### 4. 步骤调度器（路由核心）

```python
def step_router(state: AgentState) -> str:
    """根据当前步骤决定下一个节点"""
    plan = state["plan"]
    step_idx = state["current_step"]
    
    if step_idx >= len(plan):
        return "end"
    
    current_action = plan[step_idx]
    return current_action  # 返回节点名称，如 "search"、"translate"

def step_counter(state: AgentState):
    """每执行完一个节点后，步数+1"""
    return {"current_step": state["current_step"] + 1}
```

### 5. 构建图

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(AgentState)

# 添加节点
builder.add_node("planner", plan_node)
builder.add_node("search", search_node)
builder.add_node("translate", translate_node)
builder.add_node("step_counter", step_counter)  # 用于递进步数
# ... 其他节点

# 流程
builder.add_edge(START, "planner")
builder.add_conditional_edges("planner", step_router, {
    "search": "search",
    "translate": "translate",
    "end": END
})

# 每个功能节点执行后，都进入 step_counter 更新步数，再重新路由
builder.add_edge("search", "step_counter")
builder.add_edge("translate", "step_counter")
builder.add_edge("step_counter", "planner")  # 回到 planner 继续路由下一个步骤

graph = builder.compile()
```

---

## 执行流程示例

用户输入：*“查一下 LangGraph 文档，然后翻译成英文”*

1. **planner** → 生成 `plan = ["search", "translate"]`, `current_step=0`
2. **step_router** → 返回 `"search"`，进入 `search_node`
3. **search_node** → 执行查询，结果存入 `intermediate_data["search_result"]`
4. **step_counter** → `current_step=1`
5. **回到 planner** → `step_router` 发现 `current_step=1` 且 `plan[1]="translate"`，进入 `translate_node`
6. **translate_node** → 从 `intermediate_data["search_result"]` 取内容翻译，存入 `final_answer`
7. **step_counter** → `current_step=2`
8. **回到 planner** → `step_router` 发现 `current_step >= len(plan)`，返回 `"end"`，结束

---

## 关键点总结

| 问题 | 解决方案 |
|------|----------|
| 如何识别复合意图？ | 用 LLM 结构化输出将自然语言解析为有序步骤列表 |
| 如何处理步骤间数据依赖？ | 用 `intermediate_data` 字典存储中间结果，后续节点按 key 读取 |
| 如何实现顺序执行？ | 用 `step_counter` + 循环回 `planner` 的方式，每次只执行一个步骤 |
| 需要复杂条件路由吗？ | 不需要，步骤顺序已在 plan 中固定，路由只是按序取步骤名 |
| 是否必须手写 StateGraph？ | 是，`create_agent` 固定为 ReAct 循环，难以实现这种多步骤顺序依赖 |

---

## 扩展：支持并行或条件分支

如果未来需求升级，例如“查资料，如果结果长度>500则翻译，否则直接返回”：

- 在 `step_counter` 后加入条件判断节点，动态修改 `plan` 或 `current_step`。
- 或者为 `translate_node` 增加前置条件：检查 `intermediate_data` 中的长度，决定是否跳过。

这种灵活性只有手写图才能轻松实现。