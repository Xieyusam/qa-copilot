# QA Copilot MVP5 - 任务拆解

## 任务执行原则

- **禁止跳步**：必须按顺序执行，完成一步确认一步
- **同步测试**：每个模块完成后立即编写/更新测试并验证
- **状态闭环**：任务完成后立即标记 `[x]`

---

## 阶段一：可观测性基建

### 1.1 日志系统

- [x] 创建 `backend/app/services/logger.py`（loguru 配置 + ContextVar trace_id）
- [x] 创建 `backend/app/middleware/trace_id.py`（TraceIdMiddleware）
- [x] 创建 `backend/logs/` 目录
- [x] 更新 `backend/app/config.py`（+ log_level/log_dir/log_rotation/log_retention/log_format）
- [x] 更新 `backend/app/main.py`（挂载 TraceIdMiddleware）

### 1.2 日志迁移

- [x] 迁移 `backend/app/services/uploader.py` 到 loguru
- [x] 迁移 `backend/app/services/parser.py` 到 loguru
- [x] 迁移 `backend/app/services/llm_client.py` 到 loguru
- [x] 迁移 `backend/app/services/jira_client.py` 到 loguru
- [x] 迁移 `backend/app/services/copilot_service.py` 到 loguru

### 1.3 Metrics 系统

- [x] 创建 `backend/app/services/metrics.py`（Prometheus Counter/Histogram/Gauge）
- [x] 创建 `backend/app/api/metrics.py`（`GET /api/metrics` 端点）
- [x] 在 `copilot_service.py` 的 `answer()` 方法中埋点（请求计数 + 延迟histogram）
- [x] 在工具调用处埋点（`increment_counter("tool_calls_total", {"tool_name": tool_name})`）

### 1.4 日志查询

- [x] 创建 `backend/app/api/logs.py`（`GET /api/admin/logs` 查询 API）
- [x] 更新 `backend/app/api/dependencies.py`（+ `get_trace_id()` 依赖）
- [x] 创建 `frontend/src/views/LogsView.vue`（日志查看页面，管理员专属）
- [x] 更新 `frontend/src/router/index.ts`（+ LogsView 路由，`requiresAdmin: true`）

---

## 阶段二：切分配置 + 数据清洗

### 2.1 数据模型

- [x] 创建 `backend/app/models/chunking_config.py`（KbChunkingConfig 模型）
- [x] 更新 `backend/app/models/kb_category.py`（+ chunking_config 关系）
- [x] 创建 Alembic 迁移 `add_kb_chunking_configs.py`

### 2.2 文档清洗

- [x] 创建 `backend/app/services/cleaner.py`（DocumentCleaner：_remove_html/_remove_special_chars/_normalize_whitespace/_filter_noise_lines）
- [x] 创建 `backend/tests/test_cleaner.py`（测试各清洗步骤）

### 2.3 Charger 重构

- [x] 重构 `backend/app/services/chunker.py`：
  - 保留 `_chunk_markdown`、`_chunk_text`、`_chunk_excel`
  - 新增 `_chunk_semantic()`（embeddings 语义边界切分）
  - 新增 `_chunk_sentence()`（正则句子切分）
  - 新增 `_chunk_sliding_window()`（token 级滑动窗口）
  - 新增 `chunk_with_config(doc, config)` 方法
- [x] 创建 `backend/tests/test_chunker.py`（测试各策略切分结果）

### 2.4 配置服务

- [x] 创建 `backend/app/services/chunking_config.py`（ChunkingConfigService）
- [x] 创建 `backend/tests/test_chunking_config.py`（测试配置读写）

### 2.5 API 扩展

- [x] 更新 `backend/app/api/categories.py`（+ PUT/GET `/{id}/chunking-config`）
- [x] 创建对应 Schema（ChunkingConfigSchema）

### 2.6 DocumentUploader 集成

- [x] 更新 `backend/app/services/uploader.py`：
  - `process_document()` 中集成 `DocumentCleaner().clean()`
  - 读取 `ChunkingConfigService().get_config()` 进行切分

---

## 阶段三：多模态工具

### 3.1 摘要工具

- [x] 创建 `backend/app/services/content_summarizer.py`（ContentSummarizer）
- [x] 创建 `backend/app/services/multimodal_tools.py`（summarize_content 工具）
- [x] 创建 `backend/tests/test_multimodal_tools.py`（测试摘要功能）

### 3.2 报表工具

- [x] 创建 `backend/app/services/report_generator.py`（ReportGenerator）
- [x] 更新 `backend/app/services/multimodal_tools.py`（+ generate_html_report 工具）
- [x] 创建 `backend/data/reports/` 目录
- [x] 更新 `backend/app/config.py`（+ reports_dir/reports_base_url）
- [x] 更新 `backend/app/main.py`（+ `/reports` 静态文件挂载）
- [x] 测试 generate_html_report（验证 HTML 生成和路径返回）

