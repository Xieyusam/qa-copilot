# 实现计划：Copilot-transformation

## 概述
分步骤实现 LangGraph 多意图路由、混合检索增强、文档语义切分以及前端交互体验优化，将知识库升级为 AI-Copilot。

## 任务

- [x] 1. **基础架构与模型层扩展** _需求：3, 6_
  - [x] 1.1 更新数据库模型，`documents` 表增加 `status` 字段。
  - [x] 1.2 更新 Pydantic Schemas，`ChunkResult` 和 `SourceRef` 增加 `similarity_score` 字段。
  - [x] 1.3 编写数据库迁移脚本（或手动更新 SQLite 表结构）。

- [x] 2. **语义切分优化与新格式支持 (Semantic Chunker)** _需求：4_
  - [x] 2.1 安装 `langchain-text-splitters` 依赖。
  - [x] 2.2 安装 `pandas` 和 `openpyxl` 依赖以支持 Excel 文件解析。
  - [x] 2.3 重构 `app/services/chunker.py`，根据 `doc.file_type` 路由切分策略。
  - [x] 2.4 实现 Markdown 的标题层级切分。
  - [x] 2.5 实现 TXT/DOCX/PDF 的递归字符切分。
  - [x] 2.6 在 `parser.py` 中新增 `_parse_xlsx` 方法，基于 Pandas 将每一行数据展开为“表头: 值”的段落。
  - [x] 2.7 编写 Chunker 单元测试，补充 Excel 格式测试用例。

- [x] 3. **混合检索与重排引擎** _需求：3, 5_
  - [x] 3.1 安装 `rank_bm25` 依赖。
  - [x] 3.2 实现 `BM25Retriever`，支持在文档入库时构建倒排索引。
  - [x] 3.3 修改 `VectorStore` (ChromaDB)，在查询时计算并返回 `similarity_score`。
  - [x] 3.4 实现 `HybridRetriever`，融合 Vector 和 BM25 的检索结果并去重。
  - [x] 3.5 废弃大模型重排，实现基于纯数学的 RRF (Reciprocal Rank Fusion) 倒数秩融合算法对融合结果进行极速二次打分排序。

- [x] 4. **LangGraph Agent 工作流重构** _需求：1_
  - [x] 4.1 定义新的 `CopilotState`。
  - [x] 4.2 实现 `Intent Router` 节点，基于 LLM 判断用户意图。
  - [x] 4.3 迁移原有的 RAG 逻辑至 `RAG Node`。
  - [x] 4.4 实现 `Log Analysis Node`（编写特定的 Prompt）。
  - [x] 4.5 实现 `Translation Node`（编写特定的 Prompt）。
  - [x] 4.6 实现 `Jira Tool Node`（Mock 数据返回）。
  - [x] 4.7 组装 StateGraph，编译图结构，并更新流式输出逻辑。

- [x] 5. **后端 API 扩展** _需求：6_
  - [x] 5.1 修改 `documents.py` 上传逻辑，正确初始化和更新文档 `status`。
  - [x] 5.2 新增 `GET /api/documents/status` 接口。
  - [x] 5.3 确保 SSE 接口兼容新的 Agent 输出格式。
  - [x] 5.4 更新 `uploader.py` 的支持格式集合，加入 `xlsx`。

- [x] 6. **前端体验优化** _需求：2, 3, 6_
  - [x] 6.1 更新 `chat.ts` Store，集成 `AbortController` 支持中断请求。
  - [x] 6.2 在 `chat.ts` 中实现 `regenerate` 方法。
  - [x] 6.3 优化 `MessageBubble.vue`，引入 `throttle` 降低 `marked` 渲染频率。
  - [x] 6.4 在 `MessageBubble.vue` 的来源列表中展示相似度得分。
  - [x] 6.5 修改 `ChatInterface.vue`，增加“停止生成”和“重新生成”按钮。
  - [x] 6.6 修改 `DocumentList.vue`，增加轮询机制展示文档解析状态。
  - [x] 6.7 修改 `DocumentUpload.vue`，在拖拽和选择框中支持 `.xlsx` 后缀。

- [x] 7. **集成测试与修复** _需求：1-6_
  - [x] 7.1 测试多意图路由的准确性。
  - [x] 7.2 测试混合检索和相似度得分显示。
  - [x] 7.3 测试前端流式中断和重新生成功能是否会有数据残留。
  - [x] 7.4 验证长文本生成的页面渲染性能。

- [x] 8. **底层框架架构升级与运维完善** _需求：7_
  - [x] 8.1 修改 `backend/requirements.txt`，将 `langchain`, `langchain-community`, `langchain-openai`, `langchain-chroma`, `langgraph` 升级至 `^1.0.0`。
  - [x] 8.2 运行并修复可能因大版本升级导致的 API 弃用或破坏性变更报错。
  - [x] 8.3 运行全量单元测试 (`pytest`) 验证核心链路逻辑是否完整。
  - [x] 8.4 完善跨平台部署方案，提供 Mac/Linux 的 `dev.sh` 以及全平台的 `docker-compose.yml` 容器化部署脚本。
