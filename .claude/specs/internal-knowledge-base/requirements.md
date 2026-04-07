# 需求文档

## 简介

内部知识库应用，支持用户上传文档并通过 RAG（检索增强生成）技术对文档内容进行智能问答。系统具备多轮对话上下文记忆能力，能够结合历史对话和检索到的文档片段生成准确、连贯的回答。

前端采用 Vue3，后端采用 Python，核心功能基于 RAG 架构实现。

## 词汇表

- **System**：整个内部知识库应用系统
- **Document_Uploader**：负责接收、解析和存储用户上传文档的模块
- **Document_Parser**：负责将各类文档格式解析为纯文本的模块
- **Chunker**：负责将文档文本切分为语义片段（Chunk）的模块
- **Embedder**：负责将文本片段转换为向量表示的模块
- **Vector_Store**：负责存储和检索向量化文档片段的模块
- **Retriever**：负责根据用户查询检索相关文档片段的模块
- **LLM_Client**：负责调用大语言模型生成回答的模块
- **Conversation_Manager**：负责管理用户对话历史和上下文的模块
- **Chat_Interface**：前端对话交互界面组件
- **Knowledge_Base**：用户上传的文档集合及其向量化索引
- **Chunk**：文档被切分后的语义片段单元
- **Session**：用户的一次完整对话会话
- **User**：使用本系统的内部员工

---

## 需求

### 需求 1：文档上传

**用户故事：** 作为一名内部员工，我希望能够上传自己的文档，以便系统能够基于这些文档回答我的问题。

#### 验收标准

1. THE System SHALL 提供文档上传入口，支持用户通过前端界面选择并上传文件。
2. WHEN 用户上传文件时，THE Document_Uploader SHALL 校验文件格式，仅接受 PDF、DOCX、TXT、Markdown 格式的文件。
3. IF 用户上传的文件格式不受支持，THEN THE Document_Uploader SHALL 返回包含支持格式列表的错误提示信息。
4. IF 用户上传的文件大小超过 50MB，THEN THE Document_Uploader SHALL 拒绝上传并提示文件大小限制。
5. WHEN 文件上传成功后，THE System SHALL 在前端展示上传进度，并在完成后显示文档处理状态。
6. THE System SHALL 支持用户查看已上传的文档列表，包含文档名称、上传时间和处理状态。
7. WHEN 用户请求删除已上传文档时，THE System SHALL 同时删除该文档的原始文件及其对应的向量索引数据。

---

### 需求 2：文档解析与向量化

**用户故事：** 作为一名内部员工，我希望上传的文档能够被自动处理并建立索引，以便系统能够准确检索文档内容。

#### 验收标准

1. WHEN 文档上传完成后，THE Document_Parser SHALL 自动将文档内容解析为纯文本，保留段落结构信息。
2. WHEN 文档解析完成后，THE Chunker SHALL 将文本切分为不超过 512 个 token 的语义片段，相邻片段之间保留 50 个 token 的重叠。
3. WHEN 文本切分完成后，THE Embedder SHALL 将每个 Chunk 转换为向量表示并存入 Vector_Store。
4. IF 文档解析过程中发生错误，THEN THE Document_Parser SHALL 记录错误日志并将文档状态标记为"解析失败"，同时通知用户。
5. THE Document_Parser SHALL 支持解析 PDF、DOCX、TXT、Markdown 四种格式，并为每种格式提取正文文本内容。
6. FOR ALL 已成功向量化的文档，THE Vector_Store SHALL 保证在文档被删除后其对应的所有 Chunk 向量数据同步删除（一致性保证）。

---

### 需求 3：智能问答（RAG）

**用户故事：** 作为一名内部员工，我希望能够用自然语言提问，系统根据知识库文档内容给出准确回答。

#### 验收标准

1. WHEN 用户提交问题时，THE Retriever SHALL 在 Vector_Store 中检索与问题语义最相关的前 5 个 Chunk。
2. WHEN 检索完成后，THE LLM_Client SHALL 将检索到的 Chunk 内容与用户问题组合为 Prompt，调用大语言模型生成回答。
3. THE LLM_Client SHALL 在生成的回答中标注所引用的文档来源（文档名称及片段位置）。
4. IF Vector_Store 中不存在与用户问题相关的文档内容（相似度低于阈值），THEN THE System SHALL 告知用户当前知识库中未找到相关内容，并建议用户上传相关文档。
5. WHEN 用户提交问题后，THE Chat_Interface SHALL 在 3 秒内展示"正在思考"状态提示，并在回答生成完成后流式展示回答内容。
6. THE System SHALL 支持流式输出（Streaming），逐步将 LLM 生成的回答推送至前端展示。

