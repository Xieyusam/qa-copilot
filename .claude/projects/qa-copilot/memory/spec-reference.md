---
name: Spec Directory
description: Spec 驱动开发的规范文件位置和结构
type: reference
---

**Spec 路径基准**: `.claude/specs/<MVP_Name>/`

**三件套文件**:
- `requirements.md` — 需求定义、验收标准
- `design.md` — 技术架构、组件接口、数据模型
- `tasks.md` — 任务拆解、执行进度追踪

**当前 MVP 目录**: `.claude/specs/QA-Copilot-MVP4/`

**Why**: 所有代码实现必须基于 Spec，这是项目的核心开发纪律。

**How to apply**: 在开始任何开发工作前，先读取对应 MVP 的三件套文件；如果文件不存在，要求补全 Spec 再开发。