# Design Document: 数据集命名与选择功能

## Overview

本设计文档描述数据集管理和批量评估模块的优化方案。核心目标是支持数据集自定义命名，并在批量评估时允许用户选择特定数据集。

主要变更包括：
1. 数据库 datasets 表新增 name 字段
2. 数据集管理页面增加命名和描述功能
3. 批量评估页面增加数据集选择功能
4. 后端API支持多数据集查询和选择

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  dataset-manage.html    │    batch-evaluation.html              │
│  ├─ 数据集命名输入       │    ├─ 数据集选择弹窗                  │
│  ├─ 描述字段输入         │    ├─ 多数据集列表展示                │
│  └─ 重复检测提示         │    └─ 批量选择功能                    │
├─────────────────────────────────────────────────────────────────┤
│  dataset-manage.js      │    batch-evaluation.js                │
│  ├─ saveDataset()       │    ├─ showDatasetSelector()           │
│  ├─ checkDuplicate()    │    ├─ selectDatasetForHomework()      │
│  └─ generateDefaultName()│    └─ batchSelectDataset()            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  routes/dataset_manage.py    │    routes/batch_evaluation.py    │
│  ├─ POST /api/batch/datasets │    ├─ GET /api/batch/matching-   │
│  ├─ PUT /api/batch/datasets/ │        datasets                  │
│  └─ GET /api/batch/datasets/ │    └─ POST /api/batch/tasks/     │
│      check-duplicate         │        select-dataset            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  services/storage_service.py │    services/database_service.py  │
│  ├─ save_dataset()           │    ├─ create_dataset()           │
│  ├─ load_dataset()           │    ├─ update_dataset()           │
│  └─ get_matching_datasets()  │    └─ get_datasets_by_book_page()│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Database Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  MySQL: aiuser.datasets                                          │
│  ├─ id (PK)                                                      │
│  ├─ dataset_id (UNIQUE)                                          │
│  ├─ name (VARCHAR 200) ← 新增                                    │
│  ├─ book_id                                                      │
│  ├─ book_name                                                    │
│  ├─ subject_id                                                   │
│  ├─ pages (JSON)                                                 │
│  ├─ question_count                                               │
│  ├─ description (VARCHAR 500) ← 已有，复用                       │
│  ├─ created_at                                                   │
│  └─ updated_at                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Database Schema Changes

```sql
-- 为 datasets 表添加 name 字段
ALTER TABLE datasets 
ADD COLUMN name VARCHAR(200) DEFAULT NULL COMMENT '数据集名称' 
AFTER dataset_id;

-- 添加索引支持按名称搜索
CREATE INDEX idx_datasets_name ON datasets(name);
```

### 2. Backend API Interfaces

#### 2.1 数据集管理 API

```python
# POST /api/batch/datasets
# 创建数据集（新增 name 参数）
Request:
{
    "book_id": "string",
    "name": "string",           # 新增：数据集名称（可选）
    "pages": [1, 2, 3],
    "base_effects": {...},
    "description": "string"     # 可选：描述信息
}

Response:
{
    "success": true,
    "dataset_id": "abc12345"
}
```

```python
# PUT /api/batch/datasets/<dataset_id>
# 更新数据集（支持修改名称）
Request:
{
    "name": "string",           # 可选：修改名称
    "description": "string",    # 可选：修改描述
    "base_effects": {...}       # 可选：修改基准效果
}
```

```python
# GET /api/batch/datasets/check-duplicate
# 检查重复数据集
Request Params:
    book_id: string
    pages: string (comma-separated, e.g., "1,2,3")

Response:
{
    "success": true,
    "has_duplicate": true,
    "duplicates": [
        {
            "dataset_id": "abc12345",
            "name": "学生A基准",
            "pages": [1, 2, 3],
            "question_count": 50,
            "created_at": "2024-01-01T10:00:00"
        }
    ]
}
```

#### 2.2 批量评估 API

```python
# GET /api/batch/matching-datasets
# 查询匹配的数据集列表
Request Params:
    book_id: string
    page_num: int

Response:
{
    "success": true,
    "data": [
        {
            "dataset_id": "abc12345",
            "name": "学生A基准",
            "book_name": "七年级英语上册",
            "pages": [30, 31],
            "question_count": 50,
            "created_at": "2024-01-01T10:00:00"
        },
        {
            "dataset_id": "def67890",
            "name": "学生B基准",
            "book_name": "七年级英语上册",
            "pages": [30, 31],
            "question_count": 48,
            "created_at": "2024-01-02T10:00:00"
        }
    ]
}
```

