# 技术设计文档：QA-Copilot-MVP3

## Overview
本 MVP 的后端依然基于 FastAPI 和 LangGraph，前端基于 Vue 3 + Tailwind CSS。
本次升级的重点在于：
1. 引入 JWT (JSON Web Token) 与 RBAC 权限控制；
2. 集成 Alembic 实现 SQLAlchemy 数据库模型迁移；
3. 将 LangGraph 工作流由单次路由（Hard-coded Router Node）升级为支持 Function Calling 的 ReAct 范式；
4. 实现多分类知识库的逻辑隔离与真实 Jira 接口的集成；
5. 新增管理员观测界面，追踪 Agent 执行轨迹与耗时；
6. 新增对话反馈功能，记录用户满意度。

## Architecture
系统整体架构通过引入 ReAct 范式的 Agent，实现了工具的自主调用和多步推理，同时增加了观测与反馈模块。

```mermaid
graph TB
    subgraph Frontend [前端 (Vue 3)]
        UI[User Interface]
        Auth[Auth Module (JWT)]
        Chat[Chat Interface]
        Feedback[Feedback Buttons]
        Admin[Admin Dashboard]
        Observability[观测界面 (Admin Only)]
    end

    subgraph Backend [后端 (FastAPI)]
        API_Auth[Auth API]
        API_Chat[Chat API]
        API_Doc[Doc/KB API]
        API_Admin[Admin API: Traces, Feedbacks]
        
        subgraph Agent_Engine [LangGraph ReAct Agent]
            LLM[LLM with Function Calling]
            Tool_Node[Tool Executor Node]
            Tracer[Trace Logger]
        end
        
        subgraph Tools [Agent Tools]
            Tool_KB_Default[@tool: retrieve_default_kb]
            Tool_KB_Trans[@tool: retrieve_translation_kb]
            Tool_KB_Log[@tool: retrieve_log_kb]
            Tool_Jira[@tool: query_jira]
        end
        
        subgraph Data_Layer [数据层]
            SQLite[(SQLite: Users, Sessions, Docs, Traces, Feedbacks)]
            Alembic[Alembic Migration]
            Chroma[(ChromaDB)]
            BM25[BM25 Index]
        end
    end

    UI --> Auth
    Auth --> API_Auth
    UI --> Chat
    UI --> Admin
    Chat --> API_Chat
    Chat --> Feedback
    Feedback --> API_Chat
    Admin --> API_Doc
    Admin --> Observability
    Observability --> API_Admin
    
    API_Auth --> SQLite
    API_Chat --> Agent_Engine
    API_Chat --> SQLite
    API_Doc --> SQLite
    API_Doc --> Chroma
    API_Doc --> BM25
    API_Admin --> SQLite
    
    Agent_Engine -- "1. Plan & Call Tool" --> Tools
    Agent_Engine -- "2. Log Trace" --> Tracer
    Tracer --> SQLite
    Tools -- "3. Tool Result" --> Agent_Engine
    Agent_Engine -- "4. Generate Answer" --> API_Chat
    
    Tool_KB_Default --> Chroma
    Tool_KB_Trans --> Chroma
    Tool_KB_Log --> Chroma
    Tool_Jira --> Jira_API((Jira REST API))
```

## Components and Interfaces

### 1. 数据库与鉴权 (DB & Auth)
- **Alembic 集成**: 在 `backend/` 目录下初始化 `alembic`，配置 `alembic.ini` 指向现有的 SQLite 数据库，并生成初始迁移脚本（Migration Script）。
- **Data Models**: 
  - 新增 `User` 模型，包含 `id`, `username`, `hashed_password`, `role` (`user` | `admin`) 等字段。
  - 修改 `Session` 模型，增加 `user_id` 外键，实现会话与用户绑定。
  - 修改 `Document` 模型，增加 `kb_category` 字段，默认值为 `default`。
- **Auth API**:
  - `POST /api/auth/register`: 用户注册。
  - `POST /api/auth/login`: 用户登录，返回 JWT Token。
  - `dependencies.py`: 增加 `get_current_user` 和 `require_admin` 依赖项，用于保护路由。

### 2. 知识库隔离与多分类检索 (KB Isolation)
- **文档元数据 (Metadata)**: 在处理文档上传并写入 ChromaDB 和 BM25 时，将 `kb_category`（例如 `default`, `translation`, `log`）附加到 Chunk 的 metadata 中。
- **HybridRetriever 改造**: 修改 `retrieve` 方法，支持传入 `filter` 参数（例如 `{"kb_category": "translation"}`）。在向量检索和 BM25 检索时，都应用该过滤条件，确保只在对应类别的文档中搜索。

### 3. Jira 工具集成 (Jira Tool)
- **配置**: 在 `.env` 中读取 `JIRA_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`。
- **工具实现**: 封装 `jira_client.py`，使用 `requests` 库调用 Jira REST API（例如 `/rest/api/2/search` 或 `/rest/api/2/issue/{issueId}`），并将其包装成 Agent 工具。

### 4. ReAct Agent 架构 (LangGraph)
- **工具定义 (@tool)**:
  - `retrieve_default_kb`: 用于通用问题解答。
  - `retrieve_translation_kb`: 用于查询专有名词翻译。
  - `retrieve_log_kb`: 用于查询系统日志分析。
  - `query_jira`: 用于查询 Jira 任务。
