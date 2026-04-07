# QA Copilot MVP3 阶段性总结

## 1. 项目概述 (Overview)

MVP3 是 QA Copilot 向企业级应用演进的关键里程碑。本次升级聚焦于用户鉴权、多租户隔离、真实业务系统集成以及可观测性建设，将系统从一个"演示级知识库问答工具"升级为"生产级 AI Copilot 平台"。

### 核心功能升级回顾

- **用户鉴权与 RBAC**：完整的 JWT 认证流程，支持管理员/普通用户角色分离，实现会话与数据的租户级隔离。
- **多场景知识库隔离**：支持通用、翻译、日志等场景化知识库分类，检索时自动按场景过滤，提升回答精准度。
- **真实 Jira 集成**：基于官方 jira SDK 实现完整 API 调用能力，支持项目列表、JQL 查询、问题统计、状态转换等操作。
- **ReAct Agent 重构**：从"硬路由"升级为"自主推理+工具调用"范式，Agent 可根据用户意图自主决定调用工具或检索知识库，支持多步推理。
- **可观测性建设**：全链路追踪（Trace）记录 Agent 执行步骤与耗时，用户反馈（点赞/点踩）统计，管理员专属观测面板。

### 技术栈扩展

在 MVP2 架构基础上，本次升级引入：

| 领域 | 新增依赖 | 用途 |
|------|---------|------|
| 认证鉴权 | PyJWT, passlib[bcrypt] | JWT Token 生成/校验，密码哈希 |
| 数据库迁移 | Alembic | Schema 版本控制，平滑迁移 |
| Jira 集成 | jira >= 3.5.0 | 官方 SDK，支持 Basic Auth |
| 前端路由 | Vue Router 4 | 多页面导航，路由守卫 |
| 状态管理 | Pinia authStore | 全局认证状态，Token 注入 |

---

## 2. 技术架构与数据流 (Architecture & Data Flow)

### 核心架构演进

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Login   │  │  Chat    │  │ Knowledge│  │  Observability   │ │
│  │  Register│  │  Interface│ │  Sources │  │  (Admin Only)    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
└───────┼─────────────┼─────────────┼─────────────────┼───────────┘
        │             │             │                 │
        ▼             ▼             ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Auth Middleware                          ││
│  │         JWT验证 → 用户注入 → 角色权限检查                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                      │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │                ReAct Agent Engine                          │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │  Tools: retrieve_kb | query_jira | count_jira | ... │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                          │                                  │  │
│  │  ┌───────────┐  ┌───────────────┐  ┌───────────────────┐   │  │
│  │  │ Hybrid    │  │ Jira Client   │  │ Conversation      │   │  │
│  │  │ Retriever │  │ (Official SDK)│  │ Manager           │   │  │
│  │  └─────┬─────┘  └───────┬───────┘  └─────────┬─────────┘   │  │
│  └────────┼────────────────┼────────────────────┼─────────────┘  │
└───────────┼────────────────┼────────────────────┼────────────────┘
            ▼                ▼                    ▼
     ┌─────────────┐  ┌─────────────┐      ┌─────────────┐
     │ ChromaDB +  │  │ Jira Server │      │ SQLite +    │
     │ BM25 Index  │  │ / Cloud     │      │ Alembic     │
     └─────────────┘  └─────────────┘      └─────────────┘
```

### 关键数据流

#### 用户认证流程
1. 用户注册/登录 → 密码 bcrypt 哈希存储
2. 登录成功 → 生成 JWT Token（含 user_id, role）
3. 前端存储 Token → 请求时注入 Authorization Header
4. 后端中间件验证 Token → 注入当前用户到请求上下文
5. 权限守卫检查 role → 放行或拒绝

#### ReAct Agent 执行流程
1. 用户提问 → 加载最近 10 轮对话历史
2. LLM 分析意图 → 决定调用哪个工具
3. 工具执行（如 `count_jira_issues`）→ 返回结果
4. LLM 根据工具结果继续推理 → 可能调用更多工具
5. 生成最终回答 → 流式输出 + 记录 Trace

---

## 3. 核心设计思路与亮点 (Design Rationale & Highlights)

### 文件拆分与职责清晰化

针对 `copilot_service.py` 臃肿问题，实施了职责分离：

| 文件 | 职责 | 行数 |
|------|------|------|
| `copilot_prompts.py` | 系统提示词（中文） | ~30 |
| `copilot_tools.py` | 7 个工具定义 | ~100 |
| `copilot_service.py` | Agent 核心逻辑 | ~170 |

**收益**：主文件精简近 50%，代码更易维护与测试。

### Jira 集成采用官方 SDK

放弃自建 HTTP 封装，直接使用 `jira` 官方库：

```python
from jira import JIRA

