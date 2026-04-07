# 实现计划：QA-Copilot-MVP3

## 概述
本计划旨在分步实现 QA-Copilot-MVP3 的升级，包括数据库版本控制（Alembic）、用户鉴权与会话隔离、多分类知识库支持、真实 Jira API 集成，以及最终基于 LangGraph 的 ReAct Agent 重构。

## 任务

### 1. 数据库基建与用户体系 (Database & Auth)
- [x] 1.1 初始化 Alembic，配置 `alembic.ini` 与 `env.py` 以连接现有 SQLite 数据库。 _需求：5_
- [x] 1.2 在 SQLAlchemy 模型中新增 `User` 模型，并更新 `Session` 与 `Document` 模型。 _需求：1, 3, 5_
- [x] 1.3 运行 `alembic revision --autogenerate` 和 `alembic upgrade head` 生成并应用初始数据库迁移脚本。 _需求：5_
- [x] 1.4 实现基于 JWT 的鉴权逻辑（Token 生成与校验）及相关依赖（`get_current_user`, `require_admin`）。 _需求：1_
- [x] 1.5 编写后端用户注册 (`/register`) 和登录 (`/login`) API。 _需求：1_
- [x] 1.6 修改后端知识库管理与文档上传 API，注入 `require_admin` 权限依赖。 _需求：1_
- [x] 1.7 修改后端会话查询 API，使其仅返回与当前用户绑定的 Session。 _需求：1_

### 2. 知识库隔离改造 (Knowledge Base Isolation)
- [x] 2.1 修改 `HybridRetriever` 支持在向量检索和 BM25 检索中接收 `filter` 参数（按 `kb_category` 过滤）。 _需求：3_
- [x] 2.2 修改后端文档上传 API 和底层持久化逻辑，支持接收并保存 `kb_category` 元数据至 SQLite 和 ChromaDB。 _需求：3_

### 3. Jira 客户端封装 (Jira Client Integration)
- [x] 3.1 编写 `app/services/jira_client.py`，封装针对真实 Jira REST API 的调用（支持 JQL 查询）。 _需求：2_
- [x] 3.2 增加相应的环境变量配置读取（`.env`）。 _需求：2_

### 4. LangGraph ReAct 重构 (Agent Engine Refactor)
- [x] 4.1 编写 `@tool` 装饰的工具函数集：`retrieve_default_kb`, `retrieve_translation_kb`, `retrieve_log_kb`, `query_jira`。 _需求：3, 4_
- [x] 4.2 重构 `app/services/copilot_service.py`，废弃原有的单步 `Router Node` 图结构。 _需求：4_
- [x] 4.3 引入 LangGraph 预置的 `create_react_agent`（或手动构建工具循环图），将工具集注入，实现 ReAct 范式的 Agent 引擎。 _需求：4_
- [x] 4.4 确保 `copilot_service.py` 返回的 SSE 流能够正确透传 Agent 多步思考的最终结果和工具调用产生的知识溯源数据 (Sources)。 _需求：4_

### 5. 前端交互升级 (Frontend Evolution)
- [x] 5.1 在前端引入 Vue Router 和 Pinia `authStore`，实现全局路由守卫和 Axios Token 注入。 _需求：1_
- [x] 5.2 开发登录 (Login) 与注册 (Register) 页面 UI 及逻辑。 _需求：1_
- [x] 5.3 改造布局界面：隐藏非管理员用户的”知识库管理”入口；仅展示当前用户的历史会话。 _需求：1_
- [x] 5.4 改造”文档上传”组件，增加”知识库分类”（通用、翻译、日志等）下拉选择器并传递至后端。 _需求：3_
- [x] 5.5 进行全链路系统测试，验证多步意图（如”查询 Jira 并在翻译知识库中翻译结果”）是否按预期执行。 _需求：全部_

### 6. 知识源界面优化 (Knowledge Source UI Enhancement)
- [x] 6.1 重构知识源列表组件，采用卡片式布局，优化间距和排版。 _需求：6_
- [x] 6.2 应用 Tailwind CSS 响应式设计，适配不同屏幕尺寸。 _需求：6_
- [x] 6.3 统一配色方案和字体层级，确保视觉协调。 _需求：6_

### 7. 知识源详情查看与源文件下载 (Knowledge Source Detail & Download)
- [x] 7.1 开发知识源详情弹窗/页面组件，展示分块列表和元数据。 _需求：7_
- [x] 7.2 前端集成下载按钮，调用已有的 `GET /api/documents/{doc_id}/download` API。 _需求：7_

### 8. Jira 配置外部化 (Jira Config Externalization)
- [x] 8.1 在 `.env` 和 `backend/app/config.py` 中添加 Jira 相关环境变量定义。 _需求：8_
- [x] 8.2 重构 `jira_client.py`，从配置模块动态读取 Jira 连接信息。 _需求：8_
- [x] 8.3 添加配置缺失时的错误处理和日志记录。 _需求：8_

### 9. LangGraph 可观测性增强 (Observability Enhancement)
- [x] 9.1 新增 `AgentTrace` 和 `TraceStep` 数据模型（`backend/app/models/`）。 _需求：9_
- [x] 9.2 在 `CopilotService.answer()` 中注入追踪逻辑，记录输入输出和执行耗时。 _需求：9_
- [x] 9.3 开发管理员观测 API：`GET /api/admin/traces`、`GET /api/admin/traces/{id}`、导出 JSON。 _需求：9_
- [x] 9.4 开发前端观测界面 `/admin/observability`，仅管理员可访问，展示执行轨迹和耗时。 _需求：9_

### 10. 对话反馈功能 (Chat Feedback)
- [x] 10.1 新增 `ChatFeedback` 数据模型。 _需求：10_
- [x] 10.2 后端新增反馈 API：`POST /api/chat/sessions/{session_id}/messages/{index}/feedback`。 _需求：10_
- [x] 10.3 前端 `MessageBubble.vue` 添加点赞/点踩按钮，集成反馈 API。 _需求：10_
- [x] 10.4 在观测界面中展示反馈统计数据。 _需求：10_

### 11. 数据库迁移 (Database Migration)
- [x] 11.1 运行 `alembic revision --autogenerate` 生成迁移脚本（包含 `agent_traces`、`trace_steps`、`chat_feedbacks`）。 _需求：9, 10_
- [x] 11.2 运行 `alembic upgrade head` 应用数据库迁移。 _需求：9, 10_