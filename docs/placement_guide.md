# 放置说明

把本包里的所有内容复制到项目根目录，保持目录结构不变。

根目录应直接看到这些文件和目录：

```text
AGENTS.md
README.md
.env.example
docker-compose.yml
backend/
frontend/
data/
downloads/
media/
docs/
samples/
scripts/
.github/
```

首次启动：

```bash
cp .env.example .env
docker compose up --build
```

后端健康检查地址：`http://localhost:8031/health`

前端地址：`http://localhost:5173`
