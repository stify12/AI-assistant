# Design Document: Dataset Page Management

## Overview

本设计增强现有的数据集编辑弹窗，添加单页重新识别和单页删除功能。主要修改集中在前端编辑弹窗的UI和交互逻辑，以及后端数据集更新API的增强。

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Edit Modal (Enhanced)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Page Tabs (页码标签)                     │   │
│  │  [第1页] [第2页] [第3页] ...                         │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Page Actions (页面操作区)                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │ 图片预览  │  │重新识别   │  │   删除此页        │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Data Table (数据表格)                       │   │
│  │  题号 | 标准答案 | 学生答案 | 是否正确 | 操作         │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Re-recognize Panel (重新识别面板)           │   │
│  │  (条件显示，点击"重新识别"按钮后展开)                  │   │
│  │  ┌─────────────────────────────────────────────┐     │   │
│  │  │  可用作业图片列表                             │     │   │
│  │  │  [图片1] [图片2] [图片3] ...                 │     │   │
│  │  └─────────────────────────────────────────────┘     │   │
│  │  [取消] [开始识别]                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Frontend Components

#### 1. Enhanced Edit Modal

修改现有的 `editDataset()` 函数和相关渲染逻辑：

```javascript
// 编辑数据集状态扩展
let editingDataset = null;      // 当前编辑的数据集
let editingData = {};           // 按页码存储的编辑数据
let currentEditPage = null;     // 当前选中的页码
let pageImageUrls = {};         // 每个页码对应的图片URL
let reRecognizeMode = false;    // 是否处于重新识别模式
let availableImages = [];       // 可用的作业图片列表
let selectedImageForRecognize = null;  // 选中用于识别的图片
```

#### 2. Page Actions Component

新增页面操作区组件：

```javascript
function renderPageActions() {
    // 返回包含图片预览、重新识别按钮、删除此页按钮的HTML
}
```

#### 3. Re-recognize Panel Component

新增重新识别面板组件：

```javascript
function renderReRecognizePanel() {
    // 返回图片选择面板的HTML
}

async function loadAvailableImagesForPage(page) {
    // 加载指定页码的可用作业图片
}

async function startPageRecognize(page, imageInfo) {
    // 执行单页识别
}
```

#### 4. Delete Page Functions

新增删除页面功能：

```javascript
function confirmDeletePage(page) {
    // 显示删除确认对话框
}

function executeDeletePage(page) {
    // 执行删除页面操作
}
```

### Backend API

#### 1. 获取页码图片信息 (新增)

```
GET /api/dataset/page-image-info
Query: book_id, page_num
Response: { success: true, data: { pic_url, homework_id } }
```

#### 2. 更新数据集 (增强现有)

现有的 `PUT /api/batch/datasets/<dataset_id>` 已支持更新 base_effects，需要增强支持：
- 删除页码时自动更新 pages 列表
- 支持完全删除某个页码的数据

## Data Models

### Dataset Structure (现有)

```json
{
    "dataset_id": "uuid",
    "book_id": "book_id",
    "book_name": "书名",
    "pages": [1, 2, 3],
    "base_effects": {
        "1": [{ "index": "1", "userAnswer": "A", "correct": "yes", ... }],
        "2": [{ "index": "1", "userAnswer": "B", "correct": "no", ... }]
    },
    "question_count": 10,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
}
```

### Page Image Info (新增)

```json
{
    "page": 1,
    "pic_url": "http://...",
    "homework_id": "12345"
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Recognition Result Update Consistency

*For any* page in a dataset and any recognition result, if recognition succeeds, the page data should equal the new result; if recognition fails, the page data should remain unchanged from its original state.

**Validates: Requirements 2.6, 2.7**

### Property 2: Delete Page Data Consistency

*For any* dataset with multiple pages, after deleting one page, that page should not exist in the data and the total page count should decrease by exactly 1.

**Validates: Requirements 3.3**

### Property 3: Save Data Consistency

*For any* edited dataset, after saving, the data read from storage should match the edited data, and the question_count should equal the sum of all page question counts, and the pages list should contain exactly the pages that have data.

**Validates: Requirements 5.1, 5.4**

## Error Handling

### Recognition Errors

1. **Network Error**: 显示"网络连接失败，请检查网络后重试"
2. **Timeout Error**: 显示"请求超时，AI模型响应时间过长，请重试"
3. **API Error**: 显示具体错误信息，如"识别失败: [错误详情]"
4. **Parse Error**: 显示"无法解析识别结果，请重试或手动编辑"

### Delete Errors

1. **Last Page Delete**: 显示二次确认"删除最后一页将删除整个数据集，是否继续？"
2. **Save Error**: 显示"保存失败: [错误详情]"，保留编辑状态

### Save Errors

1. **Network Error**: 显示"保存失败，请检查网络后重试"
2. **Server Error**: 显示"服务器错误，请稍后重试"

## Testing Strategy

### Unit Tests

1. **renderPageActions()**: 验证操作区HTML正确生成
2. **executeDeletePage()**: 验证删除逻辑正确更新数据
3. **数据统计计算**: 验证 question_count 和 pages 列表计算正确

### Property-Based Tests

使用 Hypothesis (Python) 进行属性测试：

1. **Property 1 Test**: 生成随机数据集和识别结果，验证更新一致性
2. **Property 2 Test**: 生成随机多页数据集，验证删除后数据一致性
3. **Property 3 Test**: 生成随机编辑数据，验证保存后数据一致性

### Integration Tests

1. **完整流程测试**: 打开编辑弹窗 → 重新识别 → 保存 → 验证数据
2. **删除流程测试**: 打开编辑弹窗 → 删除页面 → 保存 → 验证数据
3. **边界条件测试**: 删除最后一页 → 验证数据集被删除