client = JIRA(
    server=self._url,
    basic_auth=(self._username, self._password),
)
```

**收益**：
- 自动处理 ADF（Atlassian Document Format）富文本解析
- 内置重试与错误处理
- 支持 Jira Cloud 与 Server/Data Center

### 流式渲染性能优化

从 `throttle(100ms)` 升级为 `requestAnimationFrame` 调度：

```typescript
function scheduleRender(content: string) {
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = null
    // 流式中：增量超过 50 字符才更新
    if (delta >= 50 || delta < 0) {
      rawContent.value = content
    }
  })
}
```

**收益**：
- 与浏览器 60fps 刷新率同步，避免丢帧
- 减少不必要的 DOM 更新（增量阈值控制）
- 流式结束后强制完整渲染，确保内容正确

### 错误容错与数据保护

在 Copilot 服务中引入 `finally` 块确保消息始终保存：

```python
try:
    # Agent 执行逻辑
except Exception as exc:
    yield f"\n\n[系统错误: {exc}]"
finally:
    # 确保消息始终被保存，防止数据丢失
    self._conv.add_message(session_id, "user", question)
    self._conv.add_message(session_id, "assistant", assistant_text, sources=sources)
```

**收益**：即使发生异常，对话记录也不会丢失。

---

## 4. 测试覆盖情况 (Test Coverage)

| 模块 | 测试文件 | 测试数量 | 状态 |
|------|---------|---------|------|
| Jira 客户端 | `test_jira_client.py` | 15 | ✅ 全部通过 |
| Copilot 工具 | `test_copilot_tools.py` | 14 | ✅ 全部通过 |
| 追踪与反馈 | `test_trace.py` | 11 | ✅ 全部通过 |
| 管理员 API | `test_admin_api.py` | 11 | ✅ 全部通过 |
| 对话管理 | `test_conversation.py` | 10 | ✅ 全部通过 |
| 其他模块 | ... | 88 | ✅ 全部通过 |
| **总计** | | **149** | ✅ |

---

## 5. 任务完成情况 (Task Completion)

| 模块 | 任务数 | 完成状态 |
|------|--------|---------|
| 1. 数据库基建与用户体系 | 7/7 | ✅ 完成 |
| 2. 知识库隔离改造 | 2/2 | ✅ 完成 |
| 3. Jira 客户端封装 | 2/2 | ✅ 完成 |
| 4. LangGraph ReAct 重构 | 4/4 | ✅ 完成 |
| 5. 前端交互升级 | 5/5 | ✅ 完成 |
| 6. 知识源界面优化 | 3/3 | ✅ 完成 |
| 7. 知识源详情与下载 | 2/2 | ✅ 完成 |
| 8. Jira 配置外部化 | 3/3 | ✅ 完成 |
| 9. 可观测性增强 | 4/4 | ✅ 完成 |
| 10. 对话反馈功能 | 4/4 | ✅ 完成 |
| 11. 数据库迁移 | 2/2 | ✅ 完成 |
| **总计** | **38/38** | ✅ **全部完成** |

---

## 6. 当前局限与未来改进方向 (Limitations & Future Improvements)

### 知识库时效性
- **局限**：目前知识库依赖手动上传，缺乏自动化同步机制。
- **改进**：引入 APScheduler 或 Celery Beat，定时同步。

### Jira 工具扩展
- **局限**：当前仅支持查询和统计，不支持批量操作。
- **改进**：新增 `batch_update_issues`、`create_sprint` 等高级工具。

### 多语言支持
- **局限**：系统提示词已中文化，但 UI 国际化尚未实现。
- **改进**：引入 vue-i18n，支持中英文切换。

### 知识库管理
- **局限**：知识库分类硬编码为 default/translation/log。
- **改进**：支持用户自定义知识库分类，动态管理。

---

## 7. 总结

MVP3 成功实现了从"演示工具"到"生产平台"的跨越：

| 维度 | MVP2 | MVP3 |
|------|------|------|
| 用户体系 | 无认证 | JWT + RBAC |
| 数据隔离 | 全局共享 | 租户级隔离 |
| Jira 集成 | Mock 数据 | 真实 API |
| Agent 架构 | 硬路由 | ReAct 自主推理 |
| 可观测性 | 无 | Trace + Feedback |
| 代码质量 | 单文件 310 行 | 拆分后主文件 170 行 |
| 测试覆盖 | 120 用例 | 149 用例 |

系统现已具备企业级应用的基础能力，可支撑真实业务场景的 AI Copilot 需求。