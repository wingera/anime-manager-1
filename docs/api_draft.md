# 接口草图

所有接口返回给前端的提示必须是中文。接口路径使用英文专业名词，方便长期维护。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 后端健康检查 |
| GET | `/sources` | 查询来源列表 |
| POST | `/sources` | 新增授权来源 |
| PATCH | `/sources/{source_id}` | 修改来源 |
| POST | `/sources/{source_id}/test` | 测试来源识别 |
| GET | `/resources` | 查询资源任务 |
| POST | `/resources/manual` | 手动添加资源指纹 |
| POST | `/resources/{resource_id}/review` | 人工确认资源 |
| POST | `/metadata/search` | 搜索影视资料 |
| POST | `/metadata/match` | 计算匹配候选 |
| GET | `/downloads` | 查询下载队列 |
| POST | `/downloads/{task_id}/pause` | 暂停下载 |
| POST | `/downloads/{task_id}/resume` | 继续下载 |
| POST | `/files/{task_id}/analyze` | 分析任务内文件 |
| GET | `/imports/preview/{task_id}` | 生成命名预览 |
| POST | `/imports/execute/{task_id}` | 执行入库 |
| POST | `/imports/{record_id}/rollback` | 回滚入库 |
| GET | `/settings` | 查询系统设置 |
| PATCH | `/settings` | 保存系统设置 |
| POST | `/settings/test-qbittorrent` | 测试下载器连接 |
| POST | `/settings/test-tmdb` | 测试影视资料连接 |
