## 变更说明

<!-- 简述本 PR 做了什么、为什么 -->

## 变更类型

- [ ] feat 新功能
- [ ] fix 缺陷修复
- [ ] docs 文档
- [ ] chore 工程 / 杂项
- [ ] refactor 重构

## 提交前检查

- [ ] 本地 `make check` 全绿（8 项指标硬门禁）
- [ ] 本地 `uv run pytest` 与 `uv run ruff check apps/` 通过
- [ ] 本地 `cd apps/web && pnpm test && pnpm build` 通过
- [ ] 如涉及种子数据 / 指标口径变更，已同步更新 `make check` 断言与 README 真值表
