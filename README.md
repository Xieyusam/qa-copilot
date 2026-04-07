# QA Copilot

基于 LangGraph ReAct 架构的企业级 AI Copilot，支持多意图智能路由、多场景知识库隔离、真实 Jira 集成、用户鉴权与权限控制。系统通过 ReAct 范式实现多步工具调用与知识库检索的深度融合。

## 核心特性

### MVP4 新增特性

- **自定义知识库分类管理**：支持管理员动态创建、编辑、删除知识库分类
- **动态工具生成**：根据数据库分类自动生成检索工具，Agent 自动选择正确知识库
- **前端设计规范**：统一的颜色体系、字体规范、间距体系、组件库
- **交互体验增强**：Toast 提示、Loading 动画、空状态引导、过渡动效

### MVP3 新增特性

- **用户鉴权与权限控制**：JWT 认证 + RBAC 角色（admin/user），会话与数据隔离
- **多场景知识库隔离**：支持通用、翻译、日志等分类知识库，检索时按场景过滤
- **真实 Jira 集成**：支持项目列表、JQL 查询、问题统计、状态转换等完整功能
- **ReAct Agent 重构**：基于 LangGraph 的多步推理与工具调用，支持多意图识别
- **可观测性增强**：执行追踪（Trace）与用户反馈（Feedback）统计面板
- **流式渲染优化**：requestAnimationFrame + 增量更新，确保长文本流畅渲染

### 基础功能

- **混合检索架构**：ChromaDB 向量检索 + BM25 关键词检索 + RRF 融合重排
- **多格式文档解析**：PDF、DOCX、TXT、Markdown、Excel
- **智能语义切分**：Markdown 标题切分、递归字符切分、Excel 结构化展开
- **流式对话体验**：SSE Token 级打字机效果，支持中断与重新生成
- **知识溯源可视化**：Top-K 片段展示 + 相似度百分比 + 低相关性警告

## 技术栈

### 前端
- Vue 3 + TypeScript + Vite
- Pinia（状态管理）+ Vue Router 4（多页面路由）
- Tailwind CSS（响应式设计）
- marked + DOMPurify（Markdown 安全渲染）
- Fetch API + AbortController（流式中断控制）

### 后端
- Python 3.11 + FastAPI
- SQLAlchemy 2.0 + SQLite + Alembic（数据库迁移）
- LangChain >= 1.0.0 + LangGraph >= 1.0.0（ReAct Agent）
- PyJWT + passlib（JWT 认证 + 密码哈希）
- jira >= 3.5.0（Jira 官方 SDK）

### 混合检索与向量库
- ChromaDB（本地持久化向量检索）
- rank_bm25（本地 BM25 倒排索引）
- RRF 倒数秩融合（纯数学重排打分）
- 支持 OpenAI Embeddings 或本地 sentence-transformers

### LLM 支持
- 兼容 OpenAI API 格式的任意模型
- 流式输出（SSE）+ 中断控制
- ReAct 多步推理 + 工具自主调用

## 快速启动

### 方式一：本地脚本启动

#### Windows (PowerShell)
```powershell
# 首次运行需允许脚本执行
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 启动前端 + 后端
.\dev.ps1

# 杀掉已有进程后重启
.\dev.ps1 -Restart
```

#### Mac / Linux (Bash)
```bash
chmod +x dev.sh
./dev.sh
```

### 方式二：手动启动

#### 后端
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填写配置

uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

访问：
- 前端：http://localhost:5173
- API 文档：http://localhost:8008/docs

## 环境变量配置

```env
# LLM 配置
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-4o-mini

# Embedding 配置
EMBEDDING_BACKEND=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2

# JWT 配置
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Jira 配置（可选）
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_PASSWORD=your-api-token-or-password
```

## 目录结构

```
.
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 路由（auth, chat, documents, admin, categories）
│   │   ├── core/          # 核心数据结构（schemas, security）
│   │   ├── db/            # 数据库配置与会话管理
│   │   ├── models/        # SQLAlchemy ORM 模型
│   │   ├── services/      # 业务逻辑服务
│   │   │   ├── copilot_service.py   # ReAct Agent 服务
│   │   │   ├── tool_generator.py    # 动态工具生成器
│   │   │   ├── copilot_prompts.py   # 系统提示词
│   │   │   ├── jira_client.py       # Jira 客户端
│   │   │   ├── hybrid_retriever.py  # 混合检索引擎
│   │   │   └── ...
│   │   ├── config.py      # 环境变量配置
│   │   └── main.py        # FastAPI 应用入口
│   ├── alembic/           # 数据库迁移脚本
│   ├── tests/             # 单元测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # API 调用模块
│   │   ├── assets/        # 静态资源与设计规范（design.css）
│   │   ├── components/    # Vue 组件（含 BaseButton, Toast 等基础组件）
│   │   ├── stores/        # Pinia 状态管理（auth, chat, documents, categories）
│   │   ├── views/         # 页面组件
│   │   └── types/         # TypeScript 类型定义
│   └── package.json
└── docs/                  # 文档
```

## 支持的文档格式

| 格式 | 扩展名 | 解析方式 |
|------|--------|---------|
| PDF | `.pdf` | PyMuPDF |
| Word | `.docx` | python-docx |
| 文本 | `.txt` | 原生读取 |
| Markdown | `.md` | 标题语义切分 |
| Excel | `.xlsx`, `.xls` | pandas 结构化展开 |

文件大小限制：50MB

## Jira 工具能力

| 工具 | 功能 | 使用场景 |
|------|------|---------|
| `list_jira_projects` | 获取所有项目列表 | "查看所有 Jira 项目" |
| `query_jira` | JQL 查询问题列表 | "查询未解决的问题" |
| `count_jira_issues` | 统计问题数量 | "PROJ-123 有多少未解决问题" |
| `get_jira_issue` | 获取问题详情 | "查看 PROJ-123 详情" |

## 测试

```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

当前测试覆盖：165 个测试用例全部通过

## 许可证

MIT