---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces for AI批改效果分析平台. Use this skill when building web components, pages, dashboards, or styling any web UI. Generates polished Jinja2 + vanilla CSS/JS code with high design quality, avoiding generic AI aesthetics while maintaining project consistency.
---

# Frontend Design Skill — AI批改效果分析平台

本 skill 指导创建有设计感、生产级的前端界面，避免"AI味"的通用美学。所有输出必须是可直接运行的代码（Jinja2 + 原生 CSS/JS），并在美学细节上精心打磨。

## 技术约束

- 前端栈：Jinja2 模板 + 原生 CSS/JS（模块化）
- 图表库：Chart.js
- 无 React/Vue/Tailwind，不引入额外框架
- 文件结构：`templates/*.html` + `static/css/*.css` + `static/js/*.js`

---

## 设计思维（编码前必须思考）

每次构建界面前，先明确：
- **目的**：这个界面解决什么问题？谁在用？（教育科技团队、测试工程师）
- **基调**：简约高级、轻量质感，Apple/ChatGPT 设计语言。在此基础上根据页面场景微调（数据看板偏克制精准，对话页面偏沉浸深色）
- **差异点**：什么让这个界面令人印象深刻？不是花哨，而是精准的留白、清晰的层次、恰到好处的动效
- **用户假设**：永远假设用户是最脆弱、最没耐心的人。不让用户思考，不让用户受伤

**核心原则**：意图明确胜过强度堆砌。极简需要克制与精准，每一个像素都有理由。

---

## 交互设计原则

### 操作路径
- 极简路径，最多 3 步完成核心操作
- 默认值 + 自动化（自动保存、自动检测、自动跳转）
- 每页只做一件事，任务单元清晰

### 反馈机制
- 所有操作立即反馈（视觉/文字/动画）
- 异步动作展示进度与说明文案
- 完成时给正向反馈："操作成功，真棒！"
- 等待时安抚语气，状态变化有柔和动画

### 错误处理
- 错误提示告诉用户「如何解决」，不是「你错了」
- 输入框实时验证
- 自动修复可预见错误
- 禁止责备性词汇（错误、失败、无效、非法）

### 文案语气
| 场景 | 文案风格 |
|------|----------|
| 正向 | "没问题，我们帮你处理。" "操作成功，真棒！" |
| 提示 | "这里好像有点小问题，我们来修复一下吧。" |
| 禁用词 | 错误、失败、无效、非法 |

---

## 美学规范

### 排版
- 选择美观、有特色的字体，避免 Inter、Roboto、Arial 等通用字体
- 搭配一种有辨识度的显示字体 + 精致的正文字体
- 用字重 + 字号建立清晰的视觉层级，不靠多字体堆砌

```css
/* 字号层级 */
--font-xl: 24px;   font-weight: 600;  /* 页面标题 */
--font-lg: 18px;   font-weight: 600;  /* 模块标题 */
--font-md: 14px;   font-weight: 500;  /* 正文/按钮 */
--font-sm: 13px;   font-weight: 400;  /* 辅助文字 */
--font-xs: 11px;   font-weight: 400;  /* 标签/徽章 */
font-family: 'Monaco', 'Consolas', monospace; /* 代码场景 */
```

### 色彩 — 灰度为主，少而精

致力于营造连贯的美学。使用 CSS 变量保持一致性。主色调搭配锐利的强调色，优于平均分配的多色方案。

#### 浅色主题（管理页面）
```css
--bg-page: #f5f5f7;        /* 页面背景 */
--bg-card: #ffffff;        /* 卡片背景 */
--bg-hover: #f0f0f2;       /* 悬停背景 */
--bg-active: #e8e8ed;      /* 激活背景 */
--text-primary: #1d1d1f;   /* 标题/重要文字 */
--text-secondary: #6e6e73; /* 正文 */
--text-muted: #86868b;     /* 辅助/弱化文字 */
--border-light: #e5e5e5;
--border-default: #d2d2d7;
--accent: #1d1d1f;         /* 黑色主按钮 */
--accent-hover: #3a3a3c;
```

#### 深色主题（对话页面）
```css
--bg-main: #212121;
--bg-sidebar: #171717;
--bg-input: #2f2f2f;
--bg-hover: #2f2f2f;
--bg-active: #424242;
--text-primary: #ececec;
--text-secondary: #b4b4b4;
--text-muted: #8e8e8e;
--border-color: #424242;
--accent: #ffffff;         /* 白色强调 */
```

#### 标签 — 统一灰色系
```css
.tag { background: #f5f5f7; color: #6e6e73; border: 1px solid #e5e5e5; }
/* 禁止彩色标签：❌ #e3f2fd / #e8f5e9 / #fff3e0 */
```

#### 状态色 — 灰度深浅区分
| 状态 | 背景 | 文字 | 说明 |
|------|------|------|------|
| 成功 | #f5f5f7 | #1d1d1f | 深色文字 + 浅灰背景 |
| 进行中 | #e8e8ed | #6e6e73 | 中灰背景 + 次级文字 |
| 待处理 | #f5f5f7 | #86868b | 浅灰背景 + 弱化文字 |
| 错误 | #1d1d1f | #ffffff | 黑底白字（强调） |

禁止使用彩色背景（蓝、绿、橙、红），用灰度深浅 + 字重 + 圆点指示器区分状态。

### 动效 — 微而巧，高影响力时刻

关注高影响力时刻：一个精心编排的页面加载、错开的渐显动画（animation-delay），比零散的微交互更有感染力。用滚动触发和 hover 状态制造惊喜。

