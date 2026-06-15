# 番剧自动整理管家

番剧自动整理管家用于接入用户有权使用的资源来源，识别 40 位资源指纹，辅助完成资料匹配、下载任务创建、文件分析、命名预览、人工入库和回滚记录。项目不内置任何默认来源，也不会自动下载或自动入库。

## 当前功能

- 系统设置：配置 TMDB、qBittorrent、下载目录、媒体库目录和匹配阈值。
- 首次安装向导：引导填写 TMDB、qBittorrent、下载目录、媒体库目录和匹配阈值。
- 备份恢复：导出和导入非敏感配置，密钥和密码不会明文写入备份。
- 系统诊断：检查目录、外部工具、下载器配置、资料库配置、数据库和密钥状态。
- 来源管理：由用户手动添加授权来源，测试来源时只做预览，不默认创建下载任务。
- 资源库：保存 40 位资源指纹，重复指纹不会重复创建。
- 资料匹配：搜索并保存电视剧资料匹配结果，低可信结果需要人工确认。
- 下载队列：下载任务需要用户手动创建，提交到 qBittorrent 后默认暂停。
- 文件分析：读取下载器文件清单，识别正片、字幕和无关文件。
- 命名预览：先生成目标路径和冲突提示，再允许执行入库。
- 入库记录：支持硬链接、复制和回滚本系统创建的入库目标文件。
- 运行日志：记录设置、来源、匹配、下载、分析、命名预览、入库和回滚等关键动作。
- 任务看板：展示来源、资源、匹配、下载、文件、命名预览、入库和最近日志统计。

## 技术栈

后端：Python 3.13.x、FastAPI、Pydantic v2、SQLAlchemy 2.x、SQLite、Alembic、APScheduler、httpx、pytest、ruff、mypy。

前端：Node.js 24、Vue 3、TypeScript、Vite、Pinia、Vue Router、Element Plus、vue-tsc、ESLint、Prettier。

外部能力：ffprobe 用于视频信息分析，qBittorrent Web API 用于下载器对接，TMDB API 用于影视资料查询，Docker Compose 用于本地部署。

## 启动命令

```bash
cp .env.example .env
docker compose up -d --build
```

前端地址：`http://localhost:5173`

后端健康检查：`http://localhost:8031/health`

常用页面：

- 首次安装向导：`/setup`
- 备份恢复：`/backup`
- 系统诊断：`/diagnostics`

## 密钥说明

生产部署建议在 `.env` 中设置 `SECRET_KEY`，值应为 Fernet 密钥。未设置时，后端会自动生成开发密钥并写入 `data/secret.key`。

`data/secret.key` 用于解密数据库中保存的 TMDB API 密钥和 qBittorrent 密码，不要提交到 Git，也不要公开给他人。

迁移到新机器时：

1. 复制项目代码。
2. 复制 `.env` 或 `data/secret.key`，确保可以解密原有敏感配置。
3. 复制 `data/app.db`。
4. 复制或重新挂载媒体库目录和下载目录。

## 本地检查

```bash
bash scripts/local_check.sh
```

## 全流程验收

```bash
bash scripts/e2e_check.sh
```

脚本会检查 Docker Compose 配置，构建并启动服务，访问健康检查和核心 API，然后运行后端 `pytest`、`ruff`、`mypy` 与前端构建。

## 重要边界

- 不内置默认来源，来源只能由用户在网页中手动添加。
- 不添加成人站点、盗版站点、磁力默认来源或绕过访问限制逻辑。
- 下载任务需要用户手动创建，系统不允许自动下载。
- 入库需要用户手动执行，系统不允许自动入库。
- 默认不删除原文件。
- 支持回滚本系统创建的入库目标文件，不回滚或删除用户原始下载文件。
- 网页文案、错误提示、接口 message 和运行日志均使用中文。
- 不在日志、接口返回或前端状态中明文显示密钥、密码或完整敏感链接。
