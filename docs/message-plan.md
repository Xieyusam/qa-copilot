针对你的需求：**在对话中支持上传附件，但历史回显时只展示文件上传记录（如文件名、大小），而不展示文件的具体内容**，核心思路是 **将附件的“展示信息”与“内容数据”分离存储**，并在不同场景下使用不同的数据视图。

下面给出一个完整、可落地的方案，基于你现有的 LangGraph + 工具调用聊天机器人架构。

---

## 一、整体设计思路

| 数据角色       | 存储位置                                     | 用途                                       | 前端是否展示内容 |
| -------------- | -------------------------------------------- | ------------------------------------------ | ---------------- |
| **附件元信息** | `HumanMessage.additional_kwargs["attachments"]` | 前端渲染附件卡片（文件名、大小、类型等）   | ✅ 展示          |
| **附件内容**   | 独立存储（文件系统/对象存储 + 向量库/文本）   | 供 LLM 理解、工具处理、检索增强             | ❌ 不展示        |
| **用户文字**   | `HumanMessage.content`                       | 前端展示用户的文字输入                     | ✅ 展示          |

这样前端只看到元信息，而 LLM 可以通过后端注入的内容“看到”附件实际信息。

---

## 二、后端实现方案（基于 LangGraph）

### 1. 定义消息结构（存储与传输）

沿用 LangChain 的 `HumanMessage`，利用 `additional_kwargs` 存放附件元信息：

```python
from langchain_core.messages import HumanMessage

# 用户上传文件后的构造示例
user_text = "请帮我分析这份报告"
attachments_meta = [
    {
        "file_name": "report.pdf",
        "file_size": 125829,   # bytes
        "file_type": "application/pdf",
        "file_id": "uuid-xxxx", # 关联实际文件内容
    }
]

message = HumanMessage(
    content=user_text,
    additional_kwargs={"attachments": attachments_meta}
)
```

### 2. 附件内容处理与注入 LLM

你需要在 LLM 看到完整消息之前，把附件内容（摘要、全文或向量检索结果）补充到对话上下文中。  
推荐使用 **LangGraph 的 `pre_model_hook`**（`create_react_agent` 支持）或自定义图节点。

#### 方法 A：使用 `pre_model_hook`（适用于 `create_react_agent`）

```python
def inject_attachments_hook(state):
    """在调用 LLM 前，把附件内容插入到消息列表中"""
    messages = state["messages"]
    new_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage) and "attachments" in msg.additional_kwargs:
            # 先保留原始 HumanMessage（前端回显用）
            new_messages.append(msg)
            # 为每个附件插入一条辅助消息（SystemMessage 或 ToolMessage）
            for att in msg.additional_kwargs["attachments"]:
                file_content = load_attachment_content(att["file_id"])  # 你的实现
                # 截断或摘要，防止 token 超限
                content_summary = file_content[:2000] + "…"
                helper_msg = SystemMessage(
                    content=f"用户上传了文件 {att['file_name']}，内容如下：\n{content_summary}"
                )
                new_messages.append(helper_msg)
        else:
            new_messages.append(msg)
    return {"messages": new_messages}

# 创建智能体时挂载钩子
agent = create_react_agent(
    model,
    tools,
    pre_model_hook=inject_attachments_hook
)
```

#### 方法 B：手动构建图（更灵活）

如果你需要更精细的控制（如附件内容走 RAG 检索），可手动编写图节点：

```python
from langgraph.graph import StateGraph, MessagesState, START

def process_attachments(state):
    messages = state["messages"]
    # 同上逻辑，返回新的消息列表
    ...

builder = StateGraph(MessagesState)
builder.add_node("attach_processor", process_attachments)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)

builder.add_edge(START, "attach_processor")
builder.add_edge("attach_processor", "agent")
# ... 其余条件边
```

### 3. 附件实际内容的存储与读取

- **存储**：用户上传后，后端接收文件 → 生成唯一 `file_id` → 保存到对象存储（MinIO/S3）或本地磁盘 → 如果需要 LLM 理解，同时提取文本并存入向量库。
- **读取**：`load_attachment_content(file_id)` 返回文本内容（若文件非文本，可用 OCR/语音识别等工具转换）。

---

## 三、前端回显实现

前端获取历史消息列表（通过你的 API），根据消息结构渲染：

```javascript
// 假设消息格式为
{
  "type": "human",
  "content": "请帮我分析这份报告",
  "additional_kwargs": {
    "attachments": [
      { "file_name": "report.pdf", "file_size": 125829, "file_type": "application/pdf" }
    ]
  }
}
```

渲染逻辑（React 示例）：

```jsx
function Message({ msg }) {
  return (
    <div>
      {/* 用户文字内容 */}
      <div>{msg.content}</div>

      {/* 附件列表（仅元信息） */}
      {msg.additional_kwargs?.attachments?.map(att => (
        <div key={att.file_name} className="attachment-card">
          📎 {att.file_name} ({(att.file_size / 1024).toFixed(1)} KB)
          <button onClick={() => downloadFile(att.file_id)}>下载</button>
        </div>
      ))}
    </div>
  );
}
```

> **注意**：如果 LLM 返回的消息中也携带了附件（例如生成的图表），你可以用相同方式处理。

---

## 四、历史对话持久化

将完整的 `HumanMessage`（含 `additional_kwargs`）存入数据库（如 JSON 字段）。加载时直接反序列化，前端渲染时依然只取元信息，不会暴露文件内容。

```sql
-- 示例表结构
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INT,
    role VARCHAR(10),
    content TEXT,
    additional_kwargs JSONB,
    created_at TIMESTAMP
);
```

---

## 五、为什么不直接把文件内容放在 `content` 里？

- 前端会直接渲染 `content`，导致文件全部内容显示在界面上，破坏 UI 且可能泄露隐私。
- LLM 确实需要看到文件内容，但可以通过“旁路”方式注入（如 `SystemMessage`），不污染用户可见区域。
- 分离后，你可以灵活控制给 LLM 的内容长度（摘要/全文/检索片段），而用户始终只看到简洁的附件记录。

---

## 六、注意事项

1. **Token 限制**：大文件内容注入 LLM 前必须截断或做摘要，否则超出上下文窗口。建议配合 RAG 或只注入文件摘要。
2. **并发与性能**：`pre_model_hook` 中读取文件内容可能耗时，可考虑异步预加载或缓存。
3. **消息顺序**：注入的辅助消息应紧跟在原 `HumanMessage` 之后，保持对话逻辑连贯。
4. **兼容性**：确保你的前端能正确处理没有 `attachments` 字段的旧消息。

---

## 总结

- **后端**：`HumanMessage.additional_kwargs["attachments"]` 存元信息，`pre_model_hook` 中根据 `file_id` 加载内容注入 LLM。
- **前端**：根据 `additional_kwargs.attachments` 渲染文件卡片，只显示名称/大小。
- **持久化**：完整存储消息对象，回显时遵循上述渲染规则。

这样既满足了用户“只看上传记录”的 UI 需求，又不影响 LLM 对文件内容的理解能力。