---

### 需求 4：多轮对话上下文记忆

**用户故事：** 作为一名内部员工，我希望系统能够记住我们对话的上下文，以便我可以进行连续追问而无需重复背景信息。

#### 验收标准

1. THE Conversation_Manager SHALL 为每个用户维护独立的 Session，记录该 Session 内的完整对话历史。
2. WHEN 用户在同一 Session 内提交新问题时，THE LLM_Client SHALL 将最近 10 轮对话历史与当前问题一同传入 Prompt，以保持上下文连贯性。
3. WHILE Session 处于活跃状态，THE Conversation_Manager SHALL 保持对话历史可访问，直到用户主动清除或 Session 超时（默认超时时间为 30 分钟）。
4. WHEN 用户请求清除对话历史时，THE Conversation_Manager SHALL 清空当前 Session 的所有对话记录，并开始新的对话轮次。
5. IF Session 超时，THEN THE Conversation_Manager SHALL 自动清除该 Session 的对话历史，并在用户下次提问时开始新的 Session。
6. THE System SHALL 支持用户在前端查看当前 Session 的历史对话记录。

---

### 需求 5：文档解析器的正确性（解析-打印往返）

**用户故事：** 作为一名开发者，我希望文档解析模块具备可验证的正确性，以便确保文档内容在处理过程中不丢失关键信息。

#### 验收标准

1. THE Document_Parser SHALL 将各格式文档解析为统一的内部文本表示（ParsedDocument 对象）。
2. FOR ALL 有效的 ParsedDocument 对象，THE Document_Parser SHALL 支持将其序列化为 JSON 格式，并能从该 JSON 反序列化还原为等价的 ParsedDocument 对象（往返属性）。
3. WHEN 对同一文档执行两次解析时，THE Document_Parser SHALL 产生内容等价的 ParsedDocument 对象（幂等性）。
4. IF 输入文档内容为空，THEN THE Document_Parser SHALL 返回包含空内容字段的 ParsedDocument 对象，而非抛出异常。

---

### 需求 7：文档删除二次确认

**用户故事：** 作为一名内部员工，我希望删除文档时有二次确认，避免误操作导致数据丢失。

#### 验收标准

1. WHEN 用户点击删除文档按钮时，THE System SHALL 弹出确认对话框，展示文档名称并要求用户确认删除操作。
2. IF 用户取消确认，THEN THE System SHALL 关闭对话框，不执行任何删除操作。
3. WHEN 用户确认删除后，THE System SHALL 显示删除中的 loading 状态，禁止重复点击。
4. WHEN 删除操作完成后，THE System SHALL 通过 Toast 通知告知用户删除结果（成功或失败）。

---

### 需求 8：多会话历史管理

**用户故事：** 作为一名内部员工，我希望能够查看和切换历史对话，以便回顾之前的问答内容，并能随时开启新的对话。

#### 验收标准

1. THE System SHALL 在问答页面左侧展示历史会话列表，每条记录显示会话标题（取首条用户消息的前 20 字）和创建时间。
2. WHEN 用户点击历史会话列表中的某条记录时，THE System SHALL 切换到该会话并加载其完整对话历史。
3. THE System SHALL 提供"新建会话"按钮，点击后创建新的空白会话并切换到该会话。
4. WHEN 用户进入问答页面时，THE System SHALL 自动加载最近一次的历史会话；若无历史会话，则自动创建新会话。
5. THE System SHALL 将会话元数据（session_id、标题、创建时间、最后活跃时间）持久化存储，确保刷新页面后历史会话不丢失。
6. WHEN 用户在某会话中发送消息后，THE System SHALL 更新该会话在列表中的最后活跃时间，并将其排列在列表顶部。
7. THE System SHALL 支持用户删除单条历史会话记录，删除后从列表中移除。

---

### 需求 6：系统安全与访问控制（后续优化）

> **说明：** 当前版本为个人知识库应用，暂不实现此模块。以下需求保留作为后续迭代参考。

**用户故事：** 作为系统管理员，我希望知识库仅对内部员工开放，以防止未授权访问。

#### 验收标准

1. THE System SHALL 要求用户在访问任何功能前完成身份认证。
2. WHEN 未认证用户尝试访问受保护资源时，THE System SHALL 返回 401 状态码并重定向至登录页面。
3. THE System SHALL 确保每个用户只能访问自己上传的文档及对应的对话历史，不能访问其他用户的数据。
4. IF 用户连续 5 次认证失败，THEN THE System SHALL 锁定该账户 15 分钟，并记录安全日志。
