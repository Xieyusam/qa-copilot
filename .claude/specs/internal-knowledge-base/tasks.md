# 实现计划：内部知识库

## 概述

基于 RAG 架构的内部知识库应用，前端 Vue3 + TypeScript，后端 Python + FastAPI，向量存储 ChromaDB，元数据存储 SQLite。实现文档上传、解析向量化、智能问答和多轮对话四大核心功能。

## 任务

- [x] 1. 搭建项目结构与基础配置
  - 创建后端目录结构：`backend/app/{api,core,models,services,db}/`
  - 创建前端目录结构：`frontend/src/{components,stores,api,types}/`
  - 配置后端 `pyproject.toml`（依赖：fastapi, uvicorn, sqlalchemy, chromadb, pymupdf, python-docx, sentence-transformers, hypothesis）
  - 配置前端 `package.json`（依赖：vue3, vite, pinia, typescript）
  - 创建 `backend/app/config.py`，读取环境变量（LLM API URL/Key、ChromaDB 路径、SQLite 路径、文件存储路径）
  - _需求：1.1, 2.1_

- [x] 2. 实现数据模型与数据库初始化
  - [x] 2.1 实现 SQLAlchemy Document 模型与数据库初始化
    - 在 `backend/app/models/document.py` 中定义 `Document` ORM 模型（id, filename, file_type, file_size, status, error_msg, uploaded_at, processed_at）
    - 在 `backend/app/db/session.py` 中配置 SQLite 引擎和 SessionLocal
    - 在 `backend/app/db/init_db.py` 中实现 `create_tables()` 函数
    - _需求：1.6, 2.1_

  - [x] 2.2 实现 ParsedDocument、Chunk、Session、Message 数据类
    - 在 `backend/app/core/schemas.py` 中定义 `ParsedDocument`、`Chunk`、`Message`、`SourceRef`、`Session` dataclass
    - 为 `ParsedDocument` 实现 `to_json()` 和 `from_json()` 方法，datetime 序列化为 ISO 8601
    - _需求：5.1, 5.2_

  - [x]* 2.3 为 ParsedDocument 编写属性测试（Property 14）
    - **Property 14: ParsedDocument 序列化往返**
    - **Validates: Requirements 5.2**

- [x] 3. 实现文档解析模块（Document_Parser）
  - [x] 3.1 实现 DocumentParser 类
    - 在 `backend/app/services/parser.py` 中实现 `DocumentParser.parse(file_path, file_type) -> ParsedDocument`
    - PDF 解析使用 PyMuPDF（`fitz`），提取文本和段落
    - DOCX 解析使用 `python-docx`，提取段落列表
    - TXT/Markdown 直接读取，按换行符切分段落
    - 空文件输入返回包含空 content 和空 paragraphs 的 ParsedDocument，不抛出异常
    - 解析失败时捕获异常，返回带 error 标记的结果（不抛出未捕获异常）
    - _需求：2.1, 2.4, 2.5, 5.1, 5.4_

  - [x]* 3.2 为 DocumentParser 编写属性测试（Property 4）
    - **Property 4: 解析输出完整性**
    - **Validates: Requirements 2.1, 2.5, 5.1**

  - [x]* 3.3 为 DocumentParser 编写属性测试（Property 7）
    - **Property 7: 解析错误状态标记**
    - **Validates: Requirements 2.4**

  - [x]* 3.4 为 DocumentParser 编写属性测试（Property 15）
    - **Property 15: 解析幂等性**
    - **Validates: Requirements 5.3**

  - [x]* 3.5 为 DocumentParser 编写单元测试
    - 测试空文件输入返回空 ParsedDocument 而非异常（需求 5.4 边界条件）
    - 测试各格式典型文件的解析示例（PDF/DOCX/TXT/MD）
    - _需求：2.5, 5.4_

- [x] 4. 实现文本切分模块（Chunker）
  - [x] 4.1 实现 Chunker 类
    - 在 `backend/app/services/chunker.py` 中实现 `Chunker.chunk(doc, max_tokens=512, overlap=50) -> list[Chunk]`
    - 使用 tiktoken 或简单空格分词计算 token 数量
    - 按 max_tokens 滑动窗口切分，相邻 Chunk 保留 overlap 个 token 的重叠
    - 每个 Chunk 记录 chunk_id、doc_id、content、token_count、position
    - _需求：2.2_

  - [x]* 4.2 为 Chunker 编写属性测试（Property 5）
    - **Property 5: Chunk 大小约束**
    - **Validates: Requirements 2.2**

