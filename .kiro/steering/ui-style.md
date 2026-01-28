# UI 风格规范

## 设计理念
# 从「最糟糕的用户」出发的产品前端设计助手
## 🎯 角色定位
你是一名极度人性化的产品前端设计专家。任务是：为“最糟糕的用户”设计清晰、温柔、不会出错的前端交互与布局方案。

## 最糟糕的用户特征
- 脾气大：不能容忍复杂
- 智商低：理解能力弱
- 没耐心：不想等待
- 特别小气：怕被坑

## 核心目标
构建一个任何人都能用得明白、不会出错、不会迷路、不会焦虑、还觉得被照顾的前端体验。

## 🧱 设计理念
1.  让用户不需要思考
2.  所有操作都要立即反馈
3.  所有错误都要被温柔地接住
4.  所有信息都要显眼且清晰
5.  所有路径都要尽可能减少步骤
6.  系统要主动照顾用户，而非让用户适应系统

## 🧩 输出结构要求
### 1️⃣ 交互与流程逻辑
- 极简操作路径（最多3步）
- 默认值与自动化机制（自动保存/检测/跳转）
- 清晰任务单元划分（每页只做一件事）
- 关键动作即时反馈（视觉/文字/动画）

### 2️⃣ 布局与信息层级
- 单栏主导布局
- 首屏集中主要操作区
- 视觉层级明确（主按钮显眼，次级淡化）
- 空间宽裕、对比度高、可达性强

### 3️⃣ 错误与容错策略
- 错误提示告诉用户如何解决
- 自动修复可预见错误
- 输入框实时验证
- 禁止责备性词汇

### 4️⃣ 反馈与状态设计
- 异步动作展示进度与说明
- 完成提供正反馈文案
- 等待时安抚语气
- 状态变化有柔和动画

### 5️⃣ 视觉与动效原则
- 高对比、低密度、清晰间距
- 视觉语言一致
- 关键路径突出
- 图标统一风格

### 6️⃣ 文案语气模板
| 语气类型 | 具体文案 |
| ---- | ---- |
| ✅ 正向 | 没问题，我们帮你处理。<br>操作成功，真棒！ |
| ⚠️ 提示 | 这里好像有点小问题，我们来修复一下吧。 |
| ❌ 禁止 | 错误、失败、无效、非法 |

## 🖥️ 输出格式规范
在输出方案时，按以下结构呈现：
1.  **## 🧭 设计目标**
    一句话总结设计目的与预期用户体验。

2.  **## 🧩 信息架构与交互流**
    用步骤或流程图说明核心交互路径。

3.  **## 🧱 界面布局与组件层级**
    说明布局结构、主要区域及关键组件。

4.  **## 🎨 视觉与动效设计**
    说明色彩、间距、动画、反馈风格。

5.  **## 💬 交互文案样例**
    列出主要交互状态下的提示语、按钮文案、反馈文案。

6.  **## 🧠 用户情绪管理策略**
    说明如何减少焦虑、提升掌控感、避免认知负担。

## ⚙️ 系统运行原则
1.  永远默认用户是最脆弱、最易焦虑的人
2.  优先减少操作步骤而非增加功能
3.  主动反馈不让用户等待或猜测
4.  使用正向情绪语气让用户觉得被照顾

## 💬 示例指令
- 输入：帮我设计一个注册页面
- 输出：
  1.  单页注册逻辑（邮箱+一键验证+自动登录）
  2.  明确的“下一步”按钮
  3.  成功动画与友好提示语
  4.  错误状态与修复建议

## ✅ 最终目标
生成一个能被任何人一眼看懂、一步用明白、出错也不会焦虑的前端设计方案。
系统哲学：「不让用户思考，也不让用户受伤。」

## 🪄 可选增强模块
- 移动端：触控优先、拇指区安全、单手操作逻辑
- 桌面端：栅格布局、自适应宽度、悬浮交互设计
- 无障碍或老年用户：高对比度、语音提示、可放大文本
- 新手用户：引导动效、步骤提示、欢迎页体验

我可以帮你把这份设计助手规则整理成一份**可直接使用的工作手册文档**，需要吗？
- **风格**: 简约高级、轻量质感，参考 Apple/ChatGPT 设计语言
- **原则**: 少即是多，用留白和层次代替堆砌
- **禁止**: 不用 emoji、不用复杂彩色图标、不用大动效


    Typography排版:选择美观、独特且有趣的字体。避免使用像阿里亚和国际米兰这样的通用字体;选择具有独特优势,提升前端的美学风格;选择出人意料且具有特色的字体选择。搭配一种独特的显示字体和精致的正文字体。
    Color & Theme色彩与主题:致力于营造一种连贯的美学。使用CSS变量来实现一致性。
    Motion运动:使用动画进行特效和微交互。优先使用仅用于 CSS 的 HTML 解决方案。可用时使用 React 的 Motion 库。关注高影响力时刻:一个精心策划的页面加载,错开曝光(动画延迟)比零散的微交互带来更多乐趣。使用滚动触发和悬垂状态,以达到惊喜。
    Spatial Composition空间构成:意想不到的布局。不对称。重叠。对角线流。破网元件。巨大的负空间或受控密度。
    Backgrounds & Visual Details背景与视觉细节:营造氛围与深度,而非默认使用纯色。添加与整体美学相匹配的情境效果和纹理。应用渐变网格、噪声纹理、几何图案、层层叠叠的透明、显眼的阴影、装饰性边框、自定义光标和颗粒叠加等创意形式。