```python
# POST /api/batch/tasks/<task_id>/select-dataset
# 为作业选择数据集
Request:
{
    "homework_ids": ["hw1", "hw2"],  # 支持批量
    "dataset_id": "abc12345"
}

Response:
{
    "success": true,
    "updated_count": 2
}
```

### 3. Frontend Components

#### 3.1 数据集管理页面 (dataset-manage.html)

新增元素：
- 数据集名称输入框（步骤3保存前）
- 描述文本框（可选）
- 重复检测提示弹窗

```html
<!-- 数据集命名区域 -->
<div class="dataset-naming-section" id="datasetNamingSection">
    <div class="form-group">
        <label>数据集名称 <span class="required">*</span></label>
        <input type="text" id="datasetNameInput" 
               placeholder="输入数据集名称，如：学生A基准效果">
    </div>
    <div class="form-group">
        <label>描述（可选）</label>
        <textarea id="datasetDescInput" 
                  placeholder="添加备注说明..."></textarea>
    </div>
</div>

<!-- 重复检测弹窗 -->
<div class="duplicate-modal" id="duplicateModal">
    <div class="duplicate-modal-content">
        <h3>发现相同页码的数据集</h3>
        <div class="duplicate-list" id="duplicateList"></div>
        <div class="duplicate-actions">
            <button onclick="editExistingDataset()">编辑现有数据集</button>
            <button onclick="continueCreateNew()">继续创建新数据集</button>
        </div>
    </div>
</div>
```

#### 3.2 批量评估页面 (batch-evaluation.html)

新增元素：
- 数据集选择弹窗
- 作业列表中显示数据集名称
- 批量选择按钮

```html
<!-- 数据集选择弹窗 -->
<div class="dataset-selector-modal" id="datasetSelectorModal">
    <div class="dataset-selector-content">
        <h3>选择数据集</h3>
        <div class="dataset-selector-info" id="selectorInfo">
            <!-- 显示当前作业信息 -->
        </div>
        <div class="dataset-list" id="matchingDatasetList">
            <!-- 匹配的数据集列表 -->
        </div>
        <div class="dataset-selector-actions">
            <button onclick="hideDatasetSelector()">取消</button>
            <button onclick="confirmDatasetSelection()">确认选择</button>
        </div>
    </div>
</div>
```

### 4. Service Layer Changes

#### 4.1 StorageService 扩展

```python
# services/storage_service.py

@staticmethod
def save_dataset(dataset_id, data):
    """保存数据集（支持 name 字段）"""
    # 确保 name 字段被保存
    name = data.get('name', '')
    if not name:
        # 生成默认名称
        name = StorageService.generate_default_dataset_name(data)
    data['name'] = name
    # ... 现有保存逻辑

@staticmethod
def generate_default_dataset_name(data):
    """生成默认数据集名称"""
    book_name = data.get('book_name', '未知书本')
    pages = data.get('pages', [])
    if pages:
        page_range = f"P{min(pages)}-{max(pages)}" if len(pages) > 1 else f"P{pages[0]}"
    else:
        page_range = ""
    timestamp = datetime.now().strftime('%m%d%H%M')
    return f"{book_name}_{page_range}_{timestamp}"

@staticmethod
def get_matching_datasets(book_id, page_num):
    """获取匹配的数据集列表"""
    # 查询所有包含指定 book_id 和 page_num 的数据集
    # 按创建时间倒序排列
    pass
```

#### 4.2 AppDatabaseService 扩展

```python
# services/database_service.py

@staticmethod
def create_dataset(dataset_id, book_id, pages, book_name=None, 
                   subject_id=None, question_count=0, name=None, description=None):
    """创建数据集（新增 name 参数）"""
    sql = """INSERT INTO datasets 
             (dataset_id, name, book_id, book_name, subject_id, pages, 
              question_count, description, created_at) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    # ...

@staticmethod
def get_datasets_by_book_page(book_id, page_num):
    """根据 book_id 和 page_num 查询所有匹配的数据集"""
    sql = """
        SELECT dataset_id, name, book_id, book_name, subject_id, 
               pages, question_count, description, created_at
        FROM datasets 
        WHERE book_id = %s 
          AND JSON_CONTAINS(pages, %s)
        ORDER BY created_at DESC
    """
    return AppDatabaseService.execute_query(sql, (book_id, json.dumps(page_num)))

@staticmethod
def update_dataset_name(dataset_id, name, description=None):
    """更新数据集名称和描述"""
    if description is not None:
        sql = "UPDATE datasets SET name = %s, description = %s WHERE dataset_id = %s"
        return AppDatabaseService.execute_update(sql, (name, description, dataset_id))
    else:
        sql = "UPDATE datasets SET name = %s WHERE dataset_id = %s"
        return AppDatabaseService.execute_update(sql, (name, dataset_id))
```

