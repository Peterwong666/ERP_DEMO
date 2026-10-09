# PRD — 跨境电商供应链 ERP_DEMO 产品需求文档

> 版本：v1.1（已冻结）　日期：2026-10-08
> 配套文档：[design-tokens.md](./design-tokens.md)（视觉规格）、[../todolist.md](../todolist.md)（任务书）
> Figma：`ERP_DEMO_V2`，fileKey `ipfKD6HngH1Gsj3xwuDMqB`
> 状态：**已冻结（2026-10-08 用户评审通过）**　变更须记入 `项目进度.md` 决策记录
> v1.1 变更：阈值/分档/口径等参数改为「系统设置」，用户可在界面自行配置

---

## 1. 产品概述

### 1.1 背景

「皮蛋王科技」是一家模拟的跨境电商卖家，经营电子配件、包袋、家居等小包商品，
销往海外独立站与平台。当前供应链管理存在三个典型痛点：

1. **采购靠 Excel / 微信**：下单、催货无系统记录，到货状态不透明。
2. **库存靠猜**：不清楚可用、在途、待检数量，频繁断货与积压并存。
3. **质量无追溯**：不良品原因无统计，无法向供应商追责与改进。

### 1.2 产品目标

构建覆盖 **新品 → 采购 → 收货 → 质检 → 库存 → AI 供应链** 的一体化 ERP，
实现单据全流程可追溯、库存口径清晰、低库存主动预警，并通过 AI 与 MCP
提供智能补货与系统打通能力。

### 1.3 范围

- 本期为 **单公司、单用户演示系统**（用户=管理员，身兼采购/收货/质检职责）。
- 真实场景中的角色分离（采购员/收货员/质检员/管理员）通过文档说明，不做权限系统。
- 明确不做的事项见 `todolist.md` 1.2 节（多租户、真实平台对接、微服务等）。

### 1.4 术语表

| 术语 | 含义 |
| --- | --- |
| SKU | 最小存货单位，如 `EC-0004-XL` |
| PO | Purchase Order，采购订单 |
| 在途 | 已下单但尚未收货的数量 |
| 待检 | 已收货但尚未完成质检、不可销售的库存 |
| 可用 | 质检合格、可销售的库存 |
| 良率 | 质检合格数 ÷ 送检数 × 100% |
| 可售天数 | 当前可用库存 ÷ 预测日均销量 |
| 安全库存 | 为应对波动设定的库存下限 |
| MCP | Model Context Protocol，Agent 调用外部系统能力的协议 |

---

## 2. 角色与使用场景

| 角色（真实场景） | 核心场景 | 本 Demo 呈现方式 |
| --- | --- | --- |
| 采购员 | 创建 PO、跟踪到货、依据 AI 建议补货 | 管理员统一操作 |
| 收货员 | 按 PO 点收、录入实收数量 | 管理员统一操作 |
| 质检员 | 抽检、录入合格数与不良原因 | 管理员统一操作 |
| 仓库/管理者 | 查看库存与预警、对账 | 管理员统一操作 |
| AI Agent（阶段 10） | 不经 UI 直接查询/创建单据 | 经 MCP 调用 |

---

## 3. 业务实体与字段

> 字段为产品需求定义，阶段 2 落为 ORM 模型与迁移。所有业务表含
> `created_at` / `updated_at`；单据含 `created_by`。

### 3.1 Supplier 供应商

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| supplier_id | int PK | |
| code | str unique | 供应商编码 |
| name | str | 供应商名称 |
| contact_person | str | 联系人 |
| email | str | 邮箱 |
| phone | str | 电话 |
| country | str | 国家/地区 |
| lead_time_days | int | 标准采购提前期（天） |
| status | enum | 合作中 / 已停用 |

### 3.2 Product（SKU）产品

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| product_id | int PK | |
| sku_code | str unique | SKU 编码，如 `EC-0004-XL` |
| name | str | 品名，如"蓝牙耳机 TWS" |
| category | enum | 电子 / 包袋 / 家居 等 |
| status | enum | 开发中 / 在售 / 停售 |
| unit | str | 单位（件/个） |
| standard_cost | decimal | 标准成本 |
| weight_g | int | 重量（克） |
| barcode | str optional | 条码 |
| safety_stock | int | 安全库存 |
| default_supplier_id | FK supplier | 默认供应商 |
| description | text optional | 描述 |

### 3.3 PurchaseOrder 采购单（PO）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| po_id | int PK | |
| po_no | str unique | PO 单号 |
| supplier_id | FK | |
| status | enum | 见 4.1 状态机 |
| total_amount | decimal | 后端由明细计算，不信前端 |
| order_date | date | 下单日期 |
| expected_date | date optional | 预计到货日期 |
| notes | text optional | 备注 |