```css
transition: all 0.15s ease;  /* hover 反馈 */
transition: all 0.2s ease;   /* 展开/收起 */
transition: all 0.3s ease;   /* 弹窗/抽屉 */
.btn:hover { transform: translateY(-1px); }
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
```

优先使用纯 CSS 动画方案。禁止全屏轮播、闪烁特效等大动效。

### 空间构成

- 卡片化布局，边界清晰
- 留白充足，低密度，呼吸感
- 首屏集中主要操作区
- 视觉层级明确（主按钮显眼，次级淡化）

```css
--space-xs: 4px;   /* 紧凑元素内 */
--space-sm: 8px;   /* 元素内部 */
--space-md: 16px;  /* 元素之间 */
--space-lg: 24px;  /* 模块之间 */
--space-xl: 32px;  /* 区块之间 */
```

### 背景与视觉细节

营造氛围与深度，而非默认纯色。在不破坏简约基调的前提下，可适度使用：
- 轻微渐变网格、噪声纹理
- 层叠透明度
- 精致阴影层级
- 装饰性边框

```css
--shadow-sm: 0 1px 3px rgba(0,0,0,0.04);   /* 普通卡片 */
--shadow-md: 0 4px 12px rgba(0,0,0,0.08);  /* 悬停/重要 */
--shadow-lg: 0 20px 40px rgba(0,0,0,0.15); /* 弹窗 */
```

---

## 组件规范

### 圆角
```css
--radius-xs: 4px;      /* 标签、小按钮 */
--radius-sm: 6px;      /* 输入框、普通按钮 */
--radius-md: 8px;      /* 卡片、下拉框 */
--radius-lg: 12px;     /* 大卡片、弹窗 */
--radius-full: 9999px; /* 胶囊按钮 */
```

### 按钮
```css
.btn { padding: 10px 16px; border-radius: 6px; font-size: 14px; font-weight: 500; transition: all 0.15s ease; }
.btn-primary { background: #1d1d1f; color: #fff; }
.btn-primary:hover { background: #3a3a3c; }
.btn-secondary { background: #f5f5f7; border: 1px solid #d2d2d7; }
```

### 输入框
```css
input, select, textarea {
    padding: 10px 12px; background: #fff; border: 1px solid #d2d2d7;
    border-radius: 6px; font-size: 14px; color: #1d1d1f; transition: border-color 0.15s ease;
}
input:focus, select:focus { border-color: #1d1d1f; outline: none; }
```

### 卡片
```css
.card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.stat-card { background: #f5f5f7; border-radius: 8px; padding: 16px; text-align: center; }
```

### 标签
```css
.tag { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; background: #f5f5f7; color: #6e6e73; border: 1px solid #e5e5e5; }
.tag-active { background: #e8e8ed; color: #1d1d1f; }
.tag-muted { background: #f5f5f7; color: #86868b; }
.tag-emphasis { background: #1d1d1f; color: #fff; }
```

### 弹窗
```css
.modal-content { background: #fff; border-radius: 12px; max-width: 500px; box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
```

### 加载状态
```css
.skeleton {
    background: linear-gradient(90deg, #f0f0f2 25%, #e8e8ed 50%, #f0f0f2 75%);
    background-size: 200% 100%; animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
```

### 速查表
| 元素 | 圆角 | 阴影 | 间距 |
|------|------|------|------|
| 按钮 | 6px | 无 | 10px 16px |
| 输入框 | 6px | 无 | 10px 12px |
| 卡片 | 8px | sm | 20px |
| 弹窗 | 12px | lg | 24px |
| 标签 | 4px | 无 | 4px 8px |

---

## 数据可视化（Chart.js）

```javascript
// 极简：去掉多余网格线
Chart.defaults.scale.grid.display = false;
Chart.defaults.scale.border.display = false;

// 同色系渐变
const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(29, 29, 31, 0.8)');
gradient.addColorStop(1, 'rgba(29, 29, 31, 0.1)');

// 轻量动画
animation: { duration: 600, easing: 'easeOutQuart' }

// 悬停提示
plugins: { tooltip: { enabled: true, backgroundColor: '#1d1d1f' } }
```

| 数据类型 | 推荐图表 |
|----------|----------|
| 占比分布 | 饼图/环形图 |
| 趋势变化 | 折线图 |
| 对比数据 | 柱状图 |
| 复杂关系 | 慎用雷达图 |

---

## 响应式布局

```css
.grid { display: grid; gap: 16px; }
@media (min-width: 1024px) { .grid { grid-template-columns: repeat(3, 1fr); } }
@media (min-width: 768px) and (max-width: 1023px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 767px) { .grid { grid-template-columns: 1fr; } }
```

---

## 禁止清单

- 不用 emoji 作为 UI 元素
- 不用复杂彩色图标
- 不用 Inter、Roboto、Arial 等通用字体族
- 不用紫色渐变白底等陈词滥调配色
- 不用彩色状态标签（蓝/绿/橙/红背景）
- 不用大动效（全屏轮播、闪烁特效）
- 不用 cookie-cutter 模板式设计
- 每次设计都应有独特性，不在多次生成间趋同

---

## 设计哲学

「不让用户思考，也不让用户受伤。」

将实施复杂性与美学愿景匹配：极简设计需要克制、精准，仔细注重间距、排版和细微细节。优雅源于很好地执行愿景。创造性地解读需求，做出适合情境的、出人意料的选择。
