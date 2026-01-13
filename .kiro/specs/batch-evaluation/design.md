# Design Document: 批量评估系统

## Overview

本系统在现有「学科评估」功能基础上新增「批量评估」模块，支持对AI已批改的多份作业进行批量评估。系统采用Tab切换的单页面架构，包含任务管理和数据集管理两个核心视图，通过弹窗处理新建和编辑操作，减少页面跳转，提供流畅的用户体验。

### 核心功能
1. 图书数据展示（从zp_book_chapter和zp_make_book读取）
2. 数据集管理（为书本页码配置基准效果）
3. 批量评估任务创建与执行
4. 基准效果自动匹配与识别
5. 总体评估报告生成
6. Excel导出

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS/CSS)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    批量评估主页面                                     │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │  [任务管理]  [数据集管理]  ← Tab切换                          │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  │  ┌─────────────────┐  ┌─────────────────────────────────────────┐   │    │
│  │  │   左侧面板       │  │           右侧面板                       │   │    │
│  │  │                 │  │                                         │   │    │
│  │  │ 任务管理视图:    │  │  任务管理视图:                          │   │    │
│  │  │ - 历史任务列表   │  │  - 任务详情                             │   │    │
│  │  │ - 新建任务按钮   │  │  - 作业列表(准确率)                     │   │    │
│  │  │                 │  │  - 总体报告                             │   │    │
│  │  │ 数据集管理视图:  │  │                                         │   │    │
│  │  │ - 图书列表      │  │  数据集管理视图:                         │   │    │
│  │  │ - 按学科分组    │  │  - 书本详情                             │   │    │
│  │  │                 │  │  - 页码列表                             │   │    │
│  │  │                 │  │  - 数据集配置                           │   │    │
│  │  └─────────────────┘  └─────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  弹窗组件: [新建任务弹窗] [添加数据集弹窗] [评估详情抽屉]                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend (Flask)                                    │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐    │
│  │ /api/batch/   │ │ /api/batch/   │ │ /api/batch/   │ │ /api/batch/   │    │
│  │ books         │ │ datasets      │ │ tasks         │ │ evaluate      │    │
│  │ (图书数据)    │ │ (数据集管理)  │ │ (任务管理)    │ │ (批量评估)    │    │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘    │
└──────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
           │                 │                 │                 │
           ▼                 ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐
│  MySQL Database  │ │  Local Storage   │ │  Local Storage   │ │ DeepSeek API │
│ zp_make_book     │ │  datasets/       │ │  batch_tasks/    │ │ (AI分析)     │
│ zp_book_chapter  │ │                  │ │                  │ │              │
│ zp_homework      │ │                  │ │                  │ │              │
└──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────┘
```

## Components and Interfaces

### 0. 题目类型分类工具函数

```python
def classify_question_type(question_data: dict) -> dict:
    """
    根据题目数据判断题目类型
    
    Args:
        question_data: 包含 questionType 和 bvalue 字段的题目数据
        
    Returns:
        {
            "is_objective": bool,  # 是否客观题
            "is_choice": bool,     # 是否选择题
            "choice_type": str     # "single" | "multiple" | None
        }
    """
    question_type = question_data.get('questionType', '')
    bvalue = str(question_data.get('bvalue', ''))
    
    # 客观题判断：questionType === "objective"
    is_objective = question_type == 'objective'
    
    # 选择题判断：bvalue === "1" (单选) 或 "2" (多选)
    is_choice = bvalue in ('1', '2')
    choice_type = None
    if bvalue == '1':
        choice_type = 'single'
    elif bvalue == '2':
        choice_type = 'multiple'
    
    return {
        'is_objective': is_objective,
        'is_choice': is_choice,
        'choice_type': choice_type
    }


