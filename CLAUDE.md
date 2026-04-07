# QA Copilot Project

## Spec-Driven Development

本项目严格采用 **Spec 驱动开发** 模式。

### 核心规则
- 所有代码实现必须且只能基于 `.claude/specs/` 目录下的规范进行
- **禁止脱离 Spec 凭空发挥或过度设计**
- **No Spec, No Code**: 如果对应的 MVP 文件夹或三件套文件不存在，拒绝编写业务代码

### 开发前置必读 (The 3 Pillars)
在编写或修改任何代码前，必须先完整读取当前 MVP 目录下的核心三件套：
1. **`requirements.md`**: 需求定义 - 明确业务目标和功能边界，遵守 KISS 和 YAGNI 原则
2. **`design.md`**: 技术设计 - 系统架构、数据模型、API 接口规范和组件拆分方案
3. **`tasks.md`**: 任务拆解 - 开发的唯一执行路径，按 Todo 列表顺序小步执行

### 标准执行流
1. **Context 载入**: 确认当前 MVP 任务，读取对应的三件套 Markdown 文件
2. **任务锁定**: 从 `tasks.md` 中选取当前需要执行的具体步骤
3. **编码与测试同步**: 必须同步编写或更新对应的单元测试，局部功能完成后立即运行测试验证
4. **状态闭环**: 任务一旦编码和测试通过，**必须第一时间回到 `tasks.md` 将对应项标记为 `[x]`**

### 纪律红线
- **禁止跳步**: 不允许一次性实现 `tasks.md` 中的多个复杂步骤，必须做完一步确认一步

---

## Backend Environment Rules

### 虚拟环境强制要求
- 在进行任何后端操作前，**必须**确保已激活 Python 虚拟环境 (`backend/.venv`)
- **禁止全局污染**: 绝对禁止在全局 Python 环境中执行 `pip install` 或运行项目代码

### 激活环境
```bash
cd backend && source .venv/bin/activate  # Mac/Linux
cd backend && .\.venv\Scripts\activate   # Windows
```

### 依赖变更审批
- 升级/降级/引入新依赖前，**必须事先向用户提出方案并征得同意**
- 严禁擅自修改 `requirements.txt` 或隐式引入新依赖

---

## Current MVP Status

**当前 MVP**: QA-Copilot-MVP4 (进行中)

**Spec 路径**: `.claude/specs/QA-Copilot-MVP4/`

**核心功能**:
- 用户鉴权、会话隔离与权限控制 (RBAC)
- Jira 工具真实集成
- 多场景专属知识库隔离
- 多意图与多步工具调用 (ReAct 升级)
- 数据库版本控制 (Alembic)

---

## Tech Stack

**后端**: FastAPI + LangGraph + SQLAlchemy + ChromaDB + BM25

**前端**: Vue 3 + Tailwind CSS + Pinia + Axios

**数据库**: SQLite + Alembic 迁移

---

## Skills (交互式流程)

### 创建新 MVP Spec
当需要创建新的 MVP 时，告诉我："创建新 MVP" 或 "生成 spec"，我会执行 spec-generator 流程：
1. 收集 MVP 名称和需求
2. 生成 requirements.md（需求文档）
3. 生成 design.md（技术设计，含 Mermaid 架构图）
4. 生成 tasks.md（任务拆解）

流程会一步一步交互进行，每个阶段需要你确认后才会继续。

### 代码审查
当需要检查代码质量时，告诉我："review 代码" 或 "检查完成情况"，我会执行 code-review 流程：
- 基于 git diff 增量审查（如有变更）
- 对照 spec 检查任务完成情况
- 检查代码质量（类型、异常处理、测试覆盖）
- 输出评分报告和优先修复建议