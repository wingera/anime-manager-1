# 番剧自动整理管家

这是项目开工前的标准命名骨架，用来统一技术栈、目录、接口、页面、数据库、样例数据和本地检查方式。当前骨架只包含准备文件和健康检查接口，不包含任何默认来源，也不会内置未授权站点。

## 技术栈

后端：Python 3.13.x、FastAPI、Pydantic v2、SQLAlchemy 2.x、SQLite、Alembic、APScheduler、httpx、pytest、ruff、mypy。

前端：Node.js 24、Vue 3、TypeScript、Vite、Pinia、Vue Router、Element Plus、vue-tsc、ESLint、Prettier。

外部能力：ffprobe 用于视频信息分析，qBittorrent Web API 用于下载器对接，TMDB API 用于影视资料查询，Docker Compose 用于本地部署。

## 放置方式

把本包里的文件按目录原样放到项目根目录。根目录需要包含：`AGENTS.md`、`README.md`、`.env.example`、`docker-compose.yml`、`backend/`、`frontend/`、`data/`、`downloads/`、`media/`、`docs/`、`samples/`、`scripts/`、`.github/`。

## 首次启动

```bash
cp .env.example .env
docker compose up --build
```

前端地址：`http://localhost:5173`

后端健康检查：`http://localhost:8031/health`

## 开工顺序

先确认 `AGENTS.md`，再执行数据库迁移，然后完成设置中心和下载器连接测试，最后再做来源、匹配、下载、分析、入库流程。

## 重要边界

来源只能通过网页添加授权来源。系统不得硬编码具体站点为默认来源，不写绕过访问限制、绕过登录、绕过反爬、规避版权限制、自动抓取成人或高风险内容的代码。
