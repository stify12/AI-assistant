# Design Document - Prompt 调优与评测系统

## Overview

本设计文档描述 Prompt 调优与评测系统的技术架构和实现方案。该系统为 AI 助手平台提供 Prompt 调试、批量评测、智能评分功能，帮助用户迭代优化 Prompt 效果。

系统采用 Flask 后端 + 原生 JavaScript 前端的架构，与现有 AI 助手平台保持一致。核心功能包括：
- **调试模式**: 单条样本测试，快速验证 Prompt 效果
- **批量评测**: 管理评测数据集，批量生成模型回答
- **智能评分**: AI 自动评分（1-10分），支持自定义评分规则

## Architecture

```mermaid
graph TB
    subgraph Frontend
        UI[prompt-optimize.html]
        JS[prompt-optimize.js]
        CSS[prompt-optimize.css]
    end
    
    subgraph Backend
        APP[app.py]
        subgraph APIs
            TASK[/api/prompt-task]
            SAMPLE[/api/prompt-sample]
            EVAL[/api/prompt-eval]
            SCORE[/api/prompt-score]
            VERSION[/api/prompt-version]
        end
    end
    
    subgraph Storage
        TASKS_DIR[prompt_tasks/]
        JSON[(JSON Files)]
    end
    
    subgraph External
        VISION[Vision Models]
        SCORING[Scoring Models]
    end
    
    UI --> JS
    JS --> APIs
    APIs --> APP
    APP --> TASKS_DIR
    TASKS_DIR --> JSON
    APP --> VISION
    APP --> SCORING
```

## Components and Interfaces

### 1. Frontend Components

#### 1.1 页面结构 (prompt-optimize.html)
```
┌─────────────────────────────────────────────────────────────┐
│ Header: 提示词优化 | 返回主页                                  │
├─────────────────────────────────────────────────────────────┤
│ Tabs: [调试] [批量] [智能优化]                                 │
├─────────────────────────────────────────────────────────────┤
│ Prompt Editor Area                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Prompt: [textarea with {{变量}} support]                │ │
│ │ Model: [select] Version: [select] [一键改写] [保存]      │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Tab Content Area (varies by selected tab)                   │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 调试模式界面
```
┌─────────────────────────────────────────────────────────────┐
│ 变量输入区                                                   │
│ ┌──────────────────┐ ┌──────────────────┐                   │
│ │ {{image}}: [上传] │ │ {{text}}: [输入] │                   │
│ └──────────────────┘ └──────────────────┘                   │
├─────────────────────────────────────────────────────────────┤
│ [生成模型回答]                                               │
├─────────────────────────────────────────────────────────────┤
│ 模型回答                        │ 理想回答                   │
│ ┌─────────────────────────────┐ │ ┌─────────────────────┐   │
│ │ (streaming response)        │ │ │ [AI生成] [手动输入]  │   │
│ └─────────────────────────────┘ │ └─────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ 评分: [1][2][3][4][5][6][7][8][9][10]  [添加至评测集]        │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3 批量评测界面
```
┌─────────────────────────────────────────────────────────────┐
│ [添加行] [上传文件] [AI生成变量] [生成全部回答] [智能评分]     │
├─────────────────────────────────────────────────────────────┤
│ 统计: 平均分 7.5 | 已评分 15/20 | 分布 [图表]                │
├─────────────────────────────────────────────────────────────┤
│ │序号│ 提问(变量)    │ 模型回答      │ 理想回答 │ 评分      │
│ ├────┼───────────────┼───────────────┼──────────┼───────────┤
│ │ 1  │ [img] text... │ response...   │ ideal... │ 8 AI评分  │
│ │ 2  │ [img] text... │ response...   │ ideal... │ 7 AI评分  │
│ │ ...│               │               │          │           │
├─────────────────────────────────────────────────────────────┤
│ 分页: 共 5 页 | [1] [2] [3] ... | 20条/页                    │
└─────────────────────────────────────────────────────────────┘
```

### 2. Backend APIs

#### 2.1 任务管理 API
```python
# POST /api/prompt-task - 创建新任务
Request: { "name": "作业批改优化", "prompt": "...", "model": "..." }
Response: { "task_id": "uuid", "created_at": "..." }

# GET /api/prompt-task/<task_id> - 获取任务详情
Response: { "task_id": "...", "prompt": "...", "samples": [...], "versions": [...] }

# PUT /api/prompt-task/<task_id> - 更新任务
Request: { "prompt": "...", "scoring_rules": "..." }

# GET /api/prompt-tasks - 获取任务列表
Response: [{ "task_id": "...", "name": "...", "avg_score": 7.5, "sample_count": 20 }]
```