## Data Models

### Dataset Model (Extended)

```python
class Dataset:
    """数据集数据模型"""
    dataset_id: str          # 唯一标识符 (8位UUID)
    name: str                # 数据集名称 (新增)
    book_id: str             # 关联书本ID
    book_name: str           # 书本名称
    subject_id: int          # 学科ID
    pages: List[int]         # 包含的页码列表
    question_count: int      # 题目总数
    description: str         # 描述信息
    base_effects: Dict       # 基准效果数据 {page_num: [questions]}
    created_at: datetime     # 创建时间
    updated_at: datetime     # 更新时间
```

### Homework Item Model (Extended)

```python
class HomeworkItem:
    """作业项数据模型（批量评估任务中）"""
    homework_id: str         # 作业ID
    book_id: str             # 书本ID
    page_num: int            # 页码
    matched_dataset: str     # 匹配的数据集ID
    matched_dataset_name: str # 匹配的数据集名称 (新增)
    status: str              # 状态
    accuracy: float          # 准确率
    # ... 其他字段
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Default Name Generation Format

*For any* dataset with book_name and pages, when no custom name is provided, the generated default name SHALL match the format "{book_name}_P{min_page}-{max_page}_{timestamp}" where timestamp is in MMDDHHmm format.

**Validates: Requirements 1.2, 6.1**

### Property 2: Whitespace Name Rejection

*For any* string composed entirely of whitespace characters (spaces, tabs, newlines) or empty string, attempting to save a dataset with such name SHALL be rejected with an error response.

**Validates: Requirements 1.5**

### Property 3: Dataset Persistence Round-Trip

*For any* valid dataset with name and description, saving then loading the dataset SHALL return an equivalent object with the same name, description, book_id, pages, and base_effects.

**Validates: Requirements 2.3, 5.4**

### Property 4: Name Search Completeness

*For any* search query string and set of datasets, the search results SHALL include all and only datasets whose name contains the query string (case-insensitive).

**Validates: Requirements 2.4, 3.3**

### Property 5: Dataset List Required Fields

*For any* dataset list API response, each dataset item SHALL contain all required fields: dataset_id, name, book_name, pages, question_count, created_at.

**Validates: Requirements 3.1, 4.2**

### Property 6: Multiple Datasets Distinguishability

*For any* book_id with multiple datasets, each dataset in the list SHALL have a non-empty name that can be used to distinguish it from other datasets of the same book.

**Validates: Requirements 3.2**

### Property 7: Dataset List Sorting

*For any* dataset list query, the returned datasets SHALL be sorted by created_at in descending order (newest first).

**Validates: Requirements 3.4, 5.2**

### Property 8: Dataset Selection State Reset

*For any* homework item with existing evaluation results, when the matched_dataset is changed to a different dataset_id, the evaluation results SHALL be cleared and status SHALL be reset to pending.

**Validates: Requirements 4.5**

### Property 9: Batch Dataset Selection

*For any* list of homework_ids and a target dataset_id, the batch selection API SHALL update all specified homework items to use the target dataset.

**Validates: Requirements 4.6**

### Property 10: Matching Datasets Completeness

*For any* book_id and page_num combination, the matching datasets query SHALL return all datasets where book_id matches AND the pages array contains the specified page_num.

**Validates: Requirements 5.1, 7.1**

### Property 11: Auto-Match Newest Selection

*For any* auto-matching scenario with multiple matching datasets, the system SHALL select the dataset with the most recent created_at timestamp.

**Validates: Requirements 5.3**

### Property 12: Duplicate Detection Accuracy

*For any* book_id and pages combination, the duplicate check SHALL return has_duplicate=true if and only if there exists at least one dataset with matching book_id that contains any of the specified pages.

**Validates: Requirements 7.1, 7.2**

### Property 13: Backward Compatibility - Nameless Dataset Reading

*For any* dataset stored without a name field (legacy data), reading the dataset SHALL return a valid dataset object with an auto-generated default name.

**Validates: Requirements 2.2, 6.1**

## Error Handling

### Input Validation Errors

| Error Code | Condition | Response |
|------------|-----------|----------|
| INVALID_NAME | Name is empty or whitespace-only | 400: "数据集名称不能为空" |
| NAME_TOO_LONG | Name exceeds 200 characters | 400: "数据集名称不能超过200个字符" |
| MISSING_BOOK_ID | book_id not provided | 400: "缺少书本ID" |
| MISSING_PAGES | pages array is empty | 400: "请选择至少一个页码" |

### Database Errors

| Error Code | Condition | Response |
|------------|-----------|----------|
| DATASET_NOT_FOUND | Dataset ID does not exist | 404: "数据集不存在" |
| DB_CONNECTION_ERROR | Database connection failed | 500: "数据库连接失败" |

### Business Logic Errors

| Error Code | Condition | Response |
|------------|-----------|----------|
| NO_MATCHING_DATASET | No dataset matches book_id + page_num | 200: { "data": [], "message": "未找到匹配的数据集" } |
| HOMEWORK_NOT_IN_TASK | Homework ID not found in task | 400: "作业不属于当前任务" |

## Testing Strategy

### Unit Tests

Unit tests focus on specific examples and edge cases:

1. **Name Generation Tests**
   - Test default name generation with various book names and page combinations
   - Test edge cases: single page, many pages, special characters in book name

2. **Input Validation Tests**
   - Test empty name rejection
   - Test whitespace-only name rejection
   - Test name length limit (200 chars)

3. **Backward Compatibility Tests**
   - Test reading legacy dataset without name field
   - Test updating legacy dataset with new name

### Property-Based Tests

Property-based tests validate universal properties across all inputs using the `hypothesis` library.

**Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: dataset-naming-selection, Property {number}: {property_text}**

```python
# tests/test_dataset_naming_properties.py

