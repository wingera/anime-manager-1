# 数据库表结构

| 表名 | 用途 |
| --- | --- |
| sources | 保存授权来源配置 |
| resources | 保存识别出的资源指纹和处理状态 |
| metadata_matches | 保存影视资料匹配结果 |
| download_tasks | 保存下载器任务映射和下载状态 |
| media_files | 保存下载任务内的文件分析结果 |
| import_records | 后续阶段保存入库和回滚记录 |
| settings | 后续阶段保存网页设置 |
| audit_logs | 后续阶段保存关键操作日志 |

主键统一为 `id`，创建时间统一为 `created_at`，更新时间统一为 `updated_at`，软删除统一为 `deleted_at`。
