.PHONY: help install dev test test-api test-web lint lint-api lint-web build

help:
	@echo "Targets:"
	@echo "  install   安装全部依赖 (uv + pnpm)"
	@echo "  dev       同时启动 API (:8000) 与 Web (:5173)"
	@echo "  test      运行全部测试"
	@echo "  lint      ruff + eslint"
	@echo "  build     前端生产构建"

install:
	uv sync
	cd apps/web && pnpm install

dev:
	@echo "API:  http://localhost:8000   Web: http://localhost:5173"
	@trap 'kill 0' INT TERM; \
	( cd apps/api && uv run uvicorn app.main:app --reload --port 8000 ) & \
	( cd apps/web && pnpm dev ) & \
	wait

test: test-api test-web

test-api:
	uv run pytest --cov=apps/api/app --cov-report=term-missing

test-web:
	cd apps/web && pnpm test

lint: lint-api lint-web

lint-api:
	uv run ruff check apps/

lint-web:
	cd apps/web && pnpm lint

build:
	cd apps/web && pnpm build
