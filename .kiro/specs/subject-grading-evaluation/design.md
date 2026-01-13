# Design Document: AI学科批改评估系统

## Overview

本系统将现有的"AI对比分析"页面重构为"AI学科批改评估"页面，提供按学科分类的AI批改效果评估功能。系统从MySQL数据库获取最近一小时的AI批改结果，用户可上传图片识别基准效果，通过DeepSeek大模型自动评估AI批改输出是否与基准效果一致。

### 核心功能
1. 按学科（英语、语文、数学、物理）分Tab展示
2. 自动获取数据库最近1小时的批改数据
3. 图片识别生成基准效果JSON
4. 模块化编辑基准效果
5. DeepSeek自动评估对比
6. 丰富的可视化展示

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS/CSS)                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │ 英语Tab │ │ 语文Tab │ │ 数学Tab │ │ 物理Tab │               │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │
│       └───────────┴───────────┴───────────┘                     │
│                         │                                        │
│  ┌──────────────────────┴──────────────────────┐                │
│  │              Subject Evaluation Panel        │                │
│  │  ┌─────────────┐  ┌─────────────────────┐   │                │
│  │  │ 数据列表    │  │ 基准效果编辑器      │   │                │
│  │  │ (从数据库)  │  │ (模块化卡片)        │   │                │
│  │  └─────────────┘  └─────────────────────┘   │                │
│  │  ┌─────────────────────────────────────┐    │                │
│  │  │         评估结果可视化               │    │                │
│  │  │  统计卡片 | 折线图 | 饼图 | 热力图   │    │                │
│  │  └─────────────────────────────────────┘    │                │
│  └─────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (Flask)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ /api/grading/   │  │ /api/grading/   │  │ /api/grading/   │  │
│  │ homework        │  │ recognize       │  │ evaluate        │  │
│  │ (获取批改数据)  │  │ (图片识别)      │  │ (DeepSeek评估)  │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌───────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   MySQL Database  │  │  Vision Model   │  │    DeepSeek API     │
│   (zp_homework)   │  │  (豆包/Qwen)    │  │   (评估分析)        │
└───────────────────┘  └─────────────────┘  └─────────────────────┘
```

## Components and Interfaces

### 1. 前端组件

#### 1.1 SubjectTabs 学科标签组件
```javascript
// 学科配置
const SUBJECTS = {
    0: { id: 0, name: '英语', icon: '🔤' },
    1: { id: 1, name: '语文', icon: '📖' },
    2: { id: 2, name: '数学', icon: '🔢' },
    3: { id: 3, name: '物理', icon: '⚡' }
};
```

#### 1.2 HomeworkList 批改数据列表组件
- 展示从数据库获取的批改记录
- 支持选择记录进行评估

#### 1.3 BaseEffectEditor 基准效果编辑器
- 模块化卡片展示每道题
- 支持编辑answer、correct、userAnswer、mainAnswer字段
- 支持添加/删除题目

#### 1.4 EvaluationResult 评估结果组件
- 统计卡片（准确率、精确率、召回率、F1值、正确数、错误数）
- 错误题目明细表格
- 可视化图表：
  - 准确率折线图（批次变化趋势）
  - 错误类型饼图（识别错误/判断错误/格式错误/其他错误分布）
  - 评分偏差热力图（题目×批次维度）
  - 学科准确率柱状图（多学科对比）
  - 题目正确率条形图（每题正确率排名）
  - 批改耗时箱线图（响应时间分布）
  - 多维能力雷达图（准确率/精确率/召回率/F1值/一致性）
  - 错误趋势面积图（错误数量随时间变化）
  - 答案分布散点图（正确/错误答案分布）

### 2. 后端API接口

#### 2.1 获取批改数据
```
GET /api/grading/homework
Query Parameters:
  - subject_id: 学科ID (0-3)
  - hours: 时间范围（默认1小时）
  
Response:
{
  "success": true,
  "data": [
    {
      "id": "1234567890",
      "student_id": "student_001",
      "page_num": 5,
      "pic_path": "https://...",
      "homework_result": "[{...}]",
      "create_time": "2026-01-08 14:30:00",
      "question_count": 10
    }
  ]
}
```

#### 2.2 图片识别基准效果
```
POST /api/grading/recognize
Body:
{
  "image": "base64...",
  "subject_id": 2
}

Response:
{
  "success": true,
  "base_effect": [
    {"answer":"D","correct":"yes","index":"1","tempIndex":0,"userAnswer":"D"},
    {"answer":"C","correct":"yes","index":"2","tempIndex":1,"userAnswer":"C"}
  ]
}
```

#### 2.3 DeepSeek评估对比
```
POST /api/grading/evaluate
Body:
{
  "base_effect": [...],
  "homework_result": [...],
  "subject_id": 2
}