- [x] 5. 实现向量化与向量存储模块（Embedder + Vector_Store）
  - [x] 5.1 实现 Embedder 类
    - 在 `backend/app/services/embedder.py` 中实现 `Embedder.embed(texts: list[str]) -> list[list[float]]`
    - 支持两种后端：sentence-transformers（本地）和 OpenAI Embeddings API（通过配置切换）
    - _需求：2.3_

  - [x] 5.2 实现 VectorStore 封装类（基于 ChromaDB）
    - 在 `backend/app/services/vector_store.py` 中封装 ChromaDB 客户端
    - 实现 `add_chunks(chunks, embeddings)`、`query(query_embedding, top_k) -> list[ChunkResult]`、`delete_by_doc_id(doc_id)` 方法
    - _需求：2.3, 2.6, 1.7_

  - [x]* 5.3 为向量化存储编写属性测试（Property 6）
    - **Property 6: 向量化存储往返**
    - **Validates: Requirements 2.3**

- [x] 6. 实现文档上传与管理服务
  - [x] 6.1 实现 DocumentUploader 服务
    - 在 `backend/app/services/uploader.py` 中实现文件格式校验（仅接受 pdf/docx/txt/md）
    - 实现文件大小校验（超过 50MB 拒绝）
    - 实现文件保存到本地磁盘，元数据写入 SQLite
    - 实现异步文档处理流程：调用 Parser → Chunker → Embedder → VectorStore，更新文档状态
    - 实现文档删除：同时删除原始文件、SQLite 元数据、ChromaDB 向量数据
    - _需求：1.2, 1.3, 1.4, 1.7, 2.1, 2.2, 2.3, 2.4, 2.6_

  - [x]* 6.2 为文件格式校验编写属性测试（Property 1）
    - **Property 1: 文件格式校验完备性**
    - **Validates: Requirements 1.2, 1.3**

  - [x]* 6.3 为删除一致性编写属性测试（Property 3）
    - **Property 3: 删除一致性**
    - **Validates: Requirements 1.7, 2.6**

  - [x]* 6.4 为文档上传编写单元测试
    - 测试文件大小超过 50MB 时被拒绝（需求 1.4 边界条件）
    - _需求：1.4_

- [x] 7. 实现文档管理 API（/api/documents）
  - [x] 7.1 实现文档 API 路由
    - 在 `backend/app/api/documents.py` 中实现：
      - `POST /api/documents/upload`：接收文件，调用 DocumentUploader，返回文档 ID 和初始状态
      - `GET /api/documents`：查询 SQLite 返回文档列表（含 filename、uploadedAt、status）
      - `DELETE /api/documents/{doc_id}`：调用删除服务，返回 204
      - `GET /api/documents/{doc_id}/status`：返回文档当前处理状态
    - _需求：1.1, 1.5, 1.6, 1.7_

  - [x]* 7.2 为文档列表接口编写属性测试（Property 2）
    - **Property 2: 文档列表字段完整性**
    - **Validates: Requirements 1.6**

- [x] 8. 检查点 - 后端文档模块
  - 确保所有测试通过，如有疑问请向用户确认。

- [x] 9. 实现检索模块（Retriever）
  - [x] 9.1 实现 Retriever 类
    - 在 `backend/app/services/retriever.py` 中实现 `Retriever.retrieve(query, top_k=5) -> list[ChunkResult]`
    - 将查询文本向量化，调用 VectorStore 检索 Top-K Chunks
    - 当所有结果相似度低于阈值时，返回空列表（触发"未找到相关内容"逻辑）
    - _需求：3.1, 3.4_

- [x] 10. 实现对话管理模块（Conversation_Manager）
  - [x] 10.1 实现 ConversationManager 类
    - 在 `backend/app/services/conversation.py` 中实现内存存储的 Session 管理
    - 实现 `get_session`、`add_message`、`clear_history`、`get_recent_history(n=10)` 方法
    - 实现 Session 超时机制（30 分钟无活动自动清除历史）
    - _需求：4.1, 4.2, 4.3, 4.4, 4.5_

  - [x]* 10.2 为 Session 隔离性编写属性测试（Property 11）
    - **Property 11: Session 隔离性**
    - **Validates: Requirements 4.1**

  - [x]* 10.3 为 Session 生命周期编写属性测试（Property 12）
    - **Property 12: Session 生命周期**
    - **Validates: Requirements 4.3, 4.5**

  - [x]* 10.4 为清除历史编写属性测试（Property 13）
    - **Property 13: 清除历史往返**
    - **Validates: Requirements 4.4**

