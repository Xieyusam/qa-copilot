# 需求文档

## 简介
QA-Copilot-MVP3 的核心目标是向真实业务级应用演进。在保留混合检索与流式回答等特性的基础上，引入用户体系与鉴权，隔离多用户会话并实现知识库管理的权限控制（RBAC）；将基于模拟数据的 Jira 意图升级为真实的 Jira API 调用；将单知识库扩展为支持多垂直领域（如通用问答、专有名词翻译、日志分析）的逻辑隔离知识库；最重要的是，重构当前的单次路由架构，升级为支持 Function Calling 和多步工具调用的标准 ReAct 范式，以满足复杂多意图的用户查询。

## 词汇表
- **RBAC (Role-Based Access Control)**: 基于角色的访问控制。本项目分为普通用户（`user`）和超级管理员（`admin`）。
- **ReAct 范式**: 大模型推理与行动（Reasoning and Acting）的 Agent 架构，允许 Agent 自主决定调用工具的顺序、次数，支持在一次对话中完成多步操作。
- **知识库隔离 (KB Isolation)**: 将不同垂直领域的文档（如 `default` 通用文档、`translation` 专有名词库、`log` 日志分析手册）在向量库（ChromaDB）和倒排索引（BM25）中进行逻辑分区检索。
- **Alembic**: SQLAlchemy 官方提供的数据库版本控制和迁移工具，用于自动追踪和应用数据库表结构的变更。
- **AgentTrace**: Agent 执行追踪记录，记录一次完整对话的元数据和总耗时。
- **TraceStep**: 单步追踪记录，记录工具调用或 LLM 生成的输入输出和耗时。
- **ChatFeedback**: 对话反馈记录，记录用户对 AI 回复的点赞或点踩反馈。

## 需求

### 需求 1：用户鉴权、会话隔离与权限控制
**用户故事：** 作为一名普通用户，我希望能够注册和登录系统，以便我的对话历史与他人隔离；作为一名管理员，我希望只有我能管理知识库，以免被其他人误删文档。
#### 验收标准
1. THE System SHALL 提供基于 JWT 的用户注册与登录接口。
2. THE System SHALL 在对话接口中强制验证用户 Token，并实现基于 User ID 的会话（Session）隔离，用户只能查看和继续自己的会话。
3. IF 用户角色不为 `admin`，THEN THE System SHALL 拒绝其访问文档上传、文档删除、知识库重建等管理 API，并返回 403 状态码。

### 需求 2：Jira 工具的真实集成
**用户故事：** 作为一名研发人员，我希望能够在对话中直接查询真实的 Jira 任务状态和详情，以便快速了解项目进度。
#### 验收标准
1. THE System SHALL 支持通过环境变量（如 `.env` 中的 `JIRA_URL`, `JIRA_USER`, `JIRA_TOKEN`）安全配置 Jira 访问凭证。
2. WHEN Agent 识别到 Jira 查询意图时，THE System SHALL 能够调用真实的 Jira REST API（如通过 JQL 搜索或获取指定 Issue）。
3. THE System SHALL 将 Jira 返回的真实 Issue 数据（状态、经办人、描述等）作为上下文注入给 LLM 进行总结回复。

### 需求 3：多场景专属知识库隔离
**用户故事：** 作为一名用户，我希望在让 Copilot 翻译文本或分析报错日志时，它能自动参考上传的“专有名词表”或“内部错误手册”，以便提供准确度更高的回答。
#### 验收标准
1. THE System SHALL 支持在文档上传时指定所属的“知识库分类”（如 `default`, `translation`, `log` 等），并在 ChromaDB 元数据和 SQLite 中落盘记录。
2. WHEN 执行特定意图（如翻译）的检索时，THE System SHALL 能够将“知识库分类”作为 Filter 传递给 HybridRetriever，确保仅在对应的分类文档中进行向量和 BM25 的混合召回。

### 需求 4：多意图与多步工具调用 (ReAct 升级)
**用户故事：** 作为一名高级用户，我希望能在一次提问中说“帮我查一下 PROJ-123 任务，并把它翻译成中文”，系统能够自动完成两步操作而不需要我分两次提问。
#### 验收标准
1. THE System SHALL 废弃现有的硬编码 Router Node 单步路由模式，使用 LangGraph 结合大模型原生的 Function/Tool Calling 能力构建标准 ReAct 架构。
2. THE System SHALL 将检索通用库、检索翻译库、检索日志库、查询 Jira 封装为独立的工具函数（`@tool`）。
3. WHEN 用户提出复合需求时，THE System SHALL 能够在一个图执行周期中多步循环（例如：调用 `jira_tool` -> 获得结果 -> 调用 `translation_kb_tool` -> 获得专有名词 -> 最终生成回答）。