### 3.4 PurchaseOrderItem 采购单明细

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| item_id | int PK | |
| po_id | FK | |
| product_id | FK | |
| qty_ordered | int | 采购数量 |
| qty_received | int, default 0 | 累计已收数量 |
| unit_price | decimal | 单价 |

### 3.5 ReceivingOrder 收货单

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| recv_id | int PK | |
| recv_no | str unique | 收货单号 |
| po_id | FK | 来源 PO |
| status | enum | 待质检 / 质检中 / 已完成 |
| received_at | datetime | 收货时间 |
| operator | str | 收货人 |
| notes | text optional | 少收/拒收备注 |

### 3.6 ReceivingItem 收货明细

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| recv_item_id | int PK | |
| recv_id | FK | |
| po_item_id | FK | 对应 PO 明细 |
| product_id | FK | |
| qty_received | int | 实收数量（≤ 该明细待收数） |

### 3.7 InspectionOrder 质检单

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| insp_id | int PK | |
| insp_no | str unique | 质检单号 |
| recv_id | FK | 来源收货单 |
| status | enum | 待质检 / 质检中 / 已完成 |
| inspected_at | datetime optional | 完成时间 |
| inspector | str | 质检员 |

### 3.8 InspectionItem 质检明细

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| insp_item_id | int PK | |
| insp_id | FK | |
| product_id | FK | |
| qty_inspected | int | 送检数 |
| qty_passed | int | 合格数 |
| qty_failed | int | 不良数（= 送检 − 合格） |

### 3.9 DefectRecord 不良记录

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| defect_id | int PK | |
| insp_item_id | FK | |
| reason_code | enum | 外观划伤/功能异常/包装破损/尺寸偏差/标签错误/其他 |
| qty | int | 该原因不良数量 |

### 3.10 Inventory 库存（按 SKU 汇总）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| inventory_id | int PK | |
| product_id | FK unique | |
| qty_available | int | 可用库存 |
| qty_pending | int | 待检库存 |
| qty_defective | int | 不良库存 |
| location | str optional | 库位 |

> 在途数量不落字段，由未完成 PO 明细实时计算：
> `qty_in_transit = Σ(qty_ordered − qty_received)`。

### 3.11 InventoryTransaction 库存变动流水

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| txn_id | int PK | |
| product_id | FK | |
| change_qty | int | 变动数量（正负）及影响的库存口径 |
| stock_type | enum | available / pending / defective |
| txn_type | enum | 收货入库 / 质检合格 / 质检不良 / 手工调整 / 调整出库 |
| ref_doc_type | str | 来源单据类型（PO/收货/质检） |
| ref_doc_no | str | 来源单据号 |
| reason | str optional | 调整原因（手工调整必填） |
| operator | str | 操作人 |
| created_at | datetime | 时间 |

**对账规则**：任意 SKU 的库存余额 = 其全部流水累计之和（阶段 8 有对账测试）。

### 3.12 DailySales 销量历史（预测输入）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| sales_id | int PK | |
| product_id | FK | |
| date | date | |
| qty_sold | int | 当日销量 |

> 每 SKU 至少 30 日历史，供补货引擎与看板使用。

### 3.13 ReplenishmentSuggestion 补货建议

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| suggestion_id | int PK | |
| product_id | FK | |
| current_stock | int | 生成时可用库存 |
| qty_in_transit | int | 在途数量 |
| forecast_7d | int | 预测 7 日销量 |
| suggested_qty | int | 建议采购量 |
| days_cover | int | 可售天数 |
| urgency | enum | 正常 / 建议 / 紧急 |
| generated_at | datetime | 生成时间 |

### 3.14 SystemSetting 系统设置（用户可配置）

以键值对存储全局业务参数。所有算法与 KPI **必须从本表读取参数，禁止硬编码**；
服务层提供带默认值的读取与类型转换。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| setting_id | int PK | |
| key | str unique | 参数键（见下表） |
| value | str | 参数值（按 value_type 转换） |
| value_type | enum | int / float / enum |
| category | enum | 库存预警 / AI 补货 / 质检 / 业务口径 |
| label | str | 界面显示名 |
| description | str | 说明 |
| updated_at | datetime | 最后修改时间 |

**预置设置项（含默认值）**

| key | 默认 | 类型 | 分类 | 含义 |
| --- | --- | --- | --- | --- |
| `low_stock_days_threshold` | 14 | int | 库存预警 | 可售天数低于该值触发低库存预警 |
| `urgency_emergency_days` | 10 | int | AI 补货 | 可售天数 ≤ 此值判为「紧急」 |
| `urgency_suggestion_days` | 21 | int | AI 补货 | 可售天数 ≤ 此值判为「建议」 |
| `qc_pass_rate_target` | 95 | float | 质检 | 良率目标(%)，低于则警示 |
| `inbound_caliber` | receiving | enum | 业务口径 | 入库口径：receiving=收货入库 / inspection=质检合格入库 |