#### 2.2 样本管理 API
```python
# POST /api/prompt-sample - 添加样本
Request: { "task_id": "...", "variables": {"image": "base64...", "text": "..."} }
Response: { "sample_id": "uuid" }

# POST /api/prompt-sample/batch - 批量导入样本
Request: FormData with Excel/CSV file
Response: { "imported": 20, "failed": 0 }

# PUT /api/prompt-sample/<sample_id> - 更新样本
Request: { "ideal_answer": "...", "score": 8, "score_reason": "..." }
```

#### 2.3 评测 API
```python
# POST /api/prompt-eval/generate - 生成模型回答
Request: { "task_id": "...", "sample_ids": ["..."] or "all" }
Response: SSE stream with progress and results

# POST /api/prompt-eval/generate-ideal - AI生成理想回答
Request: { "sample_id": "...", "model": "qwen3-max" }
Response: { "ideal_answer": "..." }
```

#### 2.4 评分 API
```python
# POST /api/prompt-score/rules - 生成评分规则
Request: { "task_id": "...", "method": "from_prompt" | "from_samples" }
Response: { "rules": "9-10分: ...\n7-8分: ..." }

# POST /api/prompt-score/batch - 批量AI评分
Request: { "task_id": "...", "sample_ids": ["..."] or "unscored" or "all" }
Response: SSE stream with scoring progress and results
```

#### 2.5 版本管理 API
```python
# POST /api/prompt-version - 保存新版本
Request: { "task_id": "..." }
Response: { "version_id": "v1", "avg_score": 7.5 }

# GET /api/prompt-version/<task_id>/compare - 版本比对
Request: { "v1": "...", "v2": "..." }
Response: { "prompt_diff": "...", "score_comparison": {...} }
```

## Data Models

### 1. PromptTask (任务)
```json
{
  "task_id": "uuid-string",
  "name": "作业批改优化",
  "created_at": "2024-12-19T10:00:00Z",
  "updated_at": "2024-12-19T15:30:00Z",
  "current_prompt": "请识别图片中的答案...",
  "model": "doubao-1-5-vision-pro-32k-250115",
  "scoring_rules": "9-10分: 格式完全正确...",
  "variables": [
    { "name": "image", "type": "image" },
    { "name": "question_type", "type": "text" }
  ],
  "versions": ["v1", "v2", "v3"],
  "current_version": "v3"
}
```

### 2. Sample (样本)
```json
{
  "sample_id": "uuid-string",
  "task_id": "uuid-string",
  "created_at": "2024-12-19T10:05:00Z",
  "variables": {
    "image": "base64-or-url",
    "question_type": "选择题"
  },
  "model_response": "识别结果: A, B, C...",
  "ideal_answer": "正确答案: A, B, D...",
  "score": 7,
  "score_source": "ai",
  "score_reason": "格式正确，但第3题识别错误",
  "scored_at": "2024-12-19T11:00:00Z"
}
```

### 3. PromptVersion (版本)
```json
{
  "version_id": "v3",
  "task_id": "uuid-string",
  "created_at": "2024-12-19T14:00:00Z",
  "prompt": "优化后的Prompt内容...",
  "scoring_rules": "...",
  "statistics": {
    "sample_count": 20,
    "scored_count": 18,
    "avg_score": 7.8,
    "score_distribution": {
      "9-10": 5,
      "7-8": 8,
      "5-6": 4,
      "3-4": 1,
      "1-2": 0
    }
  }
}
```