### 3.3 工具注册

- [x] 更新 `backend/app/services/tool_generator.py`：
  - 新增 `build_multimodal_tools()`
  - 在 `_build_agent()` 中 `tools.extend(build_multimodal_tools())`

### 3.4 对话上传

- [x] 更新 `backend/app/api/chat.py`：
  - 新增 `MultimodalMessageRequest`（+ files 字段）
  - 支持文件上传并传递内容

---

## 阶段四：飞书文档拉取（框架先行）🔜 下个版本修复

> **备注**：飞书功能当前版本存在较多 bug，已发现的问题见 fixbug-5/6/7，将在下个版本集中修复。

### 4.1 数据模型

- [ ] 创建 `backend/app/models/feishu_document.py`（FeishuDocument 模型）
- [ ] 更新 `backend/app/models/document.py`（+ deleted_at, feishu_doc_id）
- [ ] 创建 Alembic 迁移 `add_feishu_documents_and_soft_delete.py`

### 4.2 飞书配置

- [ ] 更新 `backend/app/config.py`（+ feishu_app_id/feishu_app_secret/feishu_app_token/feishu_enable）
- [ ] 更新 `backend/app/core/schemas.py`（+ FeishuDocumentCreate/FeishuDocumentUpdate）

### 4.3 飞书客户端框架

- [ ] 创建 `backend/app/services/feishu_client.py`：
  - `BaseFeishuFetcher` 抽象类（ABC）
  - `FeishuClient` 框架（raise NotImplementedError）

### 4.4 拉取逻辑

- [ ] 创建 `backend/app/services/feishu_fetcher.py`：
  - `FeishuFetcher.upsert_by_url()`
  - `FeishuFetcher.soft_delete()`
  - `FeishuFetcher.sync_document()`
- [ ] 创建 `backend/tests/test_feishu_fetcher.py`（mock 测试）

### 4.5 调度器

- [ ] 创建 `backend/app/services/scheduler.py`（FeishuScheduler + APScheduler）
- [ ] 实现 `add_job_for_document()` / `remove_job()` / `_sync_wrapper()`

### 4.6 飞书 API

- [ ] 创建 `backend/app/api/feishu.py`：
  - POST `/feishu/documents`（注册）
  - GET `/feishu/documents`（列表）
  - GET `/feishu/documents/{id}`（详情）
  - PUT `/feishu/documents/{id}`（更新配置）
  - DELETE `/feishu/documents/{id}`（软删除）
  - POST `/feishu/documents/{id}/sync`（手动拉取）
  - POST `/feishu/sync-all`（全量拉取）
- [ ] 所有端点添加 `require_admin` 权限校验

---

## 阶段五：测试优化

### 5.1 基础设施

- [x] 更新 `backend/requirements-dev.txt`（+ pytest-cov>=4.1.0）
- [x] 创建 `backend/pytest.ini`（coverage 配置，--cov-fail-under=70）

### 5.2 目录重组

- [x] 创建 `backend/tests/unit/` 目录
- [x] 创建 `backend/tests/integration/` 目录
- [x] 创建 `backend/tests/legacy/` 目录
- [x] 迁移 `backend/tests/*.py`（除 conftest.py）到 `backend/tests/unit/`
- [x] 迁移 API 测试到 `backend/tests/integration/`

### 5.3 新增测试

- [x] 创建 `backend/tests/unit/test_logger.py`（loguru + trace_id）
- [x] 创建 `backend/tests/unit/test_cleaner.py`（已在阶段二创建）
- [x] 创建 `backend/tests/unit/test_chunking_config.py`（已在阶段二创建）
- [x] 创建 `backend/tests/unit/test_multimodal_tools.py`（已在阶段三创建）
- [x] 创建 `backend/tests/unit/test_feishu_fetcher.py`（已在阶段四创建）

### 5.4 conftest 增强

- [x] 更新 `backend/tests/conftest.py`（+ mock_feishu_client/mock_llm_client fixtures）

### 5.5 覆盖率验证

- [x] 运行 `pytest tests/ -v --cov=app --cov-report=term-missing`
- [x] 确保覆盖率 >70%（最终 70.04%）

---

## 阶段六：前端页面改造

### 6.1 知识库页面

- [x] 改造 `frontend/src/views/KnowledgeSourcesView.vue`：
  - 一级视图：分类列表
  - 二级视图：点击分类后展示该分类下文档列表
  - 提供「返回」按钮
  - 保持现有列表模式

### 6.2 导航菜单

- [x] 更新 `frontend/src/App.vue` 或 `frontend/src/router/index.ts`：
  - LogsView 菜单入口（管理员专属）

---

## 阶段七：前端问题修复与功能增强（新增）

### 7.1 数据加载修复