- **Graph 重构**: 废弃原有的 `_router_node` 和多分支结构。使用 LangGraph 的 `create_react_agent`（或手动构建包含 `agent` 节点和 `tools` 节点的循环图），使得大模型能够自主选择工具并进行多步调用。
- **状态管理 (State)**: 更新 `CopilotState`，使其符合 ReAct 架构的需求（通常只需维护 `messages` 列表即可，工具调用结果会作为 `ToolMessage` 追加到历史中）。

### 5. 前端改造 (Frontend)
- **状态管理**: 在 Pinia 中增加 `authStore`，管理用户登录状态和 Token。
- **路由守卫**: 增加 Vue Router 的全局前置守卫（`beforeEach`），未登录用户重定向至登录页。
- **拦截器**: 配置 Axios 实例，在请求头中自动注入 `Authorization: Bearer <token>`。
- **界面调整**: 
  - 增加登录/注册页面。
  - 会话列表仅显示当前用户的会话。
  - 仅当当前用户角色为 `admin` 时，才显示知识库管理入口。
  - 文档上传组件增加”知识库分类”的下拉选择框。

### 6. 知识源界面优化 (Knowledge Source UI Enhancement)
- **视觉设计**: 
  - 采用卡片式布局展示知识源列表，每个卡片包含文档名称、类型、上传时间等信息。
  - 使用 Tailwind CSS 的 spacing utilities（如 `gap-4`、`p-6`）确保元素间距适中。
  - 采用一致的配色方案和字体层级，避免视觉拥挤。
- **响应式设计**: 使用 Tailwind 的响应式类（如 `sm:`、`md:`、`lg:`）适配不同屏幕尺寸。

### 7. 知识源详情与下载 (Knowledge Source Detail & Download)
- **详情弹窗/页面**: 点击知识源项后，打开详情弹窗或跳转详情页，展示：
  - 文档的所有分块（Chunk）列表，每个分块显示文本内容和元数据（页码、位置等）。
  - 分块内容支持高亮显示关键词。
- **下载接口**: 
  - 后端新增 `GET /api/documents/{doc_id}/download` API，返回原始文件流。
  - 前端在详情页提供下载按钮，调用 API 并触发浏览器下载。
- **权限校验**: 下载 API 需验证用户身份，确保用户有权访问该文档。

### 8. Jira 配置外部化 (Jira Config Externalization)
- **环境变量**: 在 `.env` 和 `backend/app/config.py` 中定义：
  ```python
  JIRA_URL: str
  JIRA_USER_EMAIL: str
  JIRA_API_TOKEN: str
  ```
- **配置读取**: `jira_client.py` 从 `config.py` 获取配置，而非硬编码。
- **错误处理**: 配置缺失时抛出明确的 `ConfigurationError`，并在日志中记录。

### 9. LangGraph 可观测性 (Observability Enhancement)
- **数据模型**: 新增 `AgentTrace` 和 `TraceStep` 模型：
  - `AgentTrace`: 记录一次完整的 Agent 执行，包含 `session_id`、`question`、`total_time_ms`、`created_at`。
  - `TraceStep`: 记录单步执行，包含 `trace_id`、`step_type`（如 `tool_call`、`llm_stream`）、`tool_name`、`input_prompt`、`output_result`、`time_ms`。
- **追踪注入**: 在 `CopilotService.answer()` 中注入追踪逻辑：
  - 使用 `time.perf_counter()` 记录每个节点的执行耗时。
  - 在 `on_tool_end` 和 `on_chat_model_stream` 事件中捕获输入输出。
- **管理员观测界面**:
  - 新增前端路由 `/admin/observability`，仅 `admin` 角色可访问。
  - 展示对话列表、每条对话的执行轨迹、耗时统计、Prompt/结果详情。
  - 支持导出单次追踪数据为 JSON。
- **API 接口**:
  - `GET /api/admin/traces`: 获取追踪列表（分页）。
  - `GET /api/admin/traces/{trace_id}`: 获取单次追踪详情。
  - `GET /api/admin/traces/{trace_id}/export`: 导出 JSON。

### 10. 对话反馈功能 (Chat Feedback)
- **数据模型**: 新增 `ChatFeedback` 模型：
  - 包含 `id`、`session_id`、`message_index`、`feedback_type`（`positive`/`negative`）、`user_id`、`created_at`。
- **前端反馈按钮**:
  - 在 `MessageBubble.vue` 的 AI 回复下方添加点赞👍/点踩👎按钮。
  - 点击后调用 `POST /api/chat/sessions/{session_id}/messages/{index}/feedback`。
- **后端 API**:
  - `POST /api/chat/sessions/{session_id}/messages/{index}/feedback`: 提交反馈。
  - `GET /api/admin/feedbacks`: 管理员获取反馈统计。
- **观测界面集成**:
  - 在观测界面中展示反馈统计：每条对话的反馈类型、反馈率等。

### 11. 数据库迁移 (Database Migration)
- 使用 Alembic 生成迁移脚本，包含新增的 `agent_traces`、`trace_steps`、`chat_feedbacks` 三张表。
- 执行 `alembic upgrade head` 应用迁移。