- [x] 11. 实现 LLM 客户端与 RAG 问答服务
  - [x] 11.1 实现 LLMClient 类
    - 在 `backend/app/services/llm_client.py` 中实现 `LLMClient.stream_chat(prompt) -> Iterator[str]`
    - 调用 OpenAI 兼容接口，启用流式输出（stream=True）
    - 实现重试机制（最多 3 次，指数退避），超时 30 秒
    - _需求：3.2, 3.6_

  - [x] 11.2 实现 RAG 问答服务
    - 在 `backend/app/services/rag.py` 中实现 `RAGService.answer(session_id, question) -> AsyncIterator[str]`
    - 构造 Prompt：最近 10 轮历史 + 检索到的 Chunks（≤5 个）+ 当前问题
    - 当检索结果为空时，返回"未找到相关内容"提示
    - 在响应中附加 sources 字段（文档名称 + chunk_position）
    - _需求：3.1, 3.2, 3.3, 3.4, 4.2_

  - [x]* 11.3 为 RAG Prompt 构造编写属性测试（Property 8）
    - **Property 8: RAG Prompt 构造完整性**
    - **Validates: Requirements 3.1, 3.2, 4.2**

  - [x]* 11.4 为回答来源引用编写属性测试（Property 9）
    - **Property 9: 回答来源引用**
    - **Validates: Requirements 3.3**

  - [x]* 11.5 为空知识库场景编写单元测试
    - 测试知识库为空时返回"未找到相关内容"提示（需求 3.4 边界条件）
    - _需求：3.4_

- [x] 12. 实现对话 API（/api/chat）
  - [x] 12.1 实现对话 API 路由
    - 在 `backend/app/api/chat.py` 中实现：
      - `POST /api/chat/sessions`：创建新 Session，返回 session_id
      - `POST /api/chat/sessions/{session_id}/messages`：调用 RAGService，以 SSE 格式流式返回回答（Content-Type: text/event-stream）
      - `DELETE /api/chat/sessions/{session_id}/history`：清除对话历史
      - `GET /api/chat/sessions/{session_id}/messages`：返回历史消息列表
    - _需求：3.5, 3.6, 4.4, 4.6_

  - [x]* 12.2 为流式输出格式编写属性测试（Property 10）
    - **Property 10: 流式输出格式**
    - **Validates: Requirements 3.6**

  - [x]* 12.3 为历史记录接口编写单元测试
    - 测试 Session 历史接口返回正确格式的消息列表（需求 4.6）
    - _需求：4.6_

- [x] 13. 注册路由并完成后端主入口
  - 在 `backend/app/main.py` 中创建 FastAPI 应用，注册 `/api/documents` 和 `/api/chat` 路由
  - 配置 CORS（允许前端开发服务器跨域）
  - 在应用启动时调用 `create_tables()` 初始化数据库
  - _需求：1.1, 3.5_

- [x] 14. 检查点 - 后端完整性
  - 确保所有测试通过，如有疑问请向用户确认。

- [x] 15. 实现前端 API 层与类型定义
  - [x] 15.1 定义前端 TypeScript 类型
    - 在 `frontend/src/types/index.ts` 中定义 `Document`、`Message`、`SourceRef` 接口
    - _需求：1.6, 3.3, 4.6_

  - [x] 15.2 实现文档 API 调用模块
    - 在 `frontend/src/api/documents.ts` 中实现 `uploadDocument`、`listDocuments`、`deleteDocument`、`getDocumentStatus` 函数
    - _需求：1.1, 1.5, 1.6, 1.7_

  - [x] 15.3 实现对话 API 调用模块（含 SSE）
    - 在 `frontend/src/api/chat.ts` 中实现 `createSession`、`sendMessage`（使用 EventSource 或 fetch + ReadableStream 处理 SSE）、`clearHistory`、`getMessages` 函数
    - _需求：3.5, 3.6, 4.4, 4.6_

- [x] 16. 实现前端 Pinia 状态管理
  - [x] 16.1 实现文档状态 Store
    - 在 `frontend/src/stores/documents.ts` 中实现 `useDocumentStore`（documents 列表、上传状态、轮询文档处理状态）
    - _需求：1.5, 1.6_

  - [x] 16.2 实现对话状态 Store
    - 在 `frontend/src/stores/chat.ts` 中实现 `useChatStore`（sessionId、messages 列表、流式接收状态）
    - _需求：3.5, 4.6_

