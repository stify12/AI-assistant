# UI 风格规范

## 设计风格
- **主题**: 黑白简洁风格，参考 ChatGPT/Apple 设计语言
- **特点**: 高对比度、圆角、无框架原生实现
- **禁止**: 不要使用 emoji

## 配色方案

### 深色主题 (index.html, compare.html 对话页面)
```css
--bg-main: #212121;        /* 主背景 */
--bg-sidebar: #171717;     /* 侧边栏背景 */
--bg-input: #2f2f2f;       /* 输入框背景 */
--bg-hover: #2f2f2f;       /* 悬停背景 */
--bg-active: #424242;      /* 激活状态背景 */
--text-primary: #ececec;   /* 主文字 */
--text-secondary: #b4b4b4; /* 次要文字 */
--text-muted: #8e8e8e;     /* 弱化文字 */
--border-color: #424242;   /* 边框颜色 */
--accent-color: #10a37f;   /* 强调色(绿) */
--error-color: #ef4444;    /* 错误色(红) */
```

### 浅色主题 (管理页面: batch-evaluation, subject-grading, data-analysis 等)
```css
背景: #f5f5f7 (页面) / #fff (卡片)
主文字: #1d1d1f
次要文字: #86868b
边框: #e5e5e5 / #d2d2d7
强调: #1d1d1f (黑色按钮)
```

## 圆角规范
```css
--radius-sm: 6px;      /* 小元素 */
--radius-md: 12px;     /* 卡片、输入框 */
--radius-lg: 16px;     /* 弹窗 */
--radius-xl: 24px;     /* 大输入框 */
--radius-full: 9999px; /* 按钮、标签 */
```

## 组件规范

### 按钮
```css
/* 所有按钮字体颜色统一为黑色 */
.btn { 
    padding: 10px 16px; 
    border-radius: 9999px; 
    font-size: 14px; 
    font-weight: 500; 
    color: #1d1d1f;  /* 黑色字体 */
}

/* 浅色主题 */
.btn-primary { 
    background: #1d1d1f; 
    color: #1d1d1f;  /* 黑色字体 */
    border-radius: 8px; 
}
.btn-secondary { 
    background: #f5f5f7; 
    border: 1px solid #d2d2d7; 
    color: #1d1d1f;  /* 黑色字体 */
}

/* 注意: 所有按钮（包括 .btn-primary, .btn-secondary, .btn-warning, .btn-danger 等）
   字体颜色都应为黑色 #1d1d1f，不使用白色字体 */
```

### 卡片
```css
.section { background: #fff; border-radius: 12px; padding: 20px; }
.stat-card { background: #f5f5f7; border-radius: 8px; padding: 16px; text-align: center; }
```

### 表单
```css
input, select, textarea { padding: 10px 12px; border: 1px solid #d2d2d7; border-radius: 8px; font-size: 14px; }
```

### 标签/徽章
```css
.tag { padding: 4px 8px; border-radius: 4px; font-size: 11px; }
```

### 弹窗
```css
.modal-content { background: #fff; border-radius: 16px; max-width: 500px; }
```

## 字体
```css
font-family: 'Söhne', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
font-family: 'Söhne Mono', 'Monaco', 'Consolas', monospace; /* 代码 */
```

## 动画
```css
transition: all 0.15s ease;  /* 悬停效果 */
transition: all 0.2s ease;   /* 展开/收起 */
transition: all 0.3s ease;   /* 抽屉/弹窗 */
```

## 状态颜色
| 状态 | 背景色 | 文字色 |
|------|--------|--------|
| 成功 | #e3f9e5 | #1e7e34 |
| 警告 | #fff3e0 | #e65100 |
| 错误 | #ffeef0 | #d73a49 |
| 信息 | #e3f2fd | #1565c0 |
| 默认 | #f5f5f7 | #86868b |