> 修改设置后，低库存预警数、补货紧急程度、良率警示等须按新值实时重算
> （看板/引擎不缓存旧参数结果）。

---

## 4. 状态机与业务流转

### 4.1 PO 状态机

```
                 取消
                  ▼
[草稿] ──下单──► [已下单] ──部分收货──► [部分收货] ──全部收齐──► [已收货] ──关闭──► [已关闭]
                   ▲                      │
                   └────── 继续收货 ──────┘
```

| 当前状态 | 允许操作 | 目标状态 |
| --- | --- | --- |
| 草稿 draft | 提交下单 / 编辑 / 删除 | 已下单 |
| 已下单 ordered | 收货（部分或全部）/ 取消 | 部分收货 / 已收货 / 已取消 |
| 部分收货 partial_received | 继续收货 / 取消（限制） | 部分收货 / 已收货 / 已取消 |
| 已收货 received | 关闭 | 已关闭 |
| 已关闭 closed / 已取消 cancelled | 无写操作 | — |

**自动判定**：收货数量 > 0 且 < 采购数 → 部分收货；= 采购数 → 已收货。
所有非法流转后端拒绝并返回明确错误（阶段 5 测试覆盖）。

### 4.2 实物流转（核心链路）

```
[下单]          在途 ↑
  │ 收货（≤待收量）
  ▼
[待检区]        pending ↑、在途 ↓      ← 计入"今日入库量"
  │ 质检录入结果
  ├─ 合格 ─► [可用库存] available ↑、pending ↓
  └─ 不良 ─► [不良品区] defective ↑、pending ↓
```

**库存守恒**：任何一步，系统总库存变化 = 单据数量；
质检时 `合格数 + 不良数 = 送检数`。

### 4.3 "入库"口径定义（重要业务规则，可在系统设置切换）

- 系统设置 `inbound_caliber` 决定入库口径：
  - `receiving`（默认）：**收货即入库**——货物进入待检区即计入入库量；
  - `inspection`：**质检合格才入库**——以合格品转入可用库存为准。
- **可用库存**始终仅统计质检合格后的数量（与口径无关）。
- 默认口径 `receiving` 的依据：跨境电商仓库 inbound 发生在收货环节、质检在库内进行，
  因此可同时出现"今日入库 1,284 件"与"待质检 5 批"。

---

## 5. KPI 与业务规则

### 5.1 看板 KPI 计算口径

| KPI | 计算规则 | 种子目标值 |
| --- | --- | --- |
| 待收货 PO 数 | PO 状态 ∈ {已下单, 部分收货} 的单数 | **4 笔**（+2 较昨日） |
| 待质检数 | 待质检/质检中的收货批次数 | **5 批**（需今日完成） |
| 今日入库 | 今日收货入库总件数 | **1,284 件**（↑18% 较昨日） |
| 可用库存 SKU | qty_available > 0 的 SKU 数 | **50 个**（共 50 SKU） |
| 质检良率 | 本期合格数 ÷ 送检数 | **57.1%**（目标取设置 `qc_pass_rate_target`，默认 ≥95%） |
| 低库存预警 | 触发预警规则的 SKU 数 | **6 个 SKU** |

### 5.2 预警规则（阶段 8）

SKU 满足任一条件即进入低库存预警：
1. `qty_available ≤ safety_stock`；或
2. `可售天数 < low_stock_days_threshold`（默认 14，**可在系统设置中修改**）。

### 5.3 补货引擎规则（阶段 9）

- 输入：近 30 日销量、可用库存、在途数量、安全库存、采购提前期。
- 输出（每 SKU）：预测 7 日销量、建议采购量、可售天数、紧急程度。
- 紧急程度（分档阈值取系统设置 `urgency_emergency_days` /
  `urgency_suggestion_days`，默认 10 / 21，**可由用户修改**）：
  - **紧急**：可售天数 ≤ 紧急阈值（如 8、9 天且无在途覆盖）；
  - **建议**：可售天数 ≤ 建议阈值且预测将低于安全库存；
  - **正常**：其余（库存充足仍给出滚动建议）。
- 目标：看板显示 **8 个 SKU 建议补货**，其中含紧急/建议/正常三态。
- 方法：移动平均/加权回归等**透明算法**；LLM 只负责自然语言表达，不生成数字。

### 5.4 环形图不良分布（本期累计）

| 原因 | 占比 |
| --- | --- |
| 外观划伤 | 37% |
| 功能异常 | 22% |
| 包装破损 | 18% |
| 尺寸偏差 | 12% |
| 标签错误 | 7% |
| 其他 | 5% |

不良总数（环形图中心）：**102**。

---

## 6. 页面功能规格（7 个模块）

