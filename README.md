# PeterWong演示项目 · 跨境电商供应链 ERP

> FDE（Forward Deployed Engineer）岗位面试作品　｜　数据锚点日：2026-10-09
> 一条命令启动、数据可精确核对、采购到入库全程可追溯、参数驱动的补货规则引擎。

一个面向**跨境电商小商品卖家**的供应链 ERP 演示系统：从采购下单（PO）、收货、质检到库存上架形成完整业务闭环，每一笔库存变动都可溯源到原始单据；系统自动识别低库存 SKU 并生成三态紧急度的补货建议。全部业务指标由一份**确定性、幂等**的种子数据集生成，可通过核对脚本精确验证。

---

## 一、快速开始

### 方式 A：一条命令（推荐，无需 Docker）

```bash
make up
```

自动完成：安装依赖（uv + pnpm）→ 空库时播种 → 并行启动 API 与 Web。

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000　（交互式文档 `/docs`）

> 环境要求：Python ≥ 3.12（[uv](https://docs.astral.sh/uv/)）、Node + [pnpm](https://pnpm.io/)。

### 方式 B：Docker Compose

```bash
docker compose up --build
```

### 手动分步

```bash
uv sync                                   # 安装后端依赖
cd apps/web && pnpm install               # 安装前端依赖
(cd apps/api && uv run python -m app.seeds.ensure_seed)  # 空库才播种（非破坏、幂等）
make dev                                  # 同时启动前后端
```

### 核对演示数据（硬门禁）

```bash
make check     # 8 项指标逐项断言，任一不符则退出码非 0
```

---

## 二、8 项关键指标（验收真值表）

`make check` 与看板页面展示的数字完全一致：

| # | 指标 | 目标值 |
| --- | --- | --- |
| 1 | 待收货采购单 | **4 笔** |
| 2 | 待质检批次 | **5 批** |
| 3 | 今日入库 | **1,284 件** |
| 4 | 可用库存 | **50 SKU** |
| 5 | 质检良率 | **57.1%** |
| 6 | 低库存预警 | **6 个 SKU** |
| 7 | 补货建议 | **8 个 SKU**（3 紧急 / 4 建议 / 1 正常） |
| 8 | 不良总数 | **102 件** |

不良原因分布：外观划伤 37% / 功能异常 22% / 包装破损 18% / 尺寸偏差 12% / 标签错误 7% / 其他 5%。

---

## 三、业务闭环（核心演示路径）

```
 采购下单 PO            收货                质检                 库存
 ┌─────────┐      ┌──────────┐      ┌──────────┐       ┌──────────────┐
 │ 草稿     │ ───▶ │ 录入实收  │ ───▶ │ 合格/不良  │ ───▶  │ available    │
 │ → 已下单 │      │ pending  │      │ +原因分布 │       │ defective    │
 └─────────┘      └──────────┘      └──────────┘       └──────────────┘
   place          recv_inbound       qc_pass/qc_fail      每步一步流水
```

1. **采购**：选供应商、多行选 SKU/数量/单价 → 下单（状态机：草稿 → 已下单 → 部分收货 → 已收货 / 已取消）。
2. **收货**：对已下单 PO 创建收货单并录入实收数量，货物进入待检（pending）库存，写 `recv_inbound` 流水。
3. **质检**：一页录入合格/不良数量与不良原因；合格转 `available`（`qc_pass`），不良转 `defective`（`qc_fail` + `defect_records`）。
4. **库存台账**：任意时刻可用「对账接口」验证 **每个 SKU 余额 = 其全部流水之和**；支持按 SKU / 单据号过滤流水、带原因的手工调整（`manual_adjust`）。

> 「今日入库」支持两种口径（系统设置 `inbound_caliber`）：`receiving`（收货即入库，默认）与 `inspection`（质检合格才入库）。

---

## 四、补货规则引擎（"AI" 参数驱动）

不硬编码、无黑盒：所有阈值来自系统设置表，可通过 `GET/PUT /api/settings` 在线调整。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `low_stock_days_threshold` | 14 | 可售天数低于此值 → 低库存预警 |
| `urgency_emergency_days` | 10 | 可售天数 ≤ 此值 → **紧急** |
| `urgency_suggestion_days` | 21 | 可售天数 ≤ 此值 → **建议**；其余 → 正常 |

计算逻辑（确定性）：

- **日均销量** = 近 7 日 DailySales 均值；**7 日预测** = 日均销量 × 7
- **可售天数** = 现有可用库存 ÷ 日均销量
- **目标库存** = round(日均销量 × 目标覆盖天数 30)（30 天为业务常量 `TARGET_COVER_DAYS`）
- **建议量** = max(0, 目标库存 − 现有库存 − 在途量)（在途量由未交 PO 行实时算出，不落字段）
- 三态紧急度（阈值见上表）：可售天数 `≤ emergency` → 紧急；`≤ suggest` → 建议；否则正常

结果：**低库存 6 SKU、补货建议 8 SKU（3 紧急 / 4 建议 / 1 正常）**。

---

## 五、系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Browser (React SPA)                      │
│  Vite · TanStack Router/Query · shadcn/ui (Radix+Tailwind)    │
│  Recharts                    │             :5173               │
└──────────────────────────────┼────────────────────────────────┘
                                │  REST / JSON
┌──────────────────────────────┼────────────────────────────────┐
│                        FastAPI  :8000                          │
│  routers (薄)  ──▶  services (业务/规则)  ──▶  SQLAlchemy ORM   │
│  dashboard · products · purchase_orders · receiving ·          │
│  inspection · inventory · replenishment · settings · suppliers │
└──────────────────────────────┬─────────────────────────────────┘
                                │
                      ┌─────────▼─────────┐
                      │   SQLite (14 表)   │
                      └───────────────────┘
        apps/mcp-server（最小库存查询 tool · 下一里程碑）
```

**设计约定**：routers 保持轻薄，业务行为收敛到 services；请求/响应/更新 schema 分离；库存过账统一走 `services/inventory_ledger.py`（原子条件 UPDATE + 余额重建 + 对账）。

### ER 简图（14 张表）

```
suppliers 1──N purchase_orders 1──N purchase_order_items N──1 products
                          │
                          └──< receiving_orders 1──N receiving_items
                                      │
                                      └──< inspection_orders 1──N inspection_items
                                                        │
products 1──N inventory 1──N inventory_transactions     └──N defect_records
products 1──N daily_sales
products 1──N replenishment_suggestions
system_settings（参数驱动）
```

---

## 六、技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic v2 · SQLite |
| 前端 | React 19 · TypeScript · Vite · TanStack Router/Query · shadcn/ui · Recharts |
| 工程 | uv workspace monorepo · pnpm · ruff · pytest · Docker Compose · CI |
| 测试 | pytest 关键路径（种子幂等、状态流转、库存对账、补货三态）；前端 Vitest |

---

## 七、FDE 能力映射

| FDE 核心能力 | 作品中的证据 |
| --- | --- |
| 数据建模 + 可验证目标 | 14 张表、确定性种子、`make check` 8 项数字精确核对 |
| 深入业务闭环 + 可追溯 | 采购 → 收货 → 质检 → 库存，每笔变动溯源到单据 |
| 用规则/参数快速交付"智能" | 补货建议由系统设置参数驱动、三态紧急度，阈值在线可调 |
| 一键部署 + 清晰沟通 | `make up` / Docker 两条路径、README + 10 分钟演示脚本 |
| 工程质量 | 库存余额恒等对账、幂等播种、关键路径自动化测试 |

---

## 八、目录结构

```
apps/
  api/app/
    main.py            # FastAPI 应用工厂
    config.py          # Pydantic 设置（锚点日、CORS、DB）
    models/            # 14 个 ORM 模型 + 枚举
    schemas/           # 请求/响应模型
    routers/           # HTTP 端点（轻薄）
    services/          # 业务与规则引擎
    seeds/             # run_seed(破坏式) / ensure_seed(非破坏) / check(核对)
  web/src/
    routes/            # TanStack 文件路由
    features/          # dashboard 等 7 个业务模块（+ errors）
  mcp-server/          # MCP 最小 tool（下一里程碑）
docs/
  PRD.md               # 需求文档
  demo-script.md       # 10 分钟演示话术
Makefile  docker-compose.yml  pyproject.toml
```

## 九、下一里程碑（可扩展点）

- **MCP Server**：暴露库存查询 tool，打通 AI Agent 与业务系统（骨架已建）。
- **LLM 分析层**：对补货建议 / 质检异常做自然语言归因（架构已预留，不影响确定性主干）。
- 补货建议「一键生成 PO」、ML 销量预测替换均值模型。
