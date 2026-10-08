# Design Tokens — ERP_DEMO 视觉设计规范

> 版本：v1.0　提取日期：2026-10-08
> 来源：Figma 文件 `ERP_DEMO_V2`（fileKey: `ipfKD6HngH1Gsj3xwuDMqB`），页面 `01.index`
> 提取方式：Figma Plugin API 遍历节点实测属性（本文件色值均为节点实际渲染值，非人工取色）
> 用途：阶段 1 Tailwind 主题配置与全部前端实现的**唯一视觉依据**

---

## 1. 字体（Typography）

### 1.1 字体族（核心设计语言）

| Token | 字体 | 用途 |
| --- | --- | --- |
| `--font-sans` | **Inter** | 所有界面文字、标题、标签、正文 |
| `--font-mono` | **JetBrains Mono** | **所有数字**：KPI 数值、表格数字、百分比、徽标文字 |

> ⚠️ 关键特征：本设计数字与文字使用不同字体。任何数值（含"57.1%""1,284""113"）
> 必须使用 JetBrains Mono，这是该设计辨识度的重要来源。

### 1.2 字号 / 字重 / 行高阶梯

| Token | 字体 · 字重 | 字号 | 行高 | 典型用途 |
| --- | --- | --- | --- | --- |
| `text-kpi` | JetBrains Mono **Bold** | 24px | 24px | KPI 卡片主数值（4 / 1,284 / 57.1%） |
| `text-kpi-unit` | JetBrains Mono Regular | 14px | 20px | KPI 数值单位（笔 / 批 / 件 / 个） |
| `text-table-num` | JetBrains Mono **Bold** | 14px | 20px | 表格数字（库存 113、建议采购量 300） |
| `text-percent` | JetBrains Mono Bold | 12px | 16px | 环形图图例百分比、徽标 |
| `text-mono-sm` | JetBrains Mono Regular/Medium | 12px | 16px | 辅助数字、计数（8 个 SKU） |
| `text-page-title` | Inter **Semi Bold** | 14px | 20px | 页面标题"数据看板"、区块标题 |
| `text-nav-active` | Inter **Medium** | 14px | 20px | 侧边栏导航文字 |
| `text-brand` | Inter Semi Bold | 14px | 17.5px | 侧栏品牌名 |
| `text-body` | Inter Regular | 14px | 20px | 表格品名等正文（蓝牙耳机 TWS） |
| `text-sm` | Inter Regular / Medium / Semi Bold | 12px | 15–16px | 卡片副标题、表头、正文、标签 |
| `text-chart-axis` | Inter Regular | 8.5px | AUTO | 图表坐标轴刻度与标签 |
| `text-chart-label` | Inter Bold | 8.5px | AUTO | 图表数值标签（柱状图顶 1284） |
| `text-donut-center` | Inter Bold | 13.6px | AUTO | 环形图中心数字 102 |
| `text-donut-center-label` | Inter Regular | 7.2px | AUTO | 环形图中心"不良总数" |

**可用字重**：Regular 400 / Medium 500 / Semi Bold 600 / Bold 700
（注意：Figma 中 Inter 样式名为 `Semi Bold`，不是 `SemiBold`）

---

## 2. 颜色（Color）

### 2.1 中性色与表面（Surface）

| Token | 色值 | 用途 |
| --- | --- | --- |
| `sidebar` | `#0F172A` | 深色侧边栏背景（Slate 900） |
| `bg-page` | `#F1F5F9` | 页面整体背景（Slate 100） |
| `bg-card` | `#FFFFFF` | 卡片 / 内容区白色背景 |
| `bg-subtle` | `#F8FAFC` | 表头、次级容器背景（Slate 50） |
| `bg-input` | `#F1F5F9` | 搜索输入框背景 |
| `border` | 待提取 | 建议 `#E2E8F0`（Slate 200），阶段 1 与描边实测复核 |

### 2.2 文字色

| Token | 色值 | 用途 |
| --- | --- | --- |
| `text-on-dark` | `#FFFFFF` | 深色侧栏上的主文字（品牌名、激活项） |
| `text-primary` | `#314158` | 内容区主文字、KPI 中性数值 |
| `text-body` | `#45556C` | 表格正文 |
| `text-secondary` | `#62748E` | 卡片副标题、说明文字 |
| `text-muted` | `#90A1B9` | 侧栏未激活导航、占位文字 |
| `text-axis` | `#94A3B8` | 图表坐标轴/网格文字（Slate 400） |

### 2.3 品牌色（Brand）

| Token | 色值 | 用途 |
| --- | --- | --- |
| `brand-600` | `#155DFC` | 主按钮、激活导航背景、主操作色 |
| `brand-700` | `#1447E6` | 链接、KPI 蓝色数值、柱状图"今日" |
| `brand-100` | `#EFF6FF` / `#BFDBFE` | 蓝色图标浅底 / 柱状图"今日前"浅蓝 |
| `brand-800` | `#1E40AF` | 柱状图今日数值标签文字 |

### 2.4 语义色（Semantic）

