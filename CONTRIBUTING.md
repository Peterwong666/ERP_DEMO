# Contributing

感谢对本项目的关注！这是一个面试演示项目，改动请遵循以下流程。

## 开发流程

1. Fork / clone 后，从 `main` 切出功能分支（如 `feat/xxx`、`fix/xxx`、`chore/xxx`）。
2. 安装依赖：`make install`（uv + pnpm）。
3. 提交前确保以下检查全部通过：
   - 后端硬门禁：`make check`（8 项指标逐项断言，任一不符即失败）
   - 后端测试与 lint：`uv run pytest` 与 `uv run ruff check apps/`
   - 前端：`cd apps/web && pnpm test && pnpm build`（首次跑测试前需 `pnpm test:browser:install` 安装 Playwright 浏览器）
4. 提交信息使用英文、约定式提交格式（如 `feat: ...` / `fix: ...` / `chore: ...`）。
5. 发起 Pull Request，CI（ruff + pytest + make check + 前端 lint/test/build）全绿后等待评审。

## 约定

- 业务逻辑收敛在 `apps/api/app/services/`，routers 保持轻薄。
- 种子数据必须保持幂等：`make check` 的 8 项指标是验收真值表，改动数据需同步更新断言。
- 前端基于 shadcn/ui + Tailwind，组件风格与现有代码保持一致。