def calculate_type_statistics(questions: list, results: list) -> dict:
    """
    计算按题目类型分类的统计数据
    
    Args:
        questions: 题目列表（包含 questionType 和 bvalue）
        results: 评估结果列表（包含 is_correct）
        
    Returns:
        {
            "objective": {"total": int, "correct": int, "accuracy": float},
            "subjective": {"total": int, "correct": int, "accuracy": float},
            "choice": {"total": int, "correct": int, "accuracy": float},
            "non_choice": {"total": int, "correct": int, "accuracy": float}
        }
    """
    stats = {
        'objective': {'total': 0, 'correct': 0},
        'subjective': {'total': 0, 'correct': 0},
        'choice': {'total': 0, 'correct': 0},
        'non_choice': {'total': 0, 'correct': 0}
    }
    
    for q, r in zip(questions, results):
        category = classify_question_type(q)
        is_correct = r.get('is_correct', False)
        
        # 主观/客观分类
        if category['is_objective']:
            stats['objective']['total'] += 1
            if is_correct:
                stats['objective']['correct'] += 1
        else:
            stats['subjective']['total'] += 1
            if is_correct:
                stats['subjective']['correct'] += 1
        
        # 选择/非选择分类
        if category['is_choice']:
            stats['choice']['total'] += 1
            if is_correct:
                stats['choice']['correct'] += 1
        else:
            stats['non_choice']['total'] += 1
            if is_correct:
                stats['non_choice']['correct'] += 1
    
    # 计算准确率
    for key in stats:
        total = stats[key]['total']
        correct = stats[key]['correct']
        stats[key]['accuracy'] = correct / total if total > 0 else 0
    
    return stats
```

### 1. 前端组件

#### 1.1 BatchEvaluationPage 批量评估主页面
```javascript
// 页面状态
const pageState = {
    currentTab: 'tasks',      // 'tasks' | 'datasets'
    selectedTask: null,       // 当前选中的任务
    selectedBook: null,       // 当前选中的图书
    taskList: [],             // 任务列表
    bookList: [],             // 图书列表
    datasetList: []           // 数据集列表
};
```

#### 1.2 TaskManager 任务管理组件
- 历史任务列表展示
- 新建任务入口
- 任务状态显示（待评估/评估中/已完成）

#### 1.3 TaskDetail 任务详情组件
- 作业任务列表（显示准确率）
- 基准效果匹配状态
- 评估进度条
- 总体报告展示

#### 1.4 DatasetManager 数据集管理组件
- 图书列表（按学科分组）
- 书本详情和页码列表
- 数据集配置入口

#### 1.5 CreateTaskModal 新建任务弹窗
- 作业任务多选列表
- 筛选条件（学科、时间范围）
- 已选数量统计

#### 1.6 DatasetEditModal 数据集编辑弹窗
- 页码选择
- 基准效果编辑器（复用现有组件）

#### 1.7 EvaluationDetailDrawer 评估详情抽屉
- 单个作业的详细评估结果
- 与单次评估页面一致的展示

### 2. 后端API接口

#### 2.1 获取图书列表
```
GET /api/batch/books
Query Parameters:
  - subject_id: 学科ID (可选，不传则返回全部)

Response:
{
  "success": true,
  "data": {
    "0": [  // 英语
      {
        "book_id": "123",
        "book_name": "人教版英语七年级上册",
        "subject_id": 0,
        "chapter_count": 12,
        "page_count": 120
      }
    ],
    "1": [...],  // 语文
    "2": [...],  // 数学
    "3": [...]   // 物理
  }
}
```

#### 2.2 获取书本页码列表
```
GET /api/batch/books/<book_id>/pages
Response:
{
  "success": true,
  "data": {
    "book_id": "123",
    "book_name": "人教版英语七年级上册",
    "chapters": [
      {
        "chapter_id": "c1",
        "chapter_name": "Unit 1",
        "pages": [1, 2, 3, 4, 5]
      }
    ],
    "all_pages": [1, 2, 3, ..., 120]
  }
}
```

#### 2.3 数据集管理
```
GET /api/batch/datasets
Query Parameters:
  - book_id: 图书ID (可选)

Response:
{
  "success": true,
  "data": [
    {
      "dataset_id": "ds_001",
      "book_id": "123",
      "book_name": "人教版英语七年级上册",
      "pages": [1, 2, 3],
      "question_count": 30,
      "created_at": "2026-01-09T10:00:00"
    }
  ]
}

POST /api/batch/datasets
Body:
{
  "book_id": "123",
  "pages": [1, 2, 3],
  "base_effects": {
    "1": [...],  // 第1页的基准效果
    "2": [...],
    "3": [...]
  }
}

DELETE /api/batch/datasets/<dataset_id>
```

#### 2.3.1 检查页码可用作业图片
```
GET /api/batch/datasets/available-homework
Query Parameters:
  - book_id: 图书ID (必需)
  - page_num: 页码 (必需)
  - minutes: 时间范围，默认30分钟

Response:
{
  "success": true,
  "data": {
    "available": true,
    "homework_list": [
      {
        "homework_id": "hw_001",
        "student_name": "张三",
        "pic_path": "https://...",
        "create_time": "2026-01-09T10:00:00"
      }
    ]
  }
}
```

#### 2.3.2 数据集页码自动识别基准效果
```
POST /api/batch/datasets/auto-recognize
Body:
{
  "book_id": "123",
  "page_num": 5,
  "homework_id": "hw_001"  // 可选，不传则使用最近的作业图片
}

