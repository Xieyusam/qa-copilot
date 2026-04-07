# QA Copilot MVP4 - 任务拆解

## 任务执行原则

- **禁止跳步**：必须按顺序执行，完成一步确认一步
- **同步测试**：每个模块完成后立即编写/更新测试并验证
- **状态闭环**：任务完成后立即标记 `[x]`

---

## 1. 数据库基建与分类模型

### 1.1 创建 KbCategory 模型
- [x] 创建 `backend/app/models/kb_category.py`
- [x] 定义 `KbCategory` 类（id, name, description, created_at, updated_at, created_by）
- [x] 建立 `Document` 与 `KbCategory` 的关联关系

### 1.2 修改 Document 模型
- [x] 添加 `kb_category_id` 外键字段
- [x] 移除旧的 `kb_category` 字符串字段
- [x] 更新 `backend/app/models/__init__.py` 导出新模型

### 1.3 数据库迁移
- [x] 创建 Alembic 迁移脚本 `add_kb_categories_table`
- [x] 迁移逻辑：创建表 → 插入默认分类 → 修改外键
- [x] 运行迁移验证

### 1.4 单元测试
- [x] 创建 `backend/tests/test_kb_category.py`
- [x] 测试模型创建、关联查询

---

## 2. 分类管理 API（管理员专属）

### 2.1 创建分类 API
- [x] 创建 `backend/app/api/categories.py`
- [x] 实现 `GET /api/admin/categories` 获取分类列表
- [x] 实现 `POST /api/admin/categories` 创建新分类
- [x] 实现 `PUT /api/admin/categories/{id}` 更新分类
- [x] 实现 `DELETE /api/admin/categories/{id}` 删除空分类
- [x] 添加 `require_admin` 权限校验

### 2.2 文档分类 API
- [x] 修改 `GET /api/documents` 支持 `?category_id=` 筛选
- [x] 实现 `PUT /api/documents/{id}/category` 移动文档分类

### 2.3 单元测试
- [x] 创建 `backend/tests/test_category_api.py`
- [x] 测试 CRUD 操作、权限校验（403）、删除非空分类拦截

---

## 3. 动态工具生成与检索优化

### 3.1 创建工具生成器
- [x] 创建 `backend/app/services/tool_generator.py`
- [x] 实现 `ToolGenerator.build_retrieve_tools()` 动态生成工具
- [x] 工具命名规范：`retrieve_{category_name}_kb`
- [x] 工具描述包含分类用途说明

### 3.2 动态系统提示词
- [x] 修改 `backend/app/services/copilot_prompts.py`
- [x] 实现 `build_system_prompt(categories)` 动态生成
- [x] 包含知识库选择规则（优先级、适用场景）

### 3.3 重构 Copilot 服务
- [x] 修改 `backend/app/services/copilot_service.py`
- [x] `_build_agent()` 改为动态加载工具和提示词
- [x] 保留 Jira 工具不变

### 3.4 移除旧工具文件
- [x] 重构 `backend/app/services/tool_generator.py` 包含 Jira 工具
- [x] 更新 `copilot_service.py` 使用新的工具生成器

### 3.5 单元测试
- [x] 创建 `backend/tests/test_tool_generator.py`
- [x] 测试工具生成数量、命名、描述内容
- [x] 全部 165 个测试通过

---

## 4. 前端设计规范基建

### 4.1 CSS 变量定义
- [x] 创建 `frontend/src/assets/design.css`
- [x] 定义颜色体系（primary, secondary, success, warning, error）
- [x] 定义字体规范（字号、字重）
- [x] 定义间距体系（spacing-1 ~ spacing-12）
- [x] 定义圆角规范（radius-sm/md/lg）

### 4.2 工具类
- [x] 创建通用工具类（flex、间距、文本颜色等）
- [x] 滚动条美化
- [x] 代码块样式

### 4.3 基础组件库
- [x] 创建 `frontend/src/components/BaseButton.vue` 统一按钮样式
- [x] 创建 `frontend/src/components/BaseCard.vue` 统一卡片样式
- [x] 创建 `frontend/src/components/LoadingSpinner.vue` 加载动画
- [x] 创建 `frontend/src/components/EmptyState.vue` 空状态引导
- [x] 创建 `frontend/src/components/Toast.vue` 全局提示