| 语义 | 文字色 | 背景色 | 用途示例 |
| --- | --- | --- | --- |
| 正向 / 正常 | `#008236`（徽标）／`#009966`（环比） | `#DCFCE7`（徽标）／`#ECFDF5`（卡片底） | 正常徽标、+2 较昨日、共 50 SKU |
| 正向数值 | `#007A55` | — | KPI 绿色主数值（1,284） |
| AI / 青绿图标 | — | `#00D492` | 图标容器 |
| 警告 / 建议 | `#BB4D00`（文字）／`#E17100`（数字） | `#FEF3C6`（徽标）／`#FFFBEB`（卡片底） | 建议徽标、57.1%、橙色库存数 |
| 警告图标 | `#FFB900` | — | 待质检/良率图标 |
| 危险 / 紧急 | `#C10007`（文字）／`#E7000B`（数字） | `#FFE2E2`（徽标）／`#FEF2F2`（卡片底） | 紧急徽标、低库存预警 6 |
| 危险图标 | `#FB2C36` / `#DC2626` | — | 预警图标 |

### 2.5 图表专用色

**柱状图（近 7 日入库量）**
- 今日前：`#BFDBFE`（浅蓝）
- 今日：`#1447E6`（柱体），数值标签 `#1E40AF`

**环形图（质检不良原因分布）**——按图例顺序：

| 不良原因 | 占比 | 色值 |
| --- | --- | --- |
| 外观划伤 | 37% | `#DC2626` |
| 功能异常 | 22% | `#D97706` |
| 包装破损 | 18% | `#7C3AED` |
| 尺寸偏差 | 12% | `#0891B2` |
| 标签错误 | 7% | `#16A34A` |
| 其他 | 5% | `#94A3B8` |

### 2.6 KPI 卡片彩色描边（细微特征）

KPI 卡片为白底 + 极淡同色 1px 内描边（Figma spread shadow 实现）：

| 卡片 | 描边色 |
| --- | --- |
| 待收货 PO 数（蓝） | `#DBEAFE` |
| 待质检数（琥珀） | `#FEF3C6` |
| 今日入库（绿） | `#D0FAE5` |
| 可用库存 SKU（灰） | `#F1F5F9` |
| 质检良率（琥珀） | `#FEF3C6` |
| 低库存预警（红） | `#FFE2E2` |

---

## 3. 圆角（Radius）

| Token | 值 | 用途 |
| --- | --- | --- |
| `rounded-sm` | 4px | 小型元素 |
| `rounded-md` | 8px | **卡片、按钮（默认）** |
| `rounded-lg` | 12px | 大型容器 |
| `rounded-full` | 9999px | 徽标、头像、图标容器（药丸形） |

---

## 4. 间距（Spacing）

### 4.1 Auto-layout 元素间距（gap）

| Token | 值 | 典型用途 |
| --- | --- | --- |
| `gap-1.5` | 6px | 紧凑元素组 |
| `gap-2` | 8px | 卡片内部、图标与文字 |
| `gap-3` | 12px | KPI 卡间距、区块内部 |
| `gap-4` | 16px | 主区块间距 |

### 4.2 常用内边距（padding）

| Token | 值（上 右 下 左） | 用途 |
| --- | --- | --- |
| 卡片内边距 | 16 / 16px | KPI 卡片、图表面板 |
| 表格单元格 | 14 / 16px | 表格行（出现 64 次，基准值） |
| 按钮内边距 | 10 / 12px 或 16/12 | 按钮 |
| 大容器 | 20 / 20px 或 16 / 20px | 面板、补货表区块 |
| 侧栏导航项 | 10 / 12px（含左偏移） | 导航按钮 |
| 徽标 | 2 / 8px | 紧急程度徽标 |

### 4.3 布局尺寸

| 对象 | 值 |
| --- | --- |
| 侧边栏宽度 | **240px**（固定） |
| 设计稿基准帧 | 1033 × 822（按实际屏幕自适应拉伸） |
| KPI 卡片 | 6 张一行，等宽，间距 12px |

---

## 5. 阴影 / 描边（Elevation）

| Token | 规格 | 用途 |
| --- | --- | --- |
| `shadow-xs` | `0 1px 2px rgba(0,0,0,0.10), spread -1` | 按钮、小型元素 |
| `shadow-sm` | `0 1px 3px rgba(0,0,0,0.10), spread 0` | 卡片默认阴影 |

> 卡片整体为「淡阴影 + 彩色内描边」组合，阴影非常克制，避免厚重感。

---

## 6. Tailwind v4 落地映射（阶段 1 执行）

阶段 1 须在前端 `@theme` 中落地以下关键变量（示例，非全量列举）：

```css
@import "tailwindcss";

@theme {
  --font-sans: "Inter", ui-sans-serif, system-blue, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  --color-sidebar: #0F172A;
  --color-page: #F1F5F9;
  --color-card: #FFFFFF;
  --color-subtle: #F8FAFC;

  --color-brand-600: #155DFC;
  --color-brand-700: #1447E6;

  --color-ok: #009966;
  --color-warn: #BB4D00;
  --color-danger: #C10007;
  /* 图表色、徽标底色等按 2.4–2.6 节补齐 */
}
```

> 落地后须在 `make dev` 中对照本文件与 Figma 截图复核，差异记入阶段 1 验收。

---

## 7. 待复核项（阶段 1 闭环）

- [ ] 通用边框 `border` 色值需在前端实现时从节点 stroke 属性二次确认。
- [ ] 搜索框、铃铛、悬浮态（hover/active）的具体色值需提取交互态节点确认。
- [ ] Inter 各字重需在前端字体加载时验证实际字形与 Figma 一致。