Response:
{
  "success": true,
  "base_effect": [
    {"answer":"D","correct":"yes","index":"1","tempIndex":0,"userAnswer":"D"},
    {"answer":"C","correct":"yes","index":"2","tempIndex":1,"userAnswer":"C"}
  ],
  "source_homework": {
    "homework_id": "hw_001",
    "student_name": "张三",
    "pic_path": "https://..."
  }
}
```

#### 2.4 批量评估任务管理
```
GET /api/batch/tasks
Response:
{
  "success": true,
  "data": [
    {
      "task_id": "task_001",
      "name": "批量评估任务-20260109",
      "status": "completed",  // pending | running | completed
      "homework_count": 10,
      "completed_count": 10,
      "overall_accuracy": 0.85,
      "created_at": "2026-01-09T10:00:00"
    }
  ]
}

POST /api/batch/tasks
Body:
{
  "name": "批量评估任务-20260109",
  "homework_ids": ["hw_001", "hw_002", ...]
}

Response:
{
  "success": true,
  "task_id": "task_001",
  "homework_items": [
    {
      "homework_id": "hw_001",
      "book_id": "123",
      "page_num": 5,
      "matched_dataset": "ds_001",  // 匹配到的数据集ID，null表示未匹配
      "status": "pending"
    }
  ]
}

GET /api/batch/tasks/<task_id>
Response:
{
  "success": true,
  "data": {
    "task_id": "task_001",
    "name": "批量评估任务-20260109",
    "status": "completed",
    "homework_items": [...],
    "overall_report": {...}
  }
}

DELETE /api/batch/tasks/<task_id>
```

#### 2.5 执行批量评估
```
POST /api/batch/tasks/<task_id>/evaluate
Body:
{
  "auto_recognize": true  // 是否对未匹配的作业自动识别基准效果
}

Response (SSE流式返回):
data: {"type": "progress", "homework_id": "hw_001", "status": "evaluating"}
data: {"type": "result", "homework_id": "hw_001", "accuracy": 0.9}
data: {"type": "progress", "homework_id": "hw_002", "status": "evaluating"}
data: {"type": "result", "homework_id": "hw_002", "accuracy": 0.85}
data: {"type": "complete", "overall_accuracy": 0.875}
```

#### 2.6 获取单个作业评估详情
```
GET /api/batch/tasks/<task_id>/homework/<homework_id>
Response:
{
  "success": true,
  "data": {
    "homework_id": "hw_001",
    "accuracy": 0.9,
    "evaluation": {
      // 与单次评估结果结构一致
      "total_questions": 10,
      "correct_count": 9,
      "error_count": 1,
      "errors": [...],
      "error_distribution": {...}
    },
    "base_effect": [...],
    "homework_result": [...]
  }
}
```

#### 2.7 生成AI分析报告
```
POST /api/batch/tasks/<task_id>/ai-report
Response:
{
  "success": true,
  "report": {
    "summary": "本次批量评估共评估10份作业...",
    "diagnosis": "主要问题集中在...",
    "suggestions": ["建议1", "建议2", ...]
  }
}
```

#### 2.8 导出Excel
```
GET /api/batch/tasks/<task_id>/export
Response: Excel文件下载
```

## Data Models

### 1. 图书数据结构
```typescript
interface Book {
  book_id: string;
  book_name: string;
  subject_id: number;
  chapter_count: number;
  page_count: number;
}

interface Chapter {
  chapter_id: string;
  chapter_name: string;
  book_id: string;
  pages: number[];
}
```

### 2. 数据集数据结构
```typescript
interface Dataset {
  dataset_id: string;
  book_id: string;
  book_name: string;
  pages: number[];
  base_effects: {
    [page: string]: BaseEffectItem[];
  };
  question_count: number;
  created_at: string;
}

interface BaseEffectItem {
  answer: string;
  correct: "yes" | "no";
  index: string;
  tempIndex: number;
  userAnswer: string;
  mainAnswer?: string;
  questionType?: string;  // "objective" = 客观题，其他 = 主观题
  bvalue?: string;        // "1" = 单选，"2" = 多选，其他 = 非选择题
}
```

### 3. 批量评估任务数据结构
```typescript
interface BatchTask {
  task_id: string;
  name: string;
  status: "pending" | "running" | "completed";
  homework_items: HomeworkItem[];
  overall_report?: OverallReport;
  created_at: string;
  updated_at: string;
}