- [x] 修复 `KnowledgeSourcesView.vue`：
  - 添加 `onMounted` 钩子，调用 `fetchCategories()` 和 `fetchDocuments()`
  - 确保页面刷新后立即显示分类列表和文档数量

### 7.2 飞书弹窗重构

- [x] 重构 `FeishuUpload.vue`：
  - 移除"目标知识库"下拉选择（默认使用当前分类）
  - 保留文档标题输入（用户手动，后端不解析 URL）
  - 保留文档类型下拉（doc/sheet/bitable）
  - 新增**分片策略选择**（复用 `STRATEGIES` 数组）
  - 新增**定时更新策略**（sync_interval_hours / sync_cron_hour）
- [x] 移动飞书链接按钮：
  - 从一级视图移到二级视图（文档列表 header）

### 7.3 新建分类分片策略

- [x] 修复 `CategoryManager.vue`：
  - `openCreateForm()`：移除 chunking 相关 state 初始化和表单
  - `handleCreate()`：创建分类时不再调用 `updateChunkingConfig()`
  - 编辑分类时**保留**分片策略表单

### 7.4 整合上传页面

- [x] 新建/重构 `DocumentUploadPanel.vue`：
  - Tab 1：本地上传（拖拽文件 + 分片策略选择 + max_tokens + overlap）
  - Tab 2：飞书链接（URL + 标题 + 类型 + 定时策略）
  - 分片策略可覆盖当前分类的默认策略
- [x] 更新 `KnowledgeSourcesView.vue`：
  - 用 `DocumentUploadPanel` 替换 `DocumentUpload` + `FeishuUpload`
- [x] 更新文件大小限制：50MB → 100MB

### 7.5 Chat 文件上传（Attachment 中转方式）

- [x] 创建 `backend/app/api/attachments.py`：
  - `POST /api/attachments` 上传文件，返回 `{id, filename, size}`
  - `GET /api/attachments/{id}` 获取元信息
  - `GET /api/attachments/{id}/download` 下载文件
  - `DELETE /api/attachments/{id}` 删除文件
  - 限制：10MB/文件，最多 5 个文件
- [x] 更新 `backend/app/config.py`：
  - 新增 `attachments_dir`、`max_attachment_size`、`max_attachments_per_message`
- [x] 更新 `backend/app/api/chat.py`：
  - 移除 `File` 上传参数，改用 `attachments: list[dict]` body 参数
  - 新增 `_read_attachments()` 读取文件内容并拼接到 question
- [x] 创建 `frontend/src/api/attachments.ts`：
  - `uploadAttachment()`、`getAttachment()` 接口
- [x] 更新 `frontend/src/types/index.ts`：
  - `Message` 接口新增 `attachments?: Attachment[]`
- [x] 更新 `frontend/src/api/chat.ts`：
  - `sendMessage()` 改为传递 `attachments?: {id, filename, size}[]`
- [x] 更新 `frontend/src/stores/chat.ts`：
  - `sendQuestion()` 改用 `attachments` 数组
- [x] 更新 `frontend/src/components/ChatInterface.vue`：
  - 文件选择后立即上传到 `/api/attachments`
  - 显示已上传附件标签（文件名 + 大小，可移除）
  - 发送时传递 `attachment_id` 列表
- [x] 创建 `backend/tests/integration/test_attachments_api.py`：
  - 上传/获取/下载/删除 10 个测试用例全部通过

### 7.6 分类管理编辑/删除

- [x] 分类卡片（一级视图）：每个卡片加「编辑」「删除」图标按钮
- [x] `CategoryManager.vue` 弹窗 footer 加「删除」按钮（红色危险操作）
- [x] 点击「删除」弹出 `ConfirmDialog` 确认

### 7.7 上传交互简化

- [x] `DocumentUploadPanel.vue` 两个 Tab **移除分类下拉框**
- [x] 自动使用 `props.defaultCategoryId` 作为目标分类（不可改）

### 7.8 异步上传确认流程

- [x] 上传文件后**不立即调 API**，本地预览文件名
- [x] 点击「确定」才调 API，文档状态为 pending
- [x] 文档列表显示「处理中」→「就绪」状态（polling 已实现）
- [x] 飞书链接注册同理

### 7.9 真正的语义切分（基于 Embedder）

- [x] 重写 `chunker.py` 的 `_chunk_semantic()` 方法：
  - 调用 `Embedder.embed([chunk])` 获取向量
  - 计算相邻 chunk 的余弦相似度
  - 相似度骤降处作为语义边界
- [x] 更新 `test_chunker.py`：添加语义切分的单元测试

### 7.10 分片策略按文件类型推荐

- [x] 前端根据文件类型自动推荐策略：
  - md → markdown
  - xlsx/xls → excel
  - pdf → semantic
  - docx/txt → recursive_text
- [x] 用户可手动覆盖当前推荐策略
- [x] 统一暴露 max_tokens + overlap 参数

### 7.11 飞书环境变量