from hypothesis import given, strategies as st
import pytest

# Property 1: Default Name Generation Format
@given(
    book_name=st.text(min_size=1, max_size=50),
    pages=st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=20)
)
def test_default_name_format(book_name, pages):
    """Feature: dataset-naming-selection, Property 1: Default Name Generation Format"""
    # Generate default name and verify format
    pass

# Property 2: Whitespace Name Rejection
@given(
    whitespace=st.text(alphabet=' \t\n\r', min_size=0, max_size=20)
)
def test_whitespace_name_rejection(whitespace):
    """Feature: dataset-naming-selection, Property 2: Whitespace Name Rejection"""
    # Attempt to save with whitespace name, verify rejection
    pass

# Property 3: Dataset Persistence Round-Trip
@given(
    name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    description=st.text(max_size=200),
    pages=st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=10)
)
def test_dataset_round_trip(name, description, pages):
    """Feature: dataset-naming-selection, Property 3: Dataset Persistence Round-Trip"""
    # Save dataset, load it back, verify equality
    pass

# Property 7: Dataset List Sorting
@given(
    datasets=st.lists(
        st.fixed_dictionaries({
            'name': st.text(min_size=1, max_size=50),
            'created_at': st.datetimes()
        }),
        min_size=2, max_size=10
    )
)
def test_dataset_list_sorting(datasets):
    """Feature: dataset-naming-selection, Property 7: Dataset List Sorting"""
    # Verify list is sorted by created_at DESC
    pass

# Property 10: Matching Datasets Completeness
@given(
    book_id=st.text(min_size=1, max_size=20),
    page_num=st.integers(min_value=1, max_value=200),
    dataset_pages=st.lists(
        st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=10),
        min_size=1, max_size=5
    )
)
def test_matching_datasets_completeness(book_id, page_num, dataset_pages):
    """Feature: dataset-naming-selection, Property 10: Matching Datasets Completeness"""
    # Create datasets, query by page_num, verify all matches returned
    pass
```

### Integration Tests

Integration tests verify end-to-end workflows:

1. **Create Dataset with Custom Name Flow**
   - Create dataset with name → Verify in list → Edit name → Verify update

2. **Batch Evaluation Dataset Selection Flow**
   - Create multiple datasets for same book/page
   - Create evaluation task
   - Verify multiple matches returned
   - Select specific dataset
   - Run evaluation
   - Verify correct dataset used

3. **Migration Compatibility Test**
   - Insert legacy dataset without name
   - Read via API
   - Verify default name generated
   - Update with custom name
   - Verify persistence