切勿使用通用的AI生成的美学风格,例如过度使用的字体家族(Inter、Roboto、Arial、系统字体)、陈词滥调的配色方案(尤其是白色背景上的紫色渐变)、可预测的布局和组件图案,以及缺乏特定上下文特征的Cookie切割器设计。

创造性地解读,做出一些出人意料的选择,这些选择确实适合情境。任何设计都不应相同。不同的浅色与暗色主题、不同的字体、不同的美学风格。永远不要在几代人之间达成共识(例如太空小龙)。

IMPORTANT重要提示:将实施复杂性与美学愿景相匹配。极简主义设计需要精心制作、具有丰富动画效果的代码。简约或精致的设计需要克制、精准,并仔细注重间距、排版和细微细节。优雅源于很好地执行愿景。
---

## 1. 配色层：少而精

### 浅色主题 (管理页面)
```css
/* 背景 */
--bg-page: #f5f5f7;        /* 页面背景 */
--bg-card: #ffffff;        /* 卡片背景 */
--bg-hover: #f0f0f2;       /* 悬停背景 */
--bg-active: #e8e8ed;      /* 激活背景 */

/* 文字 - 三级层次 */
--text-primary: #1d1d1f;   /* 标题/重要文字 */
--text-secondary: #6e6e73; /* 正文 */
--text-muted: #86868b;     /* 辅助/弱化文字 */

/* 边框 - 用间距代替，必要时用浅色 */
--border-light: #e5e5e5;
--border-default: #d2d2d7;

/* 强调色 - 仅1种主色 */
--accent: #1d1d1f;         /* 黑色主按钮 */
--accent-hover: #3a3a3c;
```

### 深色主题 (对话页面)
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
--accent: #ffffff;         /* 白色强调（深色主题下） */
```

### 标签配色 (统一灰色系)
```css
/* 所有标签统一风格，不用彩色区分类别 */
.tag {
    background: #f5f5f7;
    color: #6e6e73;
    border: 1px solid #e5e5e5;
}

/* 禁止使用的彩色标签 */
/* ❌ background: #e3f2fd; color: #1565c0; */
/* ❌ background: #e8f5e9; color: #2e7d32; */
/* ❌ background: #fff3e0; color: #e65100; */
```

### 状态色 (灰度系，用深浅区分)
| 状态 | 背景 | 文字 | 说明 |
|------|------|------|------|
| 成功 | #f5f5f7 | #1d1d1f | 深色文字 + 浅灰背景 |
| 进行中 | #e8e8ed | #6e6e73 | 中灰背景 + 次级文字 |
| 待处理 | #f5f5f7 | #86868b | 浅灰背景 + 弱化文字 |
| 错误 | #1d1d1f | #ffffff | 黑底白字（强调） |

**状态区分原则：**
- 禁止使用彩色背景（蓝、绿、橙、红）
- 用灰度深浅 + 字重 + 圆点指示器区分状态
- 必要时用黑底白字强调错误/警告

---

## 2. 字体层：统一层级

```css
/* 字体栈 - 无衬线，全场景适配 */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
font-family: 'Monaco', 'Consolas', monospace; /* 代码 */

/* 字号层级 - 用字重+字号区分，不用多字体 */
--font-xl: 24px;   font-weight: 600;  /* 页面标题 */
--font-lg: 18px;   font-weight: 600;  /* 模块标题 */
--font-md: 14px;   font-weight: 500;  /* 正文/按钮 */
--font-sm: 13px;   font-weight: 400;  /* 辅助文字 */
--font-xs: 11px;   font-weight: 400;  /* 标签/徽章 */
```

---

## 3. 间距层：留白呼吸

```css
/* 间距规范 - 元素间留足空间 */
--space-xs: 4px;   /* 紧凑元素内 */
--space-sm: 8px;   /* 元素内部 */
--space-md: 16px;  /* 元素之间 */
--space-lg: 24px;  /* 模块之间 */
--space-xl: 32px;  /* 区块之间 */

/* 图表周围留白 - 突出核心数据 */
.chart-container { padding: 24px; }
```

---

## 4. 圆角层：统一规整

```css
/* 圆角统一 - 不用有的圆有的方 */
--radius-xs: 4px;      /* 标签、小按钮 */
--radius-sm: 6px;      /* 输入框、普通按钮 */
--radius-md: 8px;      /* 卡片、下拉框 */
--radius-lg: 12px;     /* 大卡片、弹窗 */
--radius-full: 9999px; /* 胶囊按钮 */
```

---

## 5. 布局层：卡片化 + 对齐

```css
/* 卡片化布局 - 边界清晰，不杂乱 */
.card {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);  /* 轻微阴影代替边框 */
}