Response:
{
  "success": true,
  "evaluation": {
    "accuracy": 0.85,
    "precision": 0.88,
    "recall": 0.82,
    "f1_score": 0.85,
    "total_questions": 10,
    "correct_count": 8,
    "error_count": 2,
    "errors": [
      {
        "index": "3",
        "base_effect": {"answer":"B","correct":"yes","userAnswer":"B"},
        "ai_result": {"answer":"B","correct":"no","userAnswer":"B"},
        "error_type": "判断错误",
        "explanation": "AI将正确答案判断为错误"
      }
    ],
    "error_distribution": {
      "识别错误": 1,
      "判断错误": 1,
      "格式错误": 0,
      "其他错误": 0
    },
    "suggestions": ["建议优化判断逻辑..."]
  }
}
```

## Data Models

### 1. 基准效果数据结构
```typescript
interface BaseEffectItem {
  answer: string;        // 标准答案
  correct: "yes" | "no"; // 是否正确
  index: string;         // 题号
  tempIndex: number;     // 临时索引
  userAnswer: string;    // 用户手写答案
  mainAnswer?: string;   // 主观题答案（可选）
}

type BaseEffect = BaseEffectItem[];
```

### 2. 评估结果数据结构
```typescript
interface EvaluationResult {
  accuracy: number;      // 准确率
  precision: number;     // 精确率
  recall: number;        // 召回率
  f1_score: number;      // F1值
  total_questions: number;
  correct_count: number;
  error_count: number;
  errors: ErrorItem[];
  error_distribution: {
    识别错误: number;
    判断错误: number;
    格式错误: number;
    其他错误: number;
  };
  suggestions: string[];
}

interface ErrorItem {
  index: string;
  base_effect: BaseEffectItem;
  ai_result: BaseEffectItem;
  error_type: string;
  explanation: string;
}
```

### 3. 评估记录数据结构
```typescript
interface EvaluationRecord {
  id: string;
  subject_id: number;
  homework_id: string;
  timestamp: string;
  accuracy: number;
  evaluation: EvaluationResult;
  base_effect: BaseEffect;
  homework_result: BaseEffect;
}
```

### 4. 图表数据结构
```typescript
// 折线图数据
interface LineChartData {
  labels: string[];           // 批次标签
  datasets: {
    label: string;
    data: number[];
    borderColor: string;
  }[];
}

// 饼图数据
interface PieChartData {
  labels: string[];           // 错误类型
  data: number[];             // 数量
  backgroundColor: string[];
}

// 热力图数据
interface HeatmapData {
  xLabels: string[];          // 题号
  yLabels: string[];          // 批次
  data: number[][];           // 偏差值矩阵
}

// 雷达图数据
interface RadarChartData {
  labels: string[];           // 维度名称
  datasets: {
    label: string;
    data: number[];
    backgroundColor: string;
  }[];
}

// 柱状图数据
interface BarChartData {
  labels: string[];           // 学科/题号
  datasets: {
    label: string;
    data: number[];
    backgroundColor: string;
  }[];
}

// 箱线图数据
interface BoxPlotData {
  labels: string[];           // 分组标签
  datasets: {
    label: string;
    data: {
      min: number;
      q1: number;
      median: number;
      q3: number;
      max: number;
    }[];
  }[];
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 学科数据查询正确性
*For any* subject_id in [0,1,2,3], querying homework data should return only records where subject_id matches the query parameter
**Validates: Requirements 1.1, 2.2**

### Property 2: Tab切换状态保持
*For any* sequence of Tab switches, the data loaded should always correspond to the currently active Tab's subject_id
**Validates: Requirements 2.2, 2.3**

### Property 3: 基准效果编辑同步
*For any* edit operation on a BaseEffectItem, the underlying data structure should immediately reflect the change
**Validates: Requirements 3.3**

### Property 4: 题目卡片数量一致性
*For any* BaseEffect array, the number of rendered cards should equal the array length
**Validates: Requirements 4.1**

### Property 5: 题号自动分配正确性
*For any* add operation, the new item's index should be max(existing indices) + 1, and tempIndex should be array.length
**Validates: Requirements 4.3**

### Property 6: 题号重排正确性
*For any* delete operation, the remaining items should have consecutive index values starting from "1"
**Validates: Requirements 4.4**

### Property 7: 评估准确率计算正确性
*For any* pair of base_effect and homework_result arrays, accuracy should equal correct_count / total_questions
**Validates: Requirements 5.3, 6.1**

### Property 8: 错误分类完整性
*For any* evaluation result, the sum of error_distribution values should equal error_count
**Validates: Requirements 7.3**

### Property 9: 评估记录保存round-trip
*For any* saved evaluation record, loading it back should produce an identical object
**Validates: Requirements 8.2**

### Property 10: 历史记录筛选正确性
*For any* filter by subject_id, all returned records should have matching subject_id
**Validates: Requirements 8.3**

## Error Handling

### 1. 数据库连接错误
- 显示友好的错误提示
- 提供重试按钮
- 记录错误日志

### 2. 图片识别失败
- 显示识别失败原因
- 允许重新上传
- 提供手动输入选项

### 3. DeepSeek API调用失败
- 显示API错误信息
- 提供重试选项
- 支持降级到本地算法评估

### 4. 数据格式错误
- JSON解析失败时显示原始数据
- 提供格式修复建议

## Testing Strategy

### 单元测试
- 测试准确率计算函数
- 测试题号分配逻辑
- 测试数据格式转换

### 属性测试
使用 **Hypothesis** (Python) 进行属性测试：
- 每个属性测试运行至少100次迭代
- 测试标注格式：`**Feature: subject-grading-evaluation, Property {number}: {property_text}**`

### 集成测试
- 测试数据库查询API
- 测试DeepSeek评估API
- 测试前后端数据流

### E2E测试
- 测试完整的评估流程
- 测试Tab切换功能
- 测试图表渲染
