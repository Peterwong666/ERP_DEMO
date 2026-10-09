FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
# 首次启动：建表 + 空库自动播种（ensure_seed 非破坏、幂等），随后启动 API。
# 直接用镜像内 .venv，避免运行时 uv run 重新同步；exec 让 uvicorn 成为 PID 1。
CMD ["sh", "-c", "PYTHONPATH=apps/api /app/.venv/bin/python -m app.seeds.ensure_seed && exec /app/.venv/bin/uvicorn --app-dir apps/api app.main:app --host 0.0.0.0 --port 8000"]
