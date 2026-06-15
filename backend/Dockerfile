FROM python:3.13-slim-bookworm

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

RUN set -eux; \
    sed -i \
      -e 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' \
      -e 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
      /etc/apt/sources.list.d/debian.sources; \
    apt-get update -o Acquire::Retries=5; \
    apt-get install -y --no-install-recommends ffmpeg; \
    rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" "."

EXPOSE 8031

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8031"]
