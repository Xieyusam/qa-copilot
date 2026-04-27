# QA Copilot 项目规范

---

## 项目概览

**技术栈**：
- 后端：FastAPI + LangGraph + SQLAlchemy + ChromaDB + BM25
- 前端：Vue 3 + Tailwind CSS + Pinia + Fetch API
- 数据库：SQLite + Alembic 迁移

**当前 MVP**：QA-Copilot-MVP5
**Spec 路径**：`.claude/specs/QA-Copilot-MVP5/`

---

## Spec 驱动开发

本项目采用 **Spec 驱动开发** 模式，所有代码实现必须基于 `.claude/specs/` 目录下的规范进行。

### 核心规则

- **No Spec, No Code**：如果对应的 MVP 文件夹或三件套文件不存在，拒绝编写业务代码
- **禁止脱离 Spec 凭空发挥或过度设计**
- **禁止跳步**：不允许一次性实现多个复杂步骤，必须做完一步确认一步

### 三件套（开发前置必读）

在编写或修改任何代码前，必须先完整读取当前 MVP 目录下的三个核心文件：

| 文件 | 作用 |
|------|------|
| `requirements.md` | 需求定义 - 明确业务目标和功能边界，遵守 KISS 和 YAGNI 原则 |
| `design.md` | 技术设计 - 系统架构、数据模型、API 接口规范和组件拆分方案 |
| `tasks.md` | 任务拆解 - 开发的唯一执行路径，按顺序小步执行 |

### 标准执行流

1. **Context 载入**：确认当前 MVP 任务，读取三件套
2. **任务锁定**：从 `tasks.md` 中选取当前需要执行的具体步骤
3. **编码与测试同步**：必须同步编写或更新对应的单元测试
4. **状态闭环**：任务编码和测试通过后，第一时间回到 `tasks.md` 将对应项标记为 `[x]`

---

## 前端规范

### API 请求规范

**统一使用 Fetch API，禁止使用 axios**。所有请求必须通过 `src/api/request.ts` 中的 `request()` 函数（自动携带 Token）。

```typescript
// ✅ 正确
import { request } from '../api/request'
const response = await request('/api/xxx')
const data = await response.json()

// ❌ 错误
import axios from 'axios'
```

---

## 后端规范

### 服务启动与重启

**使用 `dev.ps1` 管理前后端服务**，禁止手动启动或重启。

```powershell
# 重启所有服务（前后端）
.\dev.ps1 -Restart

# 仅重启后端
.\dev.ps1 -Restart -Backend

# 仅重启前端
.\dev.ps1 -Restart -Frontend

# 前端热重载（不重启后端）
.\dev.ps1 -Reload -Frontend
```

### 虚拟环境强制要求

- 在进行任何后端操作前，**必须**确保已激活 Python 虚拟环境（`backend/.venv`）
- **禁止全局污染**：绝对禁止在全局 Python 环境中执行 `pip install` 或运行项目代码

```bash
# 激活虚拟环境
cd backend && source .venv/bin/activate  # Mac/Linux
cd backend && .\.venv\Scripts\activate   # Windows
```

### 依赖变更审批

- 升级/降级/引入新依赖前，**必须事先向用户提出方案并征得同意**
- 严禁擅自修改 `requirements.txt` 或隐式引入新依赖

---

## Skills（交互式流程）

### 创建新 MVP Spec

当需要创建新的 MVP 时，对我说"创建新 MVP"或"生成 spec"，我会执行以下流程：

1. 收集 MVP 名称和需求
2. 生成 `requirements.md`（需求文档）
3. 生成 `design.md`（技术设计，含 Mermaid 架构图）
4. 生成 `tasks.md`（任务拆解）

流程会一步一步交互进行，每个阶段需要你确认后才会继续。

### 代码审查

当需要检查代码质量时，对我说"review 代码"或"检查完成情况"，我会执行 code-review 流程：
- 基于 git diff 增量审查（如有变更）
- 对照 spec 检查任务完成情况
- 检查代码质量（类型、异常处理、测试覆盖）
- 输出评分报告和优先修复建议

---

## 行为准则

1. 行动前先思考，写代码前先阅读已有文件
2. 输出要简洁，但推理要彻底
3. 优先编辑而不是重写整个文件
4. 不要重复阅读已经读过的文件
5. 在宣布完成前测试你的代码
6. 不要有奉承的开场白或结束语
7. 保持解决方案简单直接
8. **用户指令始终覆盖此文件**

---

## 交流语言

- **请用中文回复**
- **代码注释请用中文**
