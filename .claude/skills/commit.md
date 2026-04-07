# Git Commit Skill

## Triggers
- `/git-commit`
- `提交代码`
- `创建提交`

## Description
分析当前代码改动，生成符合 Conventional Commits 规范的提交信息，并执行提交。

## Behavior
1. **分析改动**: 执行 `git status` 和 `git diff --stat` 分析当前暂存和未暂存的改动
2. **生成提交信息**: 基于改动内容，生成符合 Conventional Commits 规范的消息
   - 格式: `type(scope): description`
   - type 可选值: `feat`(新功能), `fix`(修复), `docs`(文档), `style`(格式), `refactor`(重构), `test`(测试), `chore`(杂项)
3. **展示确认**: 显示生成的提交信息供用户确认
4. **执行提交**: 用户确认后执行 `git commit`

## Example Session
```
User: /git-commit
Assistant:
  ## 当前代码改动分析

  **已暂存:**
  - M backend/app/services/copilot_prompts.py

  **改动统计:**
  - backend/app/services/copilot_prompts.py: +15 -3

  ## 生成的提交信息

  ```
  feat(copilot): enhance prompt generation logic
  ```

  是否确认提交？(yes/no)

User: yes
Assistant:
  执行 `git commit -m "feat(copilot): enhance prompt generation logic"`

  ✅ 提交成功！
```

## Commit Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type 规则
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档变更
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不属于 fix 或 feat）
- `test`: 测试相关
- `chore`: 杂项（构建、工具、依赖更新等）

### Scope 规则
- 使用受影响的主要模块（如 `auth`, `api`, `db`, `ui`, `copilot` 等）
- 如无明确模块，使用 `core`
- 多个受影响模块用 `/` 分隔（如 `auth/api`）

### Description 规则
- 使用祈使句："add" 而不是 "added" 或 "adds"
- 首字母小写
- 不使用句号结尾
- 控制在 72 字符以内