### 4. ScoringRules (评分规则)
```json
{
  "scale": "1-10",
  "rules": [
    { "range": "9-10", "criteria": "格式完全正确，无遗漏，所有答案提取准确" },
    { "range": "7-8", "criteria": "格式正确，存在1-2处小错误" },
    { "range": "5-6", "criteria": "格式基本正确，存在3-4处错误或遗漏" },
    { "range": "3-4", "criteria": "格式有问题，存在多处错误" },
    { "range": "1-2", "criteria": "格式严重错误或无法解析" }
  ],
  "generated_from": "prompt",
  "created_at": "2024-12-19T10:00:00Z"
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Variable Detection Consistency
*For any* Prompt text containing `{{variableName}}` patterns, the variable detection function should extract all unique variable names in the order they appear.
**Validates: Requirements 2.2**

### Property 2: Score Recording Validity
*For any* score value between 1 and 10 (inclusive), the system should accept and store it; for any value outside this range, the system should reject it.
**Validates: Requirements 2.6**

### Property 3: Sample Addition Increases Dataset Size
*For any* valid sample added to the dataset, the dataset size should increase by exactly 1.
**Validates: Requirements 2.7, 3.2**

### Property 4: File Import Preserves Data
*For any* valid Excel/CSV file with N rows of sample data, importing should create N samples with matching variable values.
**Validates: Requirements 3.3**

### Property 5: Pagination Correctness
*For any* dataset with N samples and page size P, the number of pages should equal ceil(N/P), and each page should contain at most P items.
**Validates: Requirements 3.5**

### Property 6: Batch Generation Processes All Unscored
*For any* dataset with samples, "生成全部回答" should process exactly those samples without model_response.
**Validates: Requirements 4.1**

### Property 7: Progress Tracking Accuracy
*For any* batch operation processing N items, the progress indicator should show values from 0/N to N/N monotonically increasing.
**Validates: Requirements 4.2, 4.3**

### Property 8: AI Scoring Completeness
*For any* "为未评分的回答评分" operation, all samples without scores should receive scores; for "为所有回答评分", all samples should be re-scored.
**Validates: Requirements 5.5, 5.6**

### Property 9: Score Display Format
*For any* AI-scored sample, the displayed score should be in range 1-10 and include the "AI评分" label.
**Validates: Requirements 5.7**

### Property 10: Scoring Rules Validation
*For any* saved scoring rules, the system should validate that criteria for all score ranges (1-2, 3-4, 5-6, 7-8, 9-10) are defined.
**Validates: Requirements 6.3**

### Property 11: Statistics Calculation
*For any* dataset with scored samples, the average score should equal sum(scores)/count(scored_samples), and distribution should correctly categorize all scores.
**Validates: Requirements 8.1**

### Property 12: Export Data Completeness
*For any* export operation, the generated Excel file should contain all samples with their variables, responses, ideal answers, and scores.
**Validates: Requirements 8.2**

### Property 13: Sorting Correctness
*For any* sort operation by score, the resulting order should be monotonically increasing or decreasing based on sort direction.
**Validates: Requirements 8.3**

### Property 14: Optimization Prerequisite Check
*For any* "智能优化" operation, the system should only proceed if the dataset has at least 5 scored samples.
**Validates: Requirements 9.1**

### Property 15: Version Creation
*For any* version save operation, a new version should be created with correct timestamp and calculated average score.
**Validates: Requirements 10.1**

### Property 16: Version Sorting
*For any* version list display, versions should be sorted by creation time in descending order (newest first).
**Validates: Requirements 10.2**

### Property 17: Version Loading Restores State
*For any* version load operation, the loaded Prompt and dataset should match the saved version's data exactly.
**Validates: Requirements 10.3**

### Property 18: Version Comparison Shows Differences
*For any* two versions being compared, the diff should correctly identify text additions, deletions, and modifications.
**Validates: Requirements 10.5**

## Error Handling

### Frontend Errors
- **Network Errors**: 显示重试按钮和错误提示
- **Validation Errors**: 实时表单验证，阻止无效提交
- **File Upload Errors**: 显示具体错误原因（格式、大小等）

### Backend Errors
- **Model API Errors**: 返回具体错误信息，支持重试
- **Storage Errors**: 自动备份，返回恢复选项
- **Rate Limiting**: 队列处理，显示等待状态

### Error Response Format
```json
{
  "error": true,
  "code": "MODEL_API_ERROR",
  "message": "模型调用失败，请稍后重试",
  "details": "Connection timeout after 30s",
  "retry_after": 5
}
```

## Testing Strategy

### Unit Tests
- 变量检测函数测试
- 评分验证函数测试
- 统计计算函数测试
- 数据模型序列化/反序列化测试

### Property-Based Tests
使用 **Hypothesis** (Python) 进行属性测试：
- 变量检测的完整性和顺序性
- 评分范围验证
- 分页计算正确性
- 排序稳定性

### Integration Tests
- API 端到端测试
- 文件导入导出测试
- 模型调用集成测试

### Test Configuration
- 每个属性测试运行至少 100 次迭代
- 测试注释格式: `**Feature: prompt-optimization, Property {number}: {property_text}**`