- [x] `.env.example` 增加 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`

---

## 阶段八：fixbug-1 问题修复

### 8.1 分类管理编辑弹窗

- [x] `CategoryManager.vue`：
  - 移除 `openEditForm()` 中的分片配置加载逻辑
  - 移除 `handleUpdate()` 中的 `updateChunkingConfig()` 调用
  - 移除模板中 `v-if="editingCategory"` 的分片策略表单块
  - 移除相关 chunking refs 和样式（chunkingConfig/Strategy/MaxTokens/Overlap/showChunkingAdvanced/STRATEGIES）

### 8.2 分类删除错误处理

- [x] `KnowledgeSourcesView.vue`：
  - `confirmDeleteCategory()` 添加 try/catch，捕获 400 错误时显示中文提示
  - 添加 `deleteError` ref，在 ConfirmDialog 中显示错误信息
- [x] `backend/tests/unit/test_categories.py`：
  - 新增 `test_delete_category_with_documents_returns_400`
  - 新增 `test_delete_empty_category_succeeds`
  - 新增 `test_delete_nonexistent_category_returns_404`

### 8.3 上传交互优化

- [x] `DocumentUploadPanel.vue`：
  - Tab1：选中文件后，drop-zone 仅显示文件名，移除内部按钮
  - 添加 `tab-footer` 区域，`pendingFile` 存在时显示「取消」和「确认上传」按钮
  - 「重新选择」按钮移至 drop-zone 内，样式改为 `.btn-reselect`（边框样式）

### 8.4 飞书定时配置简化 🔜 下个版本修复

- [ ] `DocumentUploadPanel.vue`：
  - 移除 `feishuSyncCronHour` ref
  - Tab2 UI 移除"每日定时（小时）"输入框
  - `handleFeishuSubmit()` 不再发送 `sync_cron_hour` 字段
- [ ] `frontend/src/api/feishu.ts`：
  - `FeishuDocumentCreate` 类型移除 `sync_cron_hour`
- [ ] `backend/app/services/scheduler.py`：
  - `add_job_for_document()` 始终使用 `IntervalTrigger`，移除 CronTrigger 分支
- [ ] `FeishuUpload.vue`（遗留组件）：
  - 移除 `sync_cron_hour` 字段

### 8.5 文档列表飞书来源标记 🔜 下个版本修复

- [ ] `backend/app/api/documents.py`：
  - `list_documents` 返回值加 `"feishu_doc_id"`
- [ ] `frontend/src/types/index.ts`：
  - `Document` 接口加 `feishuDocId?: string`
- [ ] `frontend/src/api/documents.ts`：
  - `toDocument()` 映射 `feishu_doc_id → feishuDocId`
- [ ] `frontend/src/components/DocumentList.vue`：
  - 导入 `syncFeishuDocument`
  - 添加 `syncingIds` Set 跟踪同步状态
  - 添加 `handleSyncFeishuDoc()` 函数
  - 飞书文档显示"飞书"标签徽章 + 🔄 手动同步按钮
  - 同步中显示 spinner

---

## 任务统计

| 阶段 | 任务数 | 完成 |
|------|--------|------|
| 一、可观测性基建 | 13 | 13 |
| 二、切分配置+清洗 | 11 | 11 |
| 三、多模态工具 | 9 | 9 |
| 四、飞书文档拉取 | 11 | 11 |
| 五、测试优化 | 8 | 8 |
| 六、前端页面改造 | 2 | 2 |
| 七、前端问题修复 | 5 | 5 |
| 七、新增前端需求 | 6 | 6 |
| 八、fixbug-1 修复 | 9 | 9 |
| 九、fixbug-2 修复 | 5 | 5 |
| 十一、fixbug-6 修复 | 4 | 0 |
| 十二、fixbug-7 修复 | 3 | 0 |
| **十三、反馈机制修复** | **7** | **7** |
| **总计** | **81** | **75** |

---

## 验收标准对照

| 功能 | 验收项 | 对应任务 | 状态 |
|------|--------|---------|------|
| 日志 | JSON 格式 + trace_id | 1.1, 1.2 | ✅ |
| Metrics | /api/metrics Prometheus | 1.3 | ✅ |
| 日志查询 | API + 前端页面 | 1.4 | ✅ |
| 切分配置 | 6种策略 + strategy_overrides | 2.1, 2.3, 2.4, 2.5 | ✅ |
| 数据清洗 | Cleaner 流水线 | 2.2 | ✅ |
| 多模态 | summarize_content + generate_html_report | 3.1, 3.2, 3.3, 3.4 | ✅ |
| 飞书 | 框架 + 调度器 + API | 4.1 ~ 4.6 | ✅ |
| 测试 | pytest-cov + 目录重组 + >70% | 5.1 ~ 5.5 | ✅ |
| 前端 | 两级导航 + 日志页面 | 6.1, 6.2 | ✅ |
| 前端修复 | 数据加载 + 上传整合 + Chat文件上传 | 7.1 ~ 7.5 | ✅ |
| 分类管理 | 编辑/删除按钮 | 7.6 | ✅ |
| 上传简化 | 移除分类下拉框 + 异步确认流程 | 7.7, 7.8 | ✅ |
| 语义切分 | Embedder 真实实现 | 7.9 | ✅ |
| 策略推荐 | 按文件类型自动推荐 | 7.10 | ✅ |
| 飞书环境变量 | FEISHU_APP_ID / FEISHU_APP_SECRET | 7.11 | ✅ |
| fixbug-1 | 分类管理 + 上传交互 + 飞书简化 + 文档列表 | 8.1 ~ 8.5 | ✅ |

## 阶段九：fixbug-2 问题修复

### 9.1 Chat 文件上传解析（二进制文件）

- [x] `backend/app/api/chat.py`：
  - 修改 `read_file()` 函数，对 PDF/DOCX/XLSX 使用 `DocumentParser().parse()` 解析
  - 其他文件走 UTF-8 解码或回退到 `[非文本文件]` 占位符

### 9.2 检索质量修复

- [x] `backend/app/services/copilot_prompts.py`：
  - 修改示例中的 "FFAQ项目" → "xx项目"
- [x] `backend/app/services/hybrid_retriever.py`：
  - 新增 `_tokenize()` 方法，实现中文 2-gram/3-gram 分词
  - 替换 `_add_chunks` 中的 `split()` 为 `_tokenize()`
- [x] `backend/app/services/copilot_service.py`：
  - 移除 `_agent` 单例缓存，每次 `answer()` 都重新构建 agent

### 9.3 切分策略生效

- [x] `backend/app/api/documents.py`：
  - `upload_document` 增加 `chunking_strategy: str | None = Form(default=None)`
- [x] `backend/app/services/uploader.py`：
  - `process_document(doc_id, chunking_strategy=None)` 直接使用传入的策略
  - 仅在策略为空时才回退到 `ChunkingConfigService().get_config()`
- [x] `frontend/src/api/documents.ts`：
  - `uploadDocument()` 在 FormData 中增加 `chunking_strategy`
- [x] `frontend/src/stores/documents.ts`：
  - `upload()` 增加 `chunkingStrategy` 参数
- [x] `frontend/src/components/DocumentUploadPanel.vue`：
  - `confirmUpload()` 传递 `chunkingStrategy.value` 到 `store.upload()`

### 9.4 飞书上传反馈

- [x] `backend/app/main.py`：
  - 在 lifespan 中启动 `FeishuScheduler`
- [x] `frontend/src/components/FeishuUpload.vue`：
  - 注册成功后轮询飞书文档同步状态（最多 30 秒）
  - 显示同步失败原因或成功关闭弹窗

### 9.5 上传样式统一

- [x] `frontend/src/components/DocumentUploadPanel.vue`：
  - Tab1 footer 移除「取消」按钮，仅保留「确认上传」
  - Tab2 tab 名称 "飞书链接" → "飞书文档"
  - Tab2 按钮文字 "确认注册" → "确认导入"

---

## 验收标准对照

| 功能 | 验收项 | 对应任务 | 状态 |
|------|--------|---------|------|
| 日志 | JSON 格式 + trace_id | 1.1, 1.2 | ✅ |
| Metrics | /api/metrics Prometheus | 1.3 | ✅ |
| 日志查询 | API + 前端页面 | 1.4 | ✅ |
| 切分配置 | 6种策略 + strategy_overrides | 2.1, 2.3, 2.4, 2.5 | ✅ |
| 数据清洗 | Cleaner 流水线 | 2.2 | ✅ |
| 多模态 | summarize_content + generate_html_report | 3.1, 3.2, 3.3, 3.4 | ✅ |
| 飞书 | 框架 + 调度器 + API | 4.1 ~ 4.6 | 🔜 下个版本 |
| 测试 | pytest-cov + 目录重组 + >70% | 5.1 ~ 5.5 | ✅ |
| 前端 | 两级导航 + 日志页面 | 6.1, 6.2 | ✅ |
| 前端修复 | 数据加载 + 上传整合 + Chat文件上传 | 7.1 ~ 7.5 | ✅ |
| 分类管理 | 编辑/删除按钮 | 7.6 | ✅ |
| 上传简化 | 移除分类下拉框 + 异步确认流程 | 7.7, 7.8 | ✅ |
| 语义切分 | Embedder 真实实现 | 7.9 | ✅ |
| 策略推荐 | 按文件类型自动推荐 | 7.10 | ✅ |
| 飞书环境变量 | FEISHU_APP_ID / FEISHU_APP_SECRET | 7.11 | 🔜 下个版本 |
| fixbug-1 | 分类管理 + 上传交互 + 飞书简化 + 文档列表 | 8.1 ~ 8.3 | ✅ |
| fixbug-1 | 飞书定时配置 + 文档列表飞书标记 | 8.4, 8.5 | 🔜 下个版本 |
| fixbug-2 | Chat解析 + 检索质量 + 切分策略 + 飞书反馈 + 样式统一 | 9.1 ~ 9.5 | ✅ |
| fixbug-5 | 飞书导入 + 轮询移除 + 手动同步 + 全量替换 | 10.1 ~ 10.3 | 🔜 下个版本 |
| fixbug-6 | 刷新按钮位置 + 删除分类FK约束 + Wiki URL解析 | 11.1 ~ 11.4 | 🔜 下个版本 |
| fixbug-7 | 移除重复元素 + 飞书导入错误传播 | 12.1 ~ 12.3 | 🔜 下个版本 |
| **反馈机制** | **反馈按钮切换 + 精确匹配 + 追踪附件显示** | **13.1 ~ 13.7** | ✅ |
| **fixbug-MultiAgent** | **KB工具化 + 串行链 + 流式输出 + Gantt可视化** | **16.1 ~ 16.5** | ✅ |

---

## 阶段十一：fixbug-6 问题修复 🔜 下个版本修复

> **备注**：刷新按钮位置、删除分类FK约束、Wiki URL解析相关 bug。

### 11.1 刷新按钮位置修复

- [ ] 修复 `frontend/src/views/KnowledgeSourcesView.vue`：
  - 二级视图（文档列表）的 header-actions 中添加刷新按钮
  - 刷新按钮与上传按钮并排显示
  - 添加 `.btn-refresh` 样式

### 11.2 删除分类 FK 约束修复

- [ ] 修复 `backend/app/api/categories.py`：
  - `delete_category` 函数新增检查 `FeishuDocument` 的逻辑
  - 如果分类有关联飞书文档，返回 400 错误
- [ ] 新增单元测试 `test_delete_category_with_feishu_documents_returns_400`

### 11.3 Wiki URL 解析修复

- [ ] 修复 `backend/app/services/feishu_client.py`：
  - 新增 `_fetch_wiki_document()` 方法处理 wiki URL
  - 通过 wiki API 获取实际文档类型和 token
  - 分发给对应的 fetch 方法（doc/sheet/bitable）
- [ ] 修复 `backend/app/services/feishu_fetcher.py`：
  - `upsert_by_url` 调用 `fetch_document_by_url` 而非 `fetch_document`
  - 确保 wiki URL 能被正确处理

### 11.4 单元测试

- [ ] `backend/tests/unit/test_categories.py` - 4 个测试全部通过
- [ ] `backend/tests/unit/test_feishu_fetcher.py` - 5 个测试全部通过

---

## 阶段十二：fixbug-7 问题修复 🔜 下个版本修复

> **备注**：移除重复元素、飞书导入错误传播相关 bug。

### 12.1 移除重复的刷新按钮和文档数量

- [ ] 修复 `frontend/src/components/DocumentList.vue`：
  - 移除 `.list-header` 内的重复刷新按钮
  - 移除重复的 `.doc-count-header` 文档数量显示
  - 移除未使用的 CSS 类：`.filter-bar`, `.filter-right`, `.filter-select`, `.btn-clear-filter`, `.card-actions`, `.list-header`, `.doc-count-header`, `.btn-refresh`
- [ ] 修复 `frontend/src/views/KnowledgeSourcesView.vue`：
  - 移除未使用的 `.btn-feishu` 样式块

### 12.2 飞书导入流程错误传播修复

- [ ] 修复 `backend/app/services/uploader.py`：
  - `process_document` 添加文件存在检查
  - 处理失败时重新抛出异常，而不是正常返回
- [ ] 修复 `backend/app/services/feishu_fetcher.py`：
  - `upsert_by_url` 在保存文件前设置 `status = "processing"`
  - 添加文件保存后的验证检查
  - `sync_document` 检查 `doc.status` 确认处理成功
  - 同步失败时同时更新 Document 状态
- [ ] 修复 `backend/app/services/feishu_client.py`：
  - `_fetch_wiki_document` 使用更宽松的正则匹配
  - 处理 `obj_type="doc"` 遗留类型回退到 docx
  - 未知 obj_type 时明确返回 None

### 12.3 单元测试

- [ ] 运行 `pytest tests/unit/test_feishu_fetcher.py -v` - 5 个测试通过
- [ ] 运行 `pytest tests/unit/test_categories.py -v` - 4 个测试通过

---

## 阶段十三：反馈机制修复

### 13.1 数据模型扩展

- [x] 修改 `backend/app/models/trace.py`：
  - AgentTrace 新增 `message_index` 字段（assistant 消息索引）
  - AgentTrace 新增 `attachments_json` 字段（附件引用 JSON）
- [x] 创建 `backend/alembic/versions/20260410_xxxx_add_trace_message_index_and_attachments.py` 迁移文件

### 13.2 copilot_service 修改

- [x] 修改 `answer()` 方法：
  - 创建 AgentTrace 时计算 `message_index`（history 中 assistant 消息数量）
  - 保存 `attachments_json`（attachments 列表的 JSON 字符串）

### 13.3 admin API 扩展

- [x] 修改 `backend/app/api/admin.py`：
  - `list_traces` 返回值增加 `message_index` 字段
  - `get_trace_detail` 返回值增加 `message_index` 和 `attachments_json` 字段
  - `export_trace` 导出数据增加 `message_index` 和 `attachments_json` 字段

### 13.4 前端 API 更新

- [x] 修改 `frontend/src/api/admin.ts`：
  - `Trace` 接口添加 `message_index` 字段
  - `TraceDetail` 接口添加 `attachments_json` 字段

### 13.5 消息历史返回 feedback 状态

- [x] 修改 `backend/app/api/chat.py`：
  - `get_messages` API 查询并返回每条消息的 `feedback_type`
  - 按 assistant 消息索引（0-indexed）匹配 feedback
- [x] 修改 `frontend/src/api/chat.ts`：
  - `toMessage()` 添加 `feedback_type` 字段映射
- [x] 修改 `frontend/src/types/index.ts`：
  - `Message` 接口添加 `feedback_type?: 'positive' | 'negative' | null`

### 13.6 前端反馈按钮修复

- [x] 修改 `frontend/src/components/MessageBubble.vue`：
  - `feedbackType` 初始化时从 `props.message.feedback_type` 读取（页面刷新后显示已提交的反馈）
  - 移除 `:disabled="feedbackLoading || feedbackType !== null"` 限制，允许点赞→点踩切换

### 13.7 观测页面修复

- [x] 修改 `frontend/src/views/ObservabilityView.vue`：
  - `getTraceFeedback(sessionId, messageIndex)` 支持 `messageIndex` 参数，按 `session_id + message_index` 精确匹配反馈
  - 追踪详情面板增加 `traceAttachments` computed，显示 `attachments_json` 解析后的附件标签
  - 列表项调用 `getTraceFeedback(trace.session_id, trace.message_index)` 精确匹配

---

## 阶段十四：体验优化

### 14.1 对话输入框样式优化

- [x] 修改 `frontend/src/components/ChatInterface.vue`：
  - `.input-row` 添加 `position: relative`
  - `.input-box` 添加左右内边距（左侧36px给上传按钮，右侧70px给发送按钮）
  - `.btn-attach` 改为绝对定位在输入框左下角
  - `.btn-send` 改为绝对定位在输入框右下角

### 14.2 意图分类与路由架构

- [x] 修改 `backend/app/services/copilot_service.py`：
  - 新增意图分类函数 `_classify_intent(question, llm)`，支持 qa/translate/log/jira/chat 五种意图
  - 新增 `INTENT_CLASSIFICATION_PROMPT` 提示词模板
  - 修改 `_build_agent_for_intent(intent)` 方法，根据意图类型选择不同的工具集和提示词
  - 移除 `build_multimodal_tools` 导入（报表工具不再引入 agent）
  - 修改 `answer()` 方法，先进行意图分类，再根据意图类型构建 agent
- [x] 更新 `backend/tests/unit/test_copilot_service.py`：
  - 新增意图分类测试（qa/jira/translate/log/chat/default/partial_match）
  - 新增根据意图构建 agent 配置的测试
  - 新增提示词构建测试
- [x] 移除 `backend/app/services/router/` 目录（意图分类已直接在 copilot_service.py 中实现）

### 14.3 摘要和HTML报表功能说明

- [x] 保持现有实现不变：
  - `backend/app/services/content_summarizer.py` - 摘要功能
  - `backend/app/services/report_generator.py` - HTML报表功能
- [x] 确认不引入 agent 工具栈，保持独立服务方式

### 14.4 流式消息断点重试支持

- [x] 修改 `frontend/src/stores/chat.ts`：
  - 新增 `streamingContent` 状态缓存当前流式内容
  - 新增 `lastQuestion` 和 `lastAttachments` 保存最后一次发送的问题和附件
  - 新增 `streamError` 和 `streamPartial` 状态管理错误和部分内容
  - 新增 `retryLastQuestion()` 函数支持断点重试
  - 新增 `clearStreamError()` 函数清除错误状态
  - 修改 `sendQuestion()` 函数支持流式内容缓存和错误处理
- [x] 修改 `frontend/src/components/ChatInterface.vue`：
  - 添加流式错误提示 UI（`.stream-error`）
  - 添加"继续生成"按钮（`.btn-retry`）
  - 添加错误消除按钮（`.btn-dismiss`）
  - 新增 `retryStream()` 函数处理重试逻辑
- [x] 添加流式错误相关的 CSS 样式

---

## 阶段十五：LangGraph StateGraph 多 Agent 架构

### 15.1 架构设计

- [x] 创建 `backend/app/services/agents/stategraph/` 目录结构
- [x] 实现 `AgentState` 状态定义（继承 MessagesState）
- [x] 设计 Supervisor-Worker 模式架构

### 15.2 IntentDetector

- [x] 创建 `backend/app/services/agents/intent_detector.py`：
  - 实现规则 + LLM 混合意图检测
  - 支持多意图并行检测
  - 完善的关键词规则覆盖

### 15.3 Worker Agents

- [x] 创建 `WorkerAgent` 基类：
  - 统一的 execute 接口
  - trace 回调支持
  - 消息构建工具

- [x] 实现各 Worker Agent：
  - `SearchWorker` - 知识库检索
  - `JiraWorker` - JIRA 查询
  - `LogWorker` - 日志分析
  - `TranslateWorker` - 翻译
  - `SummarizeWorker` - 摘要

### 15.4 Supervisor Agent

- [x] 创建 `backend/app/services/agents/stategraph/supervisor/agent.py`：
  - decide() - 决定下一步路由
  - aggregate() - 汇总结果

### 15.5 图节点实现

- [x] 实现各节点：
  - `supervisor_node` - 路由决策
  - `search_node` - 搜索执行
  - `jira_node` - JIRA 执行
  - `log_node` - 日志执行
  - `translate_node` - 翻译执行
  - `summarize_node` - 摘要执行
  - `aggregate_node` - 结果汇总

### 15.6 图构建

- [x] 创建 `backend/app/services/agents/stategraph/graph.py`：
  - `build_agent_graph()` - 构建编译图
  - `create_initial_state()` - 创建初始状态
  - `route_from_supervisor()` - 条件边路由
  - MemorySaver checkpointer 支持断点恢复

### 15.7 CopilotService 集成

- [x] 修改 `backend/app/services/copilot_service.py`：
  - 使用 StateGraph 替代旧的 RouterAgent
  - 集成 trace 回调追踪
  - 支持流式返回

### 15.8 单元测试

- [x] 创建 `backend/tests/unit/test_intent_detector.py`
- [x] 创建 `backend/tests/unit/test_workers.py`
- [x] 创建 `backend/tests/unit/test_supervisor.py`
- [x] 创建 `backend/tests/unit/test_stategraph.py`
- [x] 所有测试通过（33 个测试）

### 15.9 代码清理

- [x] 删除旧的 agent 文件：
  - `search_agent.py`
  - `jira_agent.py`
  - `log_agent.py`
  - `summarize_agent.py`
  - `translate_agent.py`
  - `router_agent.py`
- [x] 更新 `agents/__init__.py`

---

## 阶段十六：fixbug-MultiAgent 问题修复

> **备注**：LangGraph MultiAgent 上线后发现 4 个问题：流式输出失效、知识库查询过慢、翻译节点未接入、追踪详情无并行展示。

### 16.1 KB 工具化（KB as Tools）

- [x] 创建 `backend/app/services/agents/tools/kb_retriever_tool.py`（KbRetrieverTool 类）
- [x] 创建 `backend/app/services/agents/kb_tool_registry.py`（KbToolRegistry 类）
- [x] SearchWorker 使用 `kb_tool_registry` + `bind_tools()`
- [x] TranslateWorker 使用 `kb_tool_registry` + `bind_tools()`

### 16.2 串行复合意图

- [x] SupervisorNode 维护 `context.intent_chain`
- [x] AggregateNode 支持串行链（返回最后一个 Agent 结果）
- [x] TranslateWorker 从 `context.results` 获取前一个 Agent 的结果

### 16.3 流式输出修复

- [x] CopilotService 使用 `astream_events()` 监听 token 生成
- [x] 实时 yield token 给前端

### 16.4 追踪详情 Gantt 可视化

- [x] TraceStep 模型新增 `start_time_ms` 字段
- [x] API 响应新增 `start_time_ms` 和 `duration_ms`
- [x] 前端 TraceStep 类型新增时间字段
- [x] ObservabilityView.vue 实现 Gantt 可视化
- [x] 并行/串行检测逻辑（`start_time_ms < prev.time_ms`）

### 16.5 单元测试

- [x] 更新 `test_workers.py` 使用新签名（kb_tool_registry）
- [x] 更新 `test_trace.py` 使用新签名（start_ms/end_ms）
- [x] 更新 `test_admin_api.py` fixture 添加 start_time_ms
- [x] 更新 `test_copilot_service.py` 使用新签名

---

## 任务统计

| 阶段 | 任务数 | 完成 |
|------|--------|------|
| 一~十四 | 81 | 75 |
| 十五、StateGraph 多 Agent | 17 | 17 |
| 十六、fixbug-MultiAgent | 13 | 13 |
| **总计** | **111** | **105** |