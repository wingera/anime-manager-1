#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_BASE="http://127.0.0.1:8031"
PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.13 >/dev/null 2>&1; then
    PYTHON_BIN="python3.13"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "未找到 Python，请先安装 Python 3.13"
    exit 1
  fi
fi
BACKEND_VENV="${TMPDIR:-/tmp}/anime_manager_backend_e2e_venv"

echo "开始全流程验收：检查 Docker Compose 配置"
docker compose config >/tmp/anime_manager_compose_config.txt
echo "Docker Compose 配置检查通过"

echo "开始构建并启动服务"
docker compose up -d --build

echo "等待后端健康检查"
for attempt in {1..30}; do
  if curl -fsS "$API_BASE/health" >/tmp/anime_manager_health.json; then
    echo "后端健康检查通过"
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "后端健康检查超时"
    exit 1
  fi
  sleep 1
done

check_api() {
  local path="$1"
  local output_file="/tmp/anime_manager_${path//\//_}.json"
  echo "检查接口：${path}"
  curl -fsS "${API_BASE}${path}" >"$output_file"
}

check_api "/api/settings"
check_api "/api/sources"
check_api "/api/source-items"
check_api "/api/matches"
check_api "/api/downloads"
check_api "/api/imports"
check_api "/api/logs"
check_api "/api/dashboard/summary"
check_api "/api/setup/status"
check_api "/api/backup/export"
check_api "/api/diagnostics"

echo "开始后端 pytest、ruff、mypy 检查"
cd "$ROOT_DIR/backend"
"$PYTHON_BIN" -m venv "$BACKEND_VENV"
"$BACKEND_VENV/bin/python" -m pip install -q \
  "fastapi>=0.115.0" \
  "uvicorn[standard]>=0.30.0" \
  "pydantic-settings>=2.5.0" \
  "sqlalchemy>=2.0.0" \
  "alembic>=1.13.0" \
  "apscheduler>=3.10.0" \
  "httpx>=0.27.0" \
  "cryptography>=43.0.0" \
  "pytest>=8.0.0" \
  "pytest-asyncio>=0.23.0" \
  "ruff>=0.6.0" \
  "mypy>=1.11.0"
"$BACKEND_VENV/bin/pytest"
"$BACKEND_VENV/bin/ruff" check .
rm -rf .mypy_cache
"$BACKEND_VENV/bin/mypy" .

echo "开始前端构建检查"
cd "$ROOT_DIR/frontend"
npm run build

cd "$ROOT_DIR"
echo "全流程验收通过"
