---
name: spec-generator
description: 生成新 MVP 的 spec 文档（requirements/design/tasks 三件套）的交互式流程
type: reference
---

## 触发方式
用户要求"创建新 MVP"、"生成 spec"、"开始新子任务"时执行此流程。

## 执行流程

### 第一步：需求收集
向用户询问：
1. **MVP 名称/英文标识**（作为 `.trae/specs/<MVP_Name>` 文件夹名，如 `user-auth`）
2. **核心需求和业务目标**
停止，等待用户回复。

### 第二步：生成 requirements.md
文件路径：`.trae/specs/<MVP_Name>/requirements.md`

格式：
```markdown
# 需求文档

## 简介
（MVP 目标和主要功能简述）

## 词汇表
（领域专属词汇及解释）

## 需求
### 需求 X：<需求名称>
**用户故事：** 作为一名...我希望...以便...
#### 验收标准
1. THE System SHALL... / WHEN... / IF... THEN...
```

完成后询问用户是否进入设计阶段。停止，等待确认。

### 第三步：生成 design.md
文件路径：`.trae/specs/<MVP_Name>/design.md`

格式：
```markdown
# 技术设计文档：<MVP_Name>

## Overview
（技术栈概述）

## Architecture
（**必须包含 Mermaid graph TB 流程图**）

## Components and Interfaces
（前后端组件、API 接口、数据模型）
```

完成后询问用户是否进入任务拆解阶段。停止，等待确认。

### 第四步：生成 tasks.md
文件路径：`.trae/specs/<MVP_Name>/tasks.md`

格式：
```markdown
# 实现计划：<MVP_Name>

## 概述
（一句话总结）

## 任务
- [ ] 1. <主任务> _需求：1, 2_
  - [ ] 1.1 <子任务> _需求：1.1_
```

完成后通知用户 spec 文档已就绪。

## 注意事项
- **必须一步一步交互生成**，不可一次性生成三个文件
- 输出语言为**中文**
- 严格遵循格式规范，不可遗漏词汇表、验收标准语法、Mermaid 图表、需求映射