---

## 5. 前端页面改造

### 5.1 登录/注册页面
- [x] 改造 `frontend/src/views/LoginView.vue` 应用新设计规范
- [x] 改造 `frontend/src/views/RegisterView.vue`
- [x] 添加加载状态动画、表单验证反馈

### 5.2 全局布局
- [x] 改造 `frontend/src/App.vue` 导航栏样式、页面布局

### 5.3 对话界面
- [x] 改造 `frontend/src/views/ChatView.vue` 布局优化
- [x] 改造 `frontend/src/components/ChatInterface.vue` 样式统一
- [x] 改造 `frontend/src/components/MessageBubble.vue` 消息气泡样式
- [x] 改造 `frontend/src/components/SessionList.vue` 会话列表样式
- [x] 添加过渡动效（消息出现、会话切换）

### 5.4 知识库管理页面
- [x] 改造 `frontend/src/views/KnowledgeSourcesView.vue` 整体布局
- [x] 改造 `frontend/src/components/DocumentUpload.vue` 上传区域样式
- [x] 改造 `frontend/src/components/DocumentList.vue` 文档列表样式
- [x] 添加分类筛选下拉框

### 5.5 可观测性页面
- [x] 改造 `frontend/src/views/ObservabilityView.vue` 表格/卡片样式

---

## 6. 知识库分类管理功能（前端）

### 6.1 分类管理组件
- [x] 创建 `frontend/src/components/CategoryManager.vue`
- [x] 实现分类列表展示（名称、描述、文档数）
- [x] 实现创建分类表单（名称、描述输入）
- [x] 实现编辑分类功能
- [x] 实现删除分类功能（空分类才可删除）
- [x] 添加操作反馈（Toast 提示）

### 6.2 分类选择组件
- [x] 创建 `frontend/src/components/CategorySelect.vue`
- [x] 下拉选择分类（上传文档时使用）
- [x] 支持分类筛选（文档列表）

### 6.3 API 调用层
- [x] 创建 `frontend/src/api/categories.ts`
- [x] 实现 `getCategories()` 获取分类列表
- [x] 实现 `createCategory()` 创建分类
- [x] 实现 `updateCategory()` 更新分类
- [x] 实现 `deleteCategory()` 删除分类
- [x] 实现 `moveDocumentCategory()` 移动文档

### 6.4 状态管理
- [x] 创建 `frontend/src/stores/categories.ts` Pinia store
- [x] 管理分类列表、当前选中分类

---

## 7. 路由与权限调整

### 7.1 路由守卫
- [x] 修改 `frontend/src/router/index.ts`
- [x] 知识库管理页面添加 `requiresAdmin: true` 元数据
- [x] 实现管理员路由守卫（非管理员跳转到对话页）

### 7.2 导航菜单调整
- [x] 普通用户：隐藏知识库管理、可观测性入口
- [x] 管理员：显示完整菜单

---

## 8. 测试覆盖与验证

### 8.1 后端测试
- [x] 运行全部后端测试 `pytest tests/ -v`
- [x] 确保新增测试全部通过
- [x] 更新旧测试适配新模型

### 8.2 前端验证
- [x] 启动前端开发服务器
- [x] 验证所有页面样式统一
- [x] 验证交互反馈（Toast、Loading）
- [x] 验证权限控制（普通用户/管理员）

### 8.3 端到端验证
- [x] 创建自定义分类
- [x] 上传文档到新分类
- [x] 对话测试：查询新分类内容，验证 Agent 正确调用工具
- [x] 删除空分类测试

---

## 9. 文档更新

### 9.1 更新 README
- [x] 更新 `K:\kiro-project\README.md` MVP4 功能说明

### 9.2 阶段总结
- [x] 创建 `K:\kiro-project\docs\mvp4-summary.md` 阶段总结报告

---

## 任务统计

| 模块 | 任务数 |
|------|--------|
| 1. 数据库基建 | 4 |
| 2. 分类管理 API | 3 |
| 3. 动态工具生成 | 5 |
| 4. 前端设计规范 | 3 |
| 5. 前端页面改造 | 5 |
| 6. 分类管理功能 | 4 |
| 7. 路由权限调整 | 2 |
| 8. 测试覆盖 | 3 |
| 9. 文档更新 | 2 |
| **总计** | **31** |