### 需求 5：数据库版本控制与自动迁移
**用户故事：** 作为一名开发者，我希望系统能够自动生成和管理数据库表结构的变更脚本，以便在模型修改时轻松、安全地完成数据库的升级和回滚，无需手动编写和执行 SQL 脚本。
#### 验收标准
1. THE System SHALL 集成 Alembic 作为后端 SQLAlchemy 的官方数据库迁移工具。
2. WHEN 后端 ORM 数据模型发生变更时，THE System SHALL 能够通过命令（如 `alembic revision --autogenerate`）自动比对现有数据库 Schema 并生成对应的迁移脚本。
3. THE System SHALL 支持通过命令（如 `alembic upgrade head` 或 `alembic downgrade`）安全地进行数据库的升级与回滚操作。

### 需求 6：知识源界面优化
**用户故事：** 作为一名用户，我希望知识源的展示界面更加优美简洁，排版合理不紧凑，以便更舒适地浏览和查看知识来源信息。
#### 验收标准
1. THE System SHALL 优化知识源列表的视觉设计，采用清晰的卡片式布局或列表式布局，元素间距适中。
2. THE System SHALL 确保文本、图标、按钮等元素的排版协调，避免视觉拥挤。
3. THE System SHALL 支持响应式设计，在不同屏幕尺寸下保持良好的阅读体验。

### 需求 7：知识源详情查看与源文件下载
**用户故事：** 作为一名用户，我希望能够点击知识源列表项查看具体的分块内容，并支持下载原始文件，以便深入了解知识来源的细节。
#### 验收标准
1. WHEN 用户点击知识源列表项时，THE System SHALL 展示该知识库文档的所有分块（Chunk）内容，包括分块文本、元数据（如页码、位置）等信息。
2. THE System SHALL 在知识源详情页面提供"下载源文件"按钮，允许用户下载上传时的原始文档（PDF、Markdown 等）。
3. THE System SHALL 在下载时验证用户权限，确保普通用户只能下载自己可访问的知识库文档。

### 需求 8：Jira 配置外部化
**用户故事：** 作为一名运维人员，我希望 Jira 的连接信息通过环境变量配置，而不是写死在代码中，以便在不同环境中灵活切换 Jira 服务地址和凭证。
#### 验收标准
1. THE System SHALL 从 `.env` 文件中读取 `JIRA_URL`、`JIRA_USER_EMAIL`、`JIRA_API_TOKEN` 等配置项。
2. THE System SHALL 在 Jira 相关代码中通过环境变量动态获取配置，禁止硬编码任何连接信息。
3. IF 环境变量未配置或配置无效时，THE System SHALL 在启动时或调用时给出明确的错误提示，而非静默失败。

### 需求 9：LangGraph 可观测性增强
**用户故事：** 作为一名管理员，我希望能够在一个专属的观测界面中直观地追踪 LangGraph 节点的每一次多意图路由的 Prompt 表现与耗时，以便分析 Agent 的决策过程和性能瓶颈，该界面仅对管理员角色可见。
#### 验收标准
1. THE System SHALL 在每次 Agent 执行过程中记录关键节点的输入输出，包括：用户 Prompt、工具调用决策、工具返回结果、最终回答。
2. THE System SHALL 记录每个节点的执行耗时，并汇总为一次对话的完整耗时链路。
3. THE System SHALL 提供一个专属的观测管理界面（前端页面），仅当用户角色为 `admin` 时可访问，用于可视化展示多步推理轨迹。
4. THE System SHALL 在观测界面中展示：哪一步调用了哪个工具、耗时多少、Prompt 内容是什么、工具返回结果等。
5. THE System SHALL 支持将观测数据导出为结构化格式（如 JSON），便于后续分析与调试。

### 需求 10：对话反馈功能
**用户故事：** 作为一名用户，我希望在每次对话完成后能够对 AI 的回答进行点赞或点踩反馈，以便系统记录对话质量数据，帮助管理员在观测界面中追踪和评估 Agent 的回答效果。
#### 验收标准
1. THE System SHALL 在每条 AI 回复消息下方显示反馈按钮（点赞👍和点踩👎），允许用户提交满意度反馈。
2. WHEN 用户点击反馈按钮时，THE System SHALL 记录该反馈（类型：`positive` 或 `negative`），关联到具体的消息 ID 和会话 ID。
3. THE System SHALL 将反馈数据持久化存储至数据库，供管理员在观测界面中查询和分析。
4. THE System SHALL 在观测界面中展示每次对话的反馈统计，包括：点赞数、点踩数、反馈率等指标。