- [x] 17. 实现前端核心组件
  - [x] 17.1 实现 DocumentUpload.vue 组件
    - 文件选择（限制格式 pdf/docx/txt/md）、上传进度展示、上传后状态反馈
    - 调用 `useDocumentStore` 触发上传
    - _需求：1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 17.2 实现 DocumentList.vue 组件
    - 展示文档列表（文档名称、上传时间、处理状态）
    - 支持删除操作，删除后刷新列表
    - _需求：1.6, 1.7_

  - [x] 17.3 实现 MessageBubble.vue 组件
    - 渲染单条消息气泡（user/assistant 样式区分）
    - assistant 消息展示 sources 引用（文档名称 + 片段位置）
    - _需求：3.3_

  - [x] 17.4 实现 ChatInterface.vue 组件
    - 消息列表展示（使用 MessageBubble）、输入框、发送按钮
    - 发送后立即展示"正在思考"状态，流式接收并逐步渲染回答内容
    - 支持清除对话历史按钮
    - _需求：3.5, 3.6, 4.4, 4.6_

  - [x]* 17.5 为上传入口编写单元测试
    - 测试上传入口在前端页面中存在（需求 1.1）
    - _需求：1.1_

- [x] 18. 组装前端 App 入口
  - 在 `frontend/src/App.vue` 中组合 DocumentUpload、DocumentList、ChatInterface 组件
  - 在 `frontend/src/main.ts` 中初始化 Vue 应用，注册 Pinia
  - _需求：1.1_

- [x] 19. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有疑问请向用户确认。

- [x] 20. 前端界面优化（路由/Markdown/滚动/文档管理）
  - [x] 20.1 路由分页
  - [x] 20.2 Markdown 渲染
  - [x] 20.3 流式传输实时滚动
  - [x] 20.4 文档管理页面重构

- [x] 21. 删除二次确认
  - [x] 21.1 实现通用 ConfirmDialog.vue 组件
    - 接收 title、message、confirmText props
    - 确认/取消按钮，确认按钮带 loading 状态
    - 支持 ESC 键关闭
    - _需求：7.1, 7.2, 7.3_

  - [x] 21.2 集成到 DocumentList.vue
    - 点击删除按钮弹出 ConfirmDialog，展示文档名称
    - 确认后执行删除，期间按钮显示 loading
    - 删除完成后 Toast 反馈
    - _需求：7.1, 7.2, 7.3, 7.4_

- [x] 22. 多会话历史管理
  - [x] 22.1 后端 Session 持久化
    - 在 `backend/app/models/` 中新增 `ChatSession` SQLAlchemy 模型（session_id、title、messages_json、created_at、last_active）
    - 修改 `ConversationManager`：读写改为 SQLite 持久化，保留内存缓存加速
    - _需求：8.5_

  - [x] 22.2 后端新增 Session 列表和删除 API
    - `GET /api/chat/sessions`：返回所有 Session 元数据列表，按 last_active 倒序
    - `DELETE /api/chat/sessions/{session_id}`：删除指定 Session 及其消息
    - _需求：8.1, 8.7_

  - [x] 22.3 前端 API 层扩展
    - 在 `frontend/src/api/chat.ts` 中新增 `listSessions()`、`deleteSession(id)` 函数
    - 新增 `SessionMeta` 类型到 `types/index.ts`
    - _需求：8.1, 8.7_

  - [x] 22.4 前端 chat store 扩展
    - 在 `chat.ts` 中新增 `sessions` 列表、`currentSessionId`
    - 实现 `loadSessions()`、`switchSession(id)`、`newSession()`、`removeSession(id)` 方法
    - `switchSession` 时加载对应会话的消息历史
    - 发送消息后更新当前会话的 title（首条消息前 20 字）和 last_active
    - _需求：8.2, 8.3, 8.4, 8.6_

  - [x] 22.5 实现 SessionList.vue 组件
    - 展示会话列表，每条显示标题和时间
    - 当前激活会话高亮
    - 顶部"新建会话"按钮
    - 每条会话右侧删除按钮（带二次确认）
    - _需求：8.1, 8.2, 8.3, 8.7_

  - [x] 22.6 重构 ChatView.vue
    - 改为左右布局：左侧 SessionList（220px），右侧 ChatInterface
    - 进入页面时自动加载最近会话或新建会话
    - _需求：8.4_

## 备注

- 标有 `*` 的子任务为可选项，可在 MVP 阶段跳过
- 每个任务均引用具体需求条款，保证可追溯性
- 属性测试使用 Hypothesis，每个属性对应设计文档中的 Property 编号
- 单元测试覆盖边界条件和具体示例场景
- 文档解析和向量化为异步流程，前端通过轮询 `/api/documents/{doc_id}/status` 获取处理状态
