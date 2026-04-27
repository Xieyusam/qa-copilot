
目前还存在的问题：
1. 刷新文档列表的按钮不应该在新的一行，应该放到上传文档按钮的右边，不管知识库是否为空都要展示。
2. {"feishu_doc_url":"https://xjmz.feishu.cn/wiki/YRorwd6wEi6N23kjomfc1ImOnTb","feishu_doc_type":"sheet","title":"test","kb_category_id":"a3bf76e1-aa8e-495f-9228-127f988adcf8","is_active":true,"sync_interval_hours":-1}这是我上传的飞书文档参数，创建后并没有看到document表有记录，只有feishu_document表有记录，这是不对的。请你结合系统日志，排查一下问题。
3. 正确的飞书导入流程应该是：用户填好信息点击导入，系统新增文档记录，并把状态设置为准备中，用户可以在前端看到文档的状态，然后创建异步的导入任务，等导入成功后把文件状态改为“就绪”，导入失败也要改状态为导入失败，提示用户重新创建导入任务。
4. 删除的逻辑有问题，调用/api/admin/categories/a3bf76e1-aa8e-495f-9228-127f988adcf8报500，请排查

请按照以上的需求制定修改计划和方案，并且同步到K:\kiro-project\.claude\specs\QA-Copilot-MVP5，每个功能都要有单元测试，单元测试通过后才算完成。

