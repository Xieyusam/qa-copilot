# 内部知识库 (MVP) 阶段性总结

## 1. 项目概述 (Overview)

本 MVP 的核心目标是构建一个基于 RAG（检索增强生成）架构的内部知识库应用。通过该系统，内部员工能够轻松上传办公文档，并通过自然语言与知识库进行智能问答，极大提升了信息检索和知识沉淀的效率。

### 核心功能回顾
- **文档管理**：支持用户上传、列表查看和删除 PDF、DOCX、TXT 和 Markdown 格式的文件。
- **智能处理**：系统后台自动对上传的文档进行解析、结构化处理、文本切分（Chunking）并完成向量化索引。
- **智能问答**：用户可以通过自然语言提问，系统利用检索到的相关文档片段和 LLM 生成准确回答。
- **上下文记忆**：具备多轮对话能力，系统自动维护会话级别的上下文记忆（Session Context）。

### 技术栈汇总
- **前端**：Vue 3 + TypeScript + Vite + Tailwind CSS
- **后端**：Python + FastAPI (提供 RESTful API 与 SSE 流式接口)
- **数据库/存储**：
  - 向量数据库：ChromaDB（本地持久化）
  - 元数据存储：SQLite (通过 SQLAlchemy ORM 管理)
  - 文件存储：本地磁盘
- **AI/LLM 框架**：LangChain + LangGraph（支持 Embedder、LLM 调用与 RAG 流程编排）
- **解析库**：PyMuPDF (PDF)、python-docx (DOCX)

---

## 2. 技术架构与数据流 (Architecture & Data Flow)

系统采用了典型的前后端分离设计，后端服务充当 RAG 引擎的协调者。

### 核心模块划分
- **文档处理管线 (Document Pipeline)**：由 `Document_Uploader`、`Document_Parser`、`Chunker` 和 `Embedder` 组成，负责将非结构化文档转化为向量知识。
- **对话推理服务 (Chat Inference)**：由 `Retriever`、`Conversation_Manager` 和 `LLM_Client` 组成，负责处理用户查询并生成响应。

### 关键数据流

#### 数据注入流 (Data Ingestion Flow)
1. **文件上传**：用户上传文件，后端进行格式和大小校验（最大 50MB）。
2. **持久化**：原始文件保存至本地磁盘，元数据（状态为处理中）写入 SQLite。
3. **异步解析**：触发后台任务，`Document_Parser` 提取纯文本内容，保留基本段落结构。
4. **切分与向量化**：`Chunker` 按照 512 Tokens 大小和 50 Tokens 重叠率对文本进行滑动窗口切分；`Embedder` 将 Chunk 转化为向量。
5. **入库**：带有原文引用的 Chunk 向量数据存入 ChromaDB，更新 SQLite 中文档状态为已完成。

#### 检索问答流 (Retrieval & Generation Flow)
1. **查询接收**：用户发起提问，`Conversation_Manager` 关联当前 Session。
2. **向量检索**：问题经过 `Embedder` 向量化后，`Retriever` 在 ChromaDB 中召回最相关的 Top-5 Chunks。
3. **上下文拼装**：提取最近 10 轮历史对话记录，连同召回的 Chunks 一同组合为 Prompt 模板。
4. **流式生成**：`LLM_Client` 调用大模型 API 生成回答，并通过 SSE（Server-Sent Events）将回答字符流式推送至前端。

---

## 3. 核心设计思路与亮点 (Design Rationale & Highlights)

- **高度解耦与可测试性**：将 `Document_Parser`、`Chunker` 和 `Embedder` 设计为独立的 Service 类。这种高内聚低耦合的设计使得未来更换解析引擎（例如引入 OCR）或切换 Embedding 模型变得极其简单。
- **严谨的生命周期一致性**：在文档删除逻辑中，系统保证了原始文件、SQLite 元数据记录以及 ChromaDB 向量数据的**原子性级联删除**，避免了“幽灵索引”导致的回答错乱。
- **健壮的容错与状态管理**：文档解析过程是异步且容错的。即使某份异常文档导致解析崩溃，系统也会捕获异常，记录错误日志，并将该文档状态明确标记为“解析失败”，不影响其他任务执行。
- **属性测试驱动开发**：在核心模块中引入了往返测试（Round-trip Testing）。例如 `ParsedDocument` 的 JSON 序列化与反序列化测试，以及解析器的幂等性验证，从根本上保证了数据在各个流转环节不丢失、不变异。

---

## 4. 当前局限与未来改进方向 (Limitations & Future Improvements)

本阶段已成功验证了内部知识库的最小可行性，但在面向更复杂的企业级场景时，仍有以下改进空间：

### 解析与提取能力增强
- **局限**：当前对于包含复杂表格、双栏排版、甚至大量图片的 PDF 解析效果一般。
- **改进**：引入多模态大模型解析（如 GPT-4V 或专用 Document AI 服务），以及增加 OCR 组件以提取扫描版文档信息。

### 切分与检索策略优化
- **局限**：采用固定 Token 滑动窗口切分可能截断完整的语义段落；单一向量检索在面对“特定名词匹配”时容易召回失败。
- **改进**：
  - **语义切分**：基于 Markdown 标题、换行符或 AST 树进行更智能的 Semantic Chunking。
  - **混合检索 (Hybrid Search)**：引入 BM25 等传统倒排索引，结合向量检索，并增加 Reranking（重排）机制以提升 Top-K 召回准确率。

### 权限与多租户隔离
- **局限**：当前所有用户共享一个全局知识库池，缺乏权限管控。
- **改进**：设计 Workspace（工作空间）和 RBAC 权限模型。在向量查询时增加基于 User ID 或 Workspace ID 的 Metadata 过滤（Metadata Filtering），确保数据安全隔离。

### 性能与可观测性
- **局限**：单机 ChromaDB 和本地磁盘存储难以应对海量高并发请求。
- **改进**：考虑接入云端向量数据库（如 Pinecone 或 Milvus），并将文件存储迁移至 OSS/S3。增加 LangSmith 等可观测性工具，监控 Token 消耗与回答质量。