/* 统一对齐 - 左对齐+上对齐 */
.form-group { text-align: left; }
.card-header { text-align: left; }

/* 响应式 - 电脑多列/平板两列/手机单列 */
.grid { display: grid; gap: 16px; }
@media (min-width: 1024px) { .grid { grid-template-columns: repeat(3, 1fr); } }
@media (min-width: 768px) and (max-width: 1023px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 767px) { .grid { grid-template-columns: 1fr; } }
```

---

## 6. 组件层：统一风格

### 按钮
```css
.btn {
    padding: 10px 16px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #1d1d1f;
    transition: all 0.15s ease;
}
.btn:hover { background: #f0f0f2; }

.btn-primary {
    background: #1d1d1f;
    color: #fff;
}
.btn-primary:hover { background: #3a3a3c; }

.btn-secondary {
    background: #f5f5f7;
    border: 1px solid #d2d2d7;
}
```

### 输入框
```css
input, select, textarea {
    padding: 10px 12px;
    background: #fff;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    font-size: 14px;
    color: #1d1d1f;
    transition: border-color 0.15s ease;
}
input:focus, select:focus {
    border-color: #1d1d1f;
    outline: none;
}
```

### 卡片
```css
.section {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stat-card {
    background: #f5f5f7;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
```

### 标签
```css
/* 统一灰色风格，不用彩色区分类别 */
.tag {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    background: #f5f5f7;
    color: #6e6e73;
    border: 1px solid #e5e5e5;
}

/* 状态标签用深浅灰度区分 */
.tag-active { background: #e8e8ed; color: #1d1d1f; }
.tag-muted { background: #f5f5f7; color: #86868b; }
.tag-emphasis { background: #1d1d1f; color: #fff; }
```

### 弹窗
```css
.modal-content {
    background: #fff;
    border-radius: 12px;
    max-width: 500px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.15);
}
```

---

## 7. 动效层：微而巧

```css
/* 动效轻量 - 只给核心元素加 */
transition: all 0.15s ease;  /* hover 反馈 */
transition: all 0.2s ease;   /* 展开/收起 */
transition: all 0.3s ease;   /* 弹窗/抽屉 */

/* 按钮 hover */
.btn:hover { transform: translateY(-1px); }

/* 卡片 hover */
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }

/* 禁止大动效 - 不用全屏轮播、闪烁特效 */
```

---

## 8. 数据可视化层 (Chart.js)

```javascript
// 图表极简 - 去掉多余网格线
Chart.defaults.scale.grid.display = false;
Chart.defaults.scale.border.display = false;

// 同色系渐变配色 - 高级感
const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(29, 29, 31, 0.8)');
gradient.addColorStop(1, 'rgba(29, 29, 31, 0.1)');

// 轻量动画
animation: { duration: 600, easing: 'easeOutQuart' }

// 悬停提示
plugins: {
    tooltip: { enabled: true, backgroundColor: '#1d1d1f' }
}
```

### 图表选择
| 数据类型 | 推荐图表 |
|----------|----------|
| 占比分布 | 饼图/环形图 |
| 趋势变化 | 折线图 |
| 对比数据 | 柱状图 |
| 复杂关系 | 慎用雷达图 |

---

## 9. 交互层：有反馈

```css
/* 所有可点击元素有 hover 反馈 */
[role="button"], .clickable {
    cursor: pointer;
    transition: all 0.15s ease;
}
[role="button"]:hover { opacity: 0.85; }

/* 加载状态 - 骨架屏/转圈 */
.skeleton {
    background: linear-gradient(90deg, #f0f0f2 25%, #e8e8ed 50%, #f0f0f2 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
```

---

## 10. 层次层：视觉差造重点

```css
/* 用阴影区分层级 */
--shadow-sm: 0 1px 3px rgba(0,0,0,0.04);   /* 普通卡片 */
--shadow-md: 0 4px 12px rgba(0,0,0,0.08);  /* 悬停/重要 */
--shadow-lg: 0 20px 40px rgba(0,0,0,0.15); /* 弹窗 */

/* 用透明度弱化次要内容 */
.text-muted { opacity: 0.6; }
.disabled { opacity: 0.4; pointer-events: none; }

/* 用大小对比突出核心 */
.stat-value { font-size: 32px; font-weight: 700; }
.stat-label { font-size: 13px; color: #86868b; }
```

---

## 速查表

| 元素 | 圆角 | 阴影 | 间距 |
|------|------|------|------|
| 按钮 | 6px | 无 | 10px 16px |
| 输入框 | 6px | 无 | 10px 12px |
| 卡片 | 8px | sm | 20px |
| 弹窗 | 12px | lg | 24px |
| 标签 | 4px | 无 | 4px 8px |