### 6.1 数据看板 `/`（设计稿已详细，节点 2:7605）

- 顶部：页面标题、全局搜索框（SKU/PO/供应商）、通知铃铛。
- 6 张 KPI 卡片：图标 + 数值（mono 24 Bold）+ 单位 + 副标题/环比，彩色内描边。
- 近 7 日入库量柱状图：今日柱深色高亮、柱顶数值、图例（今日前/今日）。
- 质检不良原因环形图：中心不良总数 102、右侧图例+百分比。
- AI 智能补货建议：区块标题 + "8 个 SKU 建议补货" + 批量生成 PO；
  表格列：SKU 编码 / 品名 / 当前库存（带进度条）/ 在途数量 /
  预测 7 日销量（含可售天数）/ 建议采购量 / 紧急程度徽标 / 操作（生成 PO）；
  底部算法说明 + 更新时间。

### 6.2 新品管理 `/products`

- 产品列表：分页、搜索、品类筛选；列：SKU 编码/品名/品类/状态/创建时间。
- 新建/编辑产品：表单校验（必填、编码唯一、格式）。
- 产品详情：默认供应商、历史 PO、当前库存；操作"发起采购"跳转新建 PO 并带入 SKU。
- 状态：开发中 / 在售 / 停售。

### 6.3 采购管理 `/purchase-orders`

- PO 列表：状态筛选、供应商/日期/SKU 搜索、状态统计。
- 新建/编辑 PO：选供应商 + 多 SKU 明细（数量、单价），自动汇总金额。
- PO 详情：明细、收货进度（已收/待收）、关联收货/质检时间线。
- 操作：提交下单、取消、关闭（按状态机）；写审计日志。
- 支持从补货建议生成 PO / 批量生成 PO（按供应商拆单）。

### 6.4 收货管理 `/receiving`

- 待收货 PO 列表（目标 4 笔）。
- 创建收货单：选 PO，按明细录入实收数量，支持少收/拒收备注。
- 收货单详情与状态；回写 PO 收货进度；货物进入待检区。

### 6.5 质检管理 `/inspections`

- 待质检批次列表（目标 5 批）。
- 录入质检结果：合格数、不良数及不良原因明细。
- 质检单详情；自动计算批次/累计良率；低于 95% 视觉警示。
- 合格转可用、不良转不良品区。

### 6.6 库存管理 `/inventory`

- 库存总表：SKU、可用/待检/不良、在途、可售天数、库位。
- 库存变动流水：按 SKU 查看，含来源单据与操作人。
- 手工调整：必填原因，留痕；不可直接改余额。
- 低库存预警预警清单（目标 6 SKU）。

### 6.7 AI 供应链 `/ai-supply-chain`

- 补货建议总表（引擎可重新生成）：显示每 SKU 计算因子与依据。
- 一键 / 批量生成 PO。
- 自然语言问答："哪些 SKU 下周可能断货？"等，答案数字可溯源。
- 补货分析摘要（LLM，无 key 时模板化降级）。

### 6.8 MCP（非页面，阶段 10）

对外 tools 与 PRD 实体口径一致：`search_sku`、`get_inventory`、
`list_purchase_orders`、`create_purchase_order`、`list_low_stock_alerts`、
`get_replenishment_suggestions`（≥6 个），详见 `todolist.md` 阶段 10。

### 6.9 系统设置 `/settings`

入口：侧边栏底部用户信息区（管理员头像/姓名）点击进入。

- 按分类分组展示全部设置项：库存预警、AI 补货、质检、业务口径。
- 数值项用数字输入（含范围校验）；枚举项（入库口径）用单选/下拉。
- 保存：调用 `PUT /api/settings`；成功后提示并使相关结果实时重算。
- 提供"恢复默认"。

---

## 7. 验收标准（阶段 0 出口）

- [x] design tokens 五类齐全（见 design-tokens.md）。
- [x] 业务实体 13 个、字段与关系定义完整（第 3 节）。
- [x] PO 状态机与实物流转无歧义（第 4 节）。
- [x] 6 个 KPI 口径与 8 项目标数字明确（第 5 节）。
- [x] 7 个模块页面功能规格齐全（第 6 节，含系统设置页）。
- [x] **用户评审通过并冻结本 PRD（2026-10-08）**。

已冻结，进入阶段 1（工程骨架）。

---

## 8. 已确认事项（均可在系统设置中由用户修改）

1. 低库存"可售天数"阈值默认 **14 天**（`low_stock_days_threshold`）。
2. 紧急程度分档默认 **≤10 紧急 / 11–21 建议**（`urgency_emergency_days` / `urgency_suggestion_days`）。
3. 入库口径默认 **收货入库（含待检）**（`inbound_caliber=receiving`）。
4. 良率目标默认 **95%**（`qc_pass_rate_target`）。