interface HomeworkItem {
  homework_id: string;
  book_id: string;
  book_name: string;
  page_num: number;
  student_id: string;
  student_name: string;
  matched_dataset: string | null;
  status: "pending" | "matched" | "auto_recognize" | "evaluating" | "completed" | "failed";
  accuracy?: number;
  evaluation?: EvaluationResult;
}

interface EvaluationResult {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  total_questions: number;
  correct_count: number;
  error_count: number;
  errors: ErrorItem[];
  error_distribution: {
    [errorType: string]: number;
  };
  // 题目类型分类统计
  by_question_type: {
    objective: { total: number; correct: number; accuracy: number };  // 客观题
    subjective: { total: number; correct: number; accuracy: number }; // 主观题
    choice: { total: number; correct: number; accuracy: number };     // 选择题
    non_choice: { total: number; correct: number; accuracy: number }; // 非选择题
  };
}

interface ErrorItem {
  index: string;
  error_type: string;
  explanation: string;
  severity: string;
  base_effect: {
    answer: string;
    userAnswer: string;
    correct: string;
  };
  ai_result: {
    answer: string;
    userAnswer: string;
    correct: string;
  };
  // 题目类型标注
  question_category: {
    is_objective: boolean;  // 是否客观题
    is_choice: boolean;     // 是否选择题
    choice_type?: string;   // "single" | "multiple" | null
  };
}
```

### 4. 总体报告数据结构
```typescript
interface OverallReport {
  overall_accuracy: number;
  total_homework: number;
  total_questions: number;
  correct_questions: number;
  by_book: {
    [book_id: string]: {
      book_name: string;
      accuracy: number;
      homework_count: number;
    };
  };
  by_page: {
    [page_num: string]: {
      accuracy: number;
      homework_count: number;
    };
  };
  by_question_type: {
    // 主观题/客观题分类
    objective: { total: number; correct: number; accuracy: number };
    subjective: { total: number; correct: number; accuracy: number };
    // 选择题/非选择题分类
    choice: { total: number; correct: number; accuracy: number };
    non_choice: { total: number; correct: number; accuracy: number };
  };
  error_distribution: {
    [errorType: string]: number;
  };
  ai_analysis?: {
    summary: string;
    diagnosis: string;
    suggestions: string[];
  };
}
```

### 5. Excel导出数据结构
```typescript
interface ExcelExport {
  overview: {
    task_name: string;
    created_at: string;
    overall_accuracy: number;
    total_homework: number;
    total_questions: number;
    // 题目类型分类统计
    objective_accuracy: number;   // 客观题准确率
    subjective_accuracy: number;  // 主观题准确率
    choice_accuracy: number;      // 选择题准确率
    non_choice_accuracy: number;  // 非选择题准确率
  };
  homework_summary: {
    homework_id: string;
    book_name: string;
    page_num: number;
    student_name: string;
    accuracy: number;
    correct_count: number;
    error_count: number;
    // 题目类型分类统计
    objective_accuracy: number;
    subjective_accuracy: number;
    choice_accuracy: number;
    non_choice_accuracy: number;
  }[];
  detail_data: {
    homework_id: string;
    question_index: string;
    base_answer: string;
    ai_answer: string;
    is_correct: boolean;
    error_type?: string;
    // 题目类型标注
    is_objective: boolean;  // 是否客观题
    is_choice: boolean;     // 是否选择题
    choice_type?: string;   // "单选" | "多选" | null
  }[];
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 图书数据按学科分组正确性
*For any* book returned by the API, the book's subject_id should match the group key it belongs to
**Validates: Requirements 2.1**

### Property 2: 页码归属正确性
*For any* page returned for a book, the page should belong to that specific book_id
**Validates: Requirements 2.3**

### Property 3: 数据集保存round-trip
*For any* saved dataset, loading it back should produce an identical object with the same pages and base_effects
**Validates: Requirements 3.3**

### Property 4: 数据集列表字段完整性
*For any* dataset in the list, it should contain book_name, pages, question_count, and created_at fields
**Validates: Requirements 3.4**

### Property 5: 数据集删除正确性
*For any* deleted dataset, querying by its dataset_id should return not found
**Validates: Requirements 3.5**

### Property 6: 作业任务状态过滤正确性
*For any* homework returned in task creation, its status should equal 3
**Validates: Requirements 4.2**

### Property 7: 任务作业数量一致性
*For any* created task, the number of homework_items should equal the number of selected homework_ids
**Validates: Requirements 4.4**

### Property 8: 任务ID唯一性
*For any* two tasks, their task_ids should be different
**Validates: Requirements 4.5**

### Property 9: 基准效果匹配正确性
*For any* homework with matched_dataset not null, the dataset's book_id and pages should contain the homework's book_id and page_num
**Validates: Requirements 5.1, 5.2**

### Property 10: 准确率计算正确性
*For any* evaluation result, accuracy should equal correct_count / total_questions
**Validates: Requirements 6.2**

### Property 11: 任务完成状态正确性
*For any* task with status "completed", all homework_items should have status "completed" or "failed"
**Validates: Requirements 6.5**

### Property 12: 总体报告统计正确性
*For any* overall report, overall_accuracy should equal sum(correct_questions) / sum(total_questions) across all homework
**Validates: Requirements 7.1, 7.2**

### Property 13: Excel工作表完整性
*For any* exported Excel file, it should contain both overview sheet and detail sheet
**Validates: Requirements 8.2, 8.3**

### Property 14: 历史任务排序正确性
*For any* task list, tasks should be sorted by created_at in descending order
**Validates: Requirements 9.1**

### Property 15: 任务加载round-trip
*For any* saved task, loading it by task_id should produce the same task data
**Validates: Requirements 9.2**

### Property 16: 任务删除正确性
*For any* deleted task, querying by its task_id should return not found
**Validates: Requirements 9.3**

### Property 17: 题目类型分类正确性
*For any* question with questionType and bvalue fields, the classification function should correctly identify: objective (questionType === "objective"), choice (bvalue === "1" or "2"), and choice_type (single/multiple/null)
**Validates: Requirements 12.2, 12.3**

### Property 18: 题目类型统计计算正确性
*For any* list of questions with type classifications and evaluation results, the type statistics should correctly sum totals and calculate accuracies for each category (objective/subjective, choice/non_choice)
**Validates: Requirements 12.4, 12.5, 12.6**

### Property 19: 数据集题目类型字段保存正确性
*For any* saved dataset with base_effects, each question item should contain questionType and bvalue fields from the original data_value
**Validates: Requirements 12.7**

### Property 20: 评估结果题目类型标注正确性
*For any* evaluation result, each error item should contain question_category with is_objective and is_choice fields
**Validates: Requirements 12.8**

### Property 21: 一键AI评估分类统计完整性
*For any* completed AI evaluation task, the overall_report should contain by_question_type with objective, subjective, choice, and non_choice statistics
**Validates: Requirements 6.6, 6.7**

### Property 22: Excel导出分类统计完整性
*For any* exported Excel file, the overview sheet should contain objective_accuracy, subjective_accuracy, choice_accuracy, non_choice_accuracy, and detail sheet should contain is_objective and is_choice columns
**Validates: Requirements 8.4, 8.5**

## Error Handling

### 1. 数据库连接错误
- 显示友好的错误提示
- 提供重试按钮
- 记录错误日志

### 2. 数据集匹配失败
- 标记作业为"未匹配"状态
- 提供"自动识别"选项
- 允许手动配置基准效果

### 3. AI识别失败
- 标记该作业为"识别失败"
- 继续处理下一个作业
- 在报告中标注失败原因

### 4. 评估过程中断
- 保存已完成的评估结果
- 支持断点续评
- 显示中断原因

### 5. Excel导出失败
- 显示错误提示
- 提供重试选项
- 支持导出部分数据

## Testing Strategy

### 单元测试
- 测试准确率计算函数
- 测试数据集匹配逻辑
- 测试总体报告统计计算
- 测试Excel数据格式化
- 测试题目类型分类函数 (classify_question_type)
- 测试题目类型统计计算函数 (calculate_type_statistics)

### 属性测试
使用 **Hypothesis** (Python) 进行属性测试：
- 每个属性测试运行至少100次迭代
- 测试标注格式：`**Feature: batch-evaluation, Property {number}: {property_text}**`

重点属性测试：
- Property 17: 题目类型分类正确性
- Property 18: 题目类型统计计算正确性
- Property 19: 数据集题目类型字段保存正确性
- Property 20: 评估结果题目类型标注正确性

### 集成测试
- 测试图书数据API
- 测试数据集CRUD API
- 测试批量评估任务流程
- 测试Excel导出功能
- 测试一键AI评估的题目类型分类统计

### E2E测试
- 测试完整的批量评估流程
- 测试Tab切换功能
- 测试弹窗交互
- 测试题目类型分类统计在各页面的展示

