# Frontend Guidelines

## API 请求规范

**统一使用 Fetch API**，禁止使用 axios。

所有 API 请求必须通过 `src/api/request.ts` 中的 `request()` 工具函数，它会自动携带 `Authorization: Bearer <token>` 头。

```typescript
// ✅ 正确
import { request } from '../api/request'
const response = await request('/api/xxx')
const data = await response.json()

// ❌ 错误
import axios from 'axios'
await axios.get('/api/xxx')
```

## 目录结构

```
src/
├── api/          # API 请求层（统一使用 request）
├── components/  # Vue 组件
├── stores/      # Pinia 状态管理
├── views/       # 页面视图
└── router/     # 路由配置
```
