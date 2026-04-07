# QA Copilot 升级 (MVP) 阶段性总结

## 1. 项目概述 (Overview)

本 MVP 阶段的核心目标是将原有的“内部知识库”应用重构并升级为“QA Copilot”智能助手。通过引入多意图路由、混合检索架构以及更智能的文档切分策略，系统不仅提升了对知识库文档的问答准确率，还拓展了日志分析、文本翻译、Jira 查询等多元化辅助能力，前端交互体验也得到了大幅优化。

### 核心功能升级回顾
- **多意图智能路由**：引入 LangGraph 编排工作流，系统能自动识别用户意图并分发至知识库问答、日志分析、翻译或工具调用（如 Jira）等专属节点。
- **混合检索与重排**：在原有的 ChromaDB 向量检索基础上，新增基于 BM25 的倒排索引，并引入 RRF (Reciprocal Rank Fusion) 倒数秩融合算法进行极速重排，大幅提升检索召回率与准确度。
- **智能语义切分优化**：
  - 支持了 Excel (`.xlsx`) 文件的结构化展开解析（表头-行值对）。
  - 针对 Markdown 引入了基于标题层级的语义切分。
  - 针对 TXT/PDF/DOCX 引入了基于递归字符（优先换行符）的智能切分。
- **前端体验进阶**：
  - 实现基于 `AbortController` 的流式响应中断（停止生成）与单条消息重新生成。
  - 引入了增量渲染/防抖 (`throttle`) 策略，解决超长文本输出时的浏览器卡顿问题。
  - 知识溯源可视化：在回答来源中直观展示相似度得分（百分比）。
  - 文档解析状态的实时轮询反馈机制。

### 技术栈扩展
在原有架构基础上，本次升级引入了以下核心技术：
- **AI/LLM 编排**：深度集成 `langgraph>=1.0.0` 实现多节点状态机路由。
- **混合检索**：引入 `rank_bm25` 库实现本地关键词检索融合。
- **文档处理**：引入 `langchain-text-splitters` 处理复杂语义切分；引入 `pandas` 提取并结构化 Excel 数据。
- **前端优化**：原生 Fetch API `AbortController` 结合 `lodash-es` 防抖控制。

---

## 2. 技术架构与数据流 (Architecture & Data Flow)

系统在保留前后端分离架构的基础上，对后端的 Agent 引擎和检索层进行了深度重构。

### 核心模块重构
- **LangGraph Copilot Agent**：取代了单调的链式调用。定义了包含 `intent` 和 `tool_calls` 的 `CopilotState`。`Router Node` 作为中枢，利用 LLM 进行意图分类，后续节点（RAG/Log/Translate/Jira）根据路由结果组装特定的 Prompt 或执行工具，最终通过统一节点流式输出。
- **Hybrid Retrieval Engine**：整合了 `VectorStore` (ChromaDB) 与 `BM25Retriever`。在查询阶段，两者并行召回 Top-N 数据，通过数学 RRF 算法进行交叉重排打分，并附加 `similarity_score` 返回。

### 关键数据流变化

#### 混合检索问答流
1. **意图识别**：用户提问先进入 `Router Node`，识别为 `rag` (知识库问答) 意图。
2. **双路召回**：`HybridRetriever` 同时发起向量检索与 BM25 关键词检索。
3. **RRF 重排**：对双路结果进行去重并根据倒数秩融合算法打分，提取 Top-K 高分片段。
4. **流式生成与中断**：将高分片段注入 Prompt，LLM 开始生成。前端通过 `fetch` 接收 SSE 流，用户可随时触发 `AbortController.abort()` 切断底层连接停止生成。

#### 结构化数据注入流 (以 Excel 为例)
1. **文件上传**：用户上传 `.xlsx`，状态标记为 `parsing`。
2. **结构化展开**：`DocumentParser` 利用 `pandas` 提取每一行，将其与表头拼接成诸如 `[表格: Sheet1]\n列A: 值\n列B: 值` 的独立文本段落，避免了单纯提取文本造成的行列错位。
3. **入库与同步**：生成的 Chunk 分别被计算向量存入 ChromaDB，并同时送入 `BM25Retriever` 构建内存倒排索引。文档状态更新为 `completed`。

---

## 3. 核心设计思路与亮点 (Design Rationale & Highlights)

- **放弃大模型重排，追求极致性能**：在混合检索架构中，放弃了高延迟、高成本的 LLM Reranking 或专用的 Rerank 模型，转而采用纯数学的 **RRF (Reciprocal Rank Fusion)** 算法。这不仅避免了引入新的模型依赖，还在毫秒级延迟下显著提升了长尾词和专有名词的召回质量。
- **面向扩展的 Agent 架构**：通过引入 LangGraph 状态机，系统从“单一的文档问答工具”蜕变为“具备多项技能的 Copilot”。当前加入的 Log、Translate 和 Jira 节点只是起点，未来只需添加新的 Node 并在 Router 中增加枚举，即可无缝扩展新能力。
- **丝滑的降级与容错体验**：在旧版会话的溯源数据缺失或 ChromaDB collection 切换时，系统实现了对旧版 `doc_id` 的宽容处理，并通过 `filename` 进行全局兜底回查，确保用户在点击“下载原文”或查看溯源时不会遭遇 404。
- **性能与体验并重的前端重构**：针对 Markdown 在高频 SSE 推送下造成的 DOM 重绘性能瓶颈，巧妙引入 `lodash-es` 的 `throttle`，将渲染频率控制在 100ms，保证了长文本输出时页面的绝对流畅。

---

## 4. 当前局限与未来改进方向 (Limitations & Future Improvements)

本次 MVP 成功实现了向 QA Copilot 的架构演进，但在面对更深度的业务集成时，仍有优化空间：

### 检索与切分精度的持续演进
- **局限**：目前 BM25 索引是基于内存并在应用启动/文档入库时维护的，对于超大规模文档集可能会带来内存压力；Markdown 标题切分仍可能在超长段落处表现不佳。
- **改进**：
  - 将 BM25 索引持久化或迁移至支持混合检索的专业向量数据库（如 Qdrant 或新版 Milvus）。
  - 引入更智能的基于大模型的 Document Layout Analysis（文档布局分析）进行精准分块。

### 工具调用 (Function Calling) 的深度整合
- **局限**：当前的意图路由属于“硬路由”（基于 Prompt 的单次判断），Jira 节点等工具调用采用的是 Mock 数据，且不支持在一次对话中多步调用不同工具。
- **改进**：利用 OpenAI / 本地大模型的原生 Function Calling 能力，将 LangGraph 升级为标准的 ReAct 范式，允许 Agent 自主决定何时调用工具、何时检索知识库，甚至进行多步推理。

### 系统运维与可观测性
- **局限**：在 LangGraph 节点中追踪每一次多意图路由的 Prompt 表现与耗时不够直观。
- **改进**：
  - 在 LangGraph 节点中全面接入 LangSmith。
  - **(已解决)** 之前排查偶尔出现的“端口幽灵监听”依赖手工脚本，且存在跨平台兼容性问题。本次已引入 Docker Compose 进行全容器化部署 (`docker-compose.yml` 及双端 `Dockerfile`)，彻底解决了开发环境一致性与系统网络栈残留问题，并补充了 Mac/Linux 专用的 `dev.sh`。
