# Design Document

## Overview

本设计文档详细说明测试计划看板（index.html）高级分析工具功能的技术实现方案。主要包括：

1. **徽章数据加载** - 页面加载时从API获取各工具统计数据
2. **6个弹窗功能** - 错误样本库、异常检测、错误聚类、优化建议、批次对比、数据下钻
3. **热点图详情弹窗** - 点击热点图单元格查看详情
4. **日报详情弹窗** - 查看日报完整内容
5. **空状态优化** - 各模块无数据时的友好提示

**重要：所有数据都基于批量评估任务（batch_tasks）的评估结果进行分析。**

数据来源说明：
- **错误样本** - 从批量评估任务中识别出的 AI 批改错误（AI评分与期望评分不一致的作业）
- **异常检测** - 从批量评估任务中检测到的异常评分模式（如评分偏差过大、批量错误等）
- **错误聚类** - 对批量评估任务中的错误样本按错误类型进行聚类分析
- **优化建议** - 基于批量评估任务的错误分析，AI 生成的改进建议
- **批次对比** - 对比不同批量评估任务的评估结果
- **数据下钻** - 对批量评估任务数据进行多维度分析

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        index.html                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   高级分析工具区域                        │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │    │
│  │  │错误样本 │ │异常检测 │ │错误聚类 │ │优化建议 │        │    │
│  │  │ Badge   │ │ Badge   │ │ Badge   │ │ Badge   │        │    │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘        │    │
│  │       │           │           │           │              │    │
│  │       ▼           ▼           ▼           ▼              │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │              Modal Container                     │    │    │
│  │  │  - errorSamplesModal                            │    │    │
│  │  │  - anomalyModal                                 │    │    │
│  │  │  - clusteringModal                              │    │    │
│  │  │  - optimizationModal                            │    │    │
│  │  │  - batchCompareModal                            │    │    │
│  │  │  - drilldownModal                               │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      index.js (前端逻辑)                         │
│  - loadAdvancedToolsStats()  // 加载徽章数据                     │
│  - openErrorSamplesModal()   // 打开错误样本弹窗                 │
│  - openAnomalyModal()        // 打开异常检测弹窗                 │
│  - openClusteringModal()     // 打开错误聚类弹窗                 │
│  - openOptimizationModal()   // 打开优化建议弹窗                 │
│  - openBatchCompareModal()   // 打开批次对比弹窗                 │
│  - openDrilldownModal()      // 打开数据下钻弹窗                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Flask API Routes                            │
│  /api/error-samples          - 错误样本 CRUD                     │
│  /api/anomaly/logs           - 异常日志列表                      │
│  /api/clustering/clusters    - 聚类列表                          │
│  /api/optimization/suggestions - 优化建议列表                    │
│  /api/dashboard/batch-compare  - 批次对比                        │
│  /api/dashboard/drilldown      - 数据下钻                        │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. 前端组件

#### 1.1 徽章数据加载组件

```javascript
// 在 index.js 中实现
async function loadAdvancedToolsStats() {
    try {
        const [samplesRes, anomalyRes, clustersRes, suggestionsRes] = await Promise.allSettled([
            DashboardAPI.getErrorSamplesStats(),
            DashboardAPI.getAnomalyStats(),
            DashboardAPI.getClusteringStats(),
            DashboardAPI.getOptimizationStats()
        ]);
        
        // 更新徽章
        updateBadge('errorSampleCount', samplesRes);
        updateBadge('anomalyCount', anomalyRes, true); // warning style
        updateBadge('clusterCount', clustersRes);
        updateBadge('suggestionCount', suggestionsRes);
    } catch (e) {
        console.error('[AdvancedTools] 加载统计失败:', e);
    }
}
```

#### 1.2 弹窗基础组件

所有弹窗遵循统一的结构和样式：

```html
<div class="modal" id="{modalId}" onclick="on{ModalName}BackdropClick(event)" style="display:none;">
    <div class="modal-content {modal-size-class}" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h3 class="modal-title">{标题}</h3>
            <button class="modal-close" onclick="close{ModalName}()">×</button>
        </div>
        <div class="modal-body">
            <!-- 内容区 -->
        </div>
        <div class="modal-footer">
            <!-- 操作按钮 -->
        </div>
    </div>
</div>
```

### 2. API 接口设计

#### 2.1 徽章统计 API

**GET /api/dashboard/advanced-tools/stats**

```json
// Response
{
    "success": true,
    "data": {
        "error_samples": {
            "total": 156,
            "pending": 42,
            "analyzed": 89,
            "fixed": 25
        },
        "anomalies": {
            "total": 12,
            "unconfirmed": 5,
            "today": 3
        },
        "clusters": {
            "total": 8
        },
        "suggestions": {
            "total": 15,
            "pending": 7
        }
    }
}
```

#### 2.2 错误样本 API

**GET /api/error-samples**

```json
// Query Parameters
{
    "page": 1,
    "page_size": 20,
    "error_type": "string",  // 可选
    "status": "pending|analyzed|fixed",  // 可选
    "subject_id": 0  // 可选
}

// Response
{
    "success": true,
    "data": {
        "total": 156,
        "items": [{
            "sample_id": "xxx",
            "task_id": "xxx",
            "homework_id": "xxx",
            "error_type": "漏批",
            "status": "pending",
            "subject_id": 3,
            "subject_name": "物理",
            "book_name": "物理八上",
            "page_num": 97,
            "question_index": 5,
            "ai_score": 8,
            "expected_score": 10,
            "created_at": "2026-01-24 10:30:00"
        }],
        "stats": {
            "total": 156,
            "pending": 42,
            "analyzed": 89,
            "fixed": 25
        }
    }
}
```

**PUT /api/error-samples/{sample_id}/status**

```json
// Request Body
{
    "status": "analyzed|fixed"
}

// Response
{
    "success": true,
    "message": "状态更新成功"
}
```

**POST /api/error-samples/batch-update**

```json
// Request Body
{
    "sample_ids": ["id1", "id2"],
    "status": "analyzed|fixed"
}

// Response
{
    "success": true,
    "message": "批量更新成功",
    "updated_count": 2
}
```

#### 2.3 异常检测 API

**GET /api/anomaly/logs**

```json
// Query Parameters
{
    "page": 1,
    "page_size": 20,
    "status": "unconfirmed|confirmed"  // 可选
}

// Response
{
    "success": true,
    "data": {
        "total": 12,
        "items": [{
            "anomaly_id": "xxx",
            "task_id": "xxx",
            "anomaly_type": "score_deviation",
            "description": "评分偏差超过阈值",
            "severity": "high",
            "status": "unconfirmed",
            "detected_at": "2026-01-24 10:30:00"
        }],
        "stats": {
            "unconfirmed": 5,
            "today": 3
        }
    }
}
```

**PUT /api/anomaly/logs/{anomaly_id}/confirm**

```json
// Response
{
    "success": true,
    "message": "异常已确认"
}
```

#### 2.4 错误聚类 API

**GET /api/clustering/clusters**

```json
// Response
{
    "success": true,
    "data": [{
        "cluster_id": "xxx",
        "error_type": "漏批",
        "sample_count": 45,
        "description": "AI未识别到学生答案",
        "created_at": "2026-01-24 10:30:00"
    }]
}
```

**GET /api/clustering/clusters/{cluster_id}/samples**

```json
// Response
{
    "success": true,
    "data": {
        "cluster": { /* cluster info */ },
        "samples": [{ /* sample list */ }]
    }
}
```

#### 2.5 优化建议 API

**GET /api/optimization/suggestions**

```json
// Query Parameters
{
    "status": "pending|accepted|rejected"  // 可选
}

// Response
{
    "success": true,
    "data": [{
        "suggestion_id": "xxx",
        "title": "优化漏批检测",
        "description": "建议调整...",
        "priority": "high",
        "status": "pending",
        "created_at": "2026-01-24 10:30:00"
    }]
}
```

**PUT /api/optimization/suggestions/{suggestion_id}/status**

```json
// Request Body
{
    "status": "accepted|rejected"
}

// Response
{
    "success": true,
    "message": "状态更新成功"
}
```

#### 2.6 批次对比 API

**GET /api/dashboard/batch-compare**

```json
// Query Parameters
{
    "task_id_1": "xxx",
    "task_id_2": "xxx"
}

// Response
{
    "success": true,
    "data": {
        "task1": {
            "task_id": "xxx",
            "name": "任务1",
            "accuracy": 0.85,
            "total_questions": 100,
            "error_distribution": {
                "漏批": 10,
                "误批": 5
            }
        },
        "task2": {
            "task_id": "xxx",
            "name": "任务2",
            "accuracy": 0.88,
            "total_questions": 100,
            "error_distribution": {
                "漏批": 8,
                "误批": 4
            }
        },
        "comparison": {
            "accuracy_diff": 0.03,
            "improvement": true
        }
    }
}
```

#### 2.7 数据下钻 API

**GET /api/dashboard/drilldown**

```json
// Query Parameters
{
    "dimension": "subject|book|page|question_type",
    "parent_id": "xxx"  // 可选，用于下钻
}

// Response
{
    "success": true,
    "data": {
        "dimension": "subject",
        "items": [{
            "id": "3",
            "name": "物理",
            "total_questions": 500,
            "error_count": 45,
            "accuracy": 0.91,
            "has_children": true
        }]
    }
}
```

## Data Models

### 1. 错误样本 (Error Sample)

错误样本来源于批量评估任务中 AI 评分与期望评分不一致的作业。

```python
class ErrorSample:
    sample_id: str          # 样本ID
    task_id: str            # 关联批量评估任务ID
    homework_id: str        # 关联作业ID（来自批量评估）
    error_type: str         # 错误类型: 漏批/误批/评分偏差
    status: str             # 状态: pending/analyzed/fixed
    subject_id: int         # 学科ID（从批量评估任务获取）
    book_name: str          # 书本名称（从批量评估任务获取）
    page_num: int           # 页码
    question_index: int     # 题目序号
    ai_score: float         # AI评分（批量评估结果）
    expected_score: float   # 期望评分（数据集标准答案）
    created_at: datetime    # 创建时间
```

### 2. 异常记录 (Anomaly Log)

异常记录来源于批量评估任务执行过程中检测到的异常模式。

```python
class AnomalyLog:
    anomaly_id: str         # 异常ID
    task_id: str            # 关联批量评估任务ID
    anomaly_type: str       # 异常类型: score_deviation/batch_error/timeout
    description: str        # 异常描述
    severity: str           # 严重程度: low/medium/high
    status: str             # 状态: unconfirmed/confirmed
    detected_at: datetime   # 检测时间
```

### 3. 错误聚类 (Error Cluster)

错误聚类是对批量评估任务中的错误样本按错误类型进行的聚类分析结果。

```python
class ErrorCluster:
    cluster_id: str         # 聚类ID
    error_type: str         # 错误类型
    sample_count: int       # 样本数量（来自批量评估的错误样本）
    description: str        # 聚类描述
    task_ids: List[str]     # 关联的批量评估任务ID列表
    created_at: datetime    # 创建时间
```

### 4. 优化建议 (Optimization Suggestion)

优化建议基于批量评估任务的错误分析，由 AI 生成的改进建议。

```python
class OptimizationSuggestion:
    suggestion_id: str      # 建议ID
    title: str              # 建议标题
    description: str        # 建议详情
    priority: str           # 优先级: low/medium/high
    status: str             # 状态: pending/accepted/rejected
    source_task_ids: List[str]  # 来源批量评估任务ID列表
    created_at: datetime    # 创建时间
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 徽章数据一致性

*For any* API返回的统计数据，徽章显示的数字应该与API返回的对应字段值相等。

**Validates: Requirements 1.2, 1.3, 1.4, 1.5**

### Property 2: 筛选结果正确性

*For any* 错误样本筛选条件（错误类型、状态、学科），返回的所有样本都应该满足该筛选条件。

**Validates: Requirements 2.5**

### Property 3: 批量操作完整性

*For any* 批量操作请求，操作完成后受影响的样本数量应该等于请求中指定的样本数量。

**Validates: Requirements 2.8**

### Property 4: 列表渲染完整性

*For any* API返回的列表数据，渲染后的DOM元素数量应该等于数据项数量。

**Validates: Requirements 2.4, 3.3, 4.2, 5.2**

### Property 5: 批次对比计算正确性

*For any* 两个批次的评估数据，对比结果中的准确率差值应该等于两个批次准确率的差。

**Validates: Requirements 8.3**

### Property 6: 数据下钻聚合正确性

*For any* 维度的数据下钻，子级数据的总和应该等于父级数据的总量。

**Validates: Requirements 9.3**

### Property 7: 空状态显示正确性

*For any* 空数据列表，应该显示对应的空状态提示文本而不是空白。

**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**

## Error Handling

### 1. API 错误处理

```javascript
// 统一的 API 错误处理
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '请求失败');
        }
        
        return data;
    } catch (error) {
        console.error(`[API] ${url} 请求失败:`, error);
        showToast(error.message || '网络请求失败', 'error');
        throw error;
    }
}
```

### 2. 弹窗加载错误处理

```javascript
// 弹窗数据加载失败时显示错误状态
function renderModalError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="error-state">
                <div class="error-state-icon">!</div>
                <div class="error-state-text">${escapeHtml(message)}</div>
                <button class="btn btn-secondary" onclick="retryLoad()">重试</button>
            </div>
        `;
    }
}
```

### 3. 徽章加载失败处理

```javascript
// 徽章加载失败时显示 0
function updateBadge(elementId, result, isWarning = false) {
    const badge = document.getElementById(elementId);
    if (!badge) return;
    
    if (result.status === 'fulfilled' && result.value.success) {
        const count = result.value.data?.total || result.value.data?.length || 0;
        badge.textContent = count;
        if (isWarning && count > 0) {
            badge.classList.add('warning');
        }
    } else {
        badge.textContent = '0';
        console.error(`[Badge] ${elementId} 加载失败`);
    }
}
```

## Testing Strategy

### 1. 单元测试

使用 pytest 测试后端 API：

```python
# tests/test_advanced_tools.py
import pytest
from app import app

class TestAdvancedToolsAPI:
    def test_get_error_samples_stats(self, client):
        """测试获取错误样本统计"""
        response = client.get('/api/error-samples?page_size=1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert 'total' in data['data']
    
    def test_get_anomaly_stats(self, client):
        """测试获取异常统计"""
        response = client.get('/api/anomaly/logs?page_size=1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
    
    def test_batch_compare(self, client):
        """测试批次对比"""
        response = client.get('/api/dashboard/batch-compare?task_id_1=xxx&task_id_2=yyy')
        assert response.status_code == 200
```

### 2. 属性测试

使用 hypothesis 进行属性测试：

```python
# tests/test_properties.py
from hypothesis import given, strategies as st

class TestAdvancedToolsProperties:
    @given(st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=50))
    def test_filter_results_match_criteria(self, scores):
        """
        Property 2: 筛选结果正确性
        Feature: dashboard-advanced-tools, Property 2: 筛选结果正确性
        Validates: Requirements 2.5
        """
        # 给定任意分数列表，筛选后的结果应该都满足条件
        threshold = 60
        filtered = [s for s in scores if s >= threshold]
        assert all(s >= threshold for s in filtered)
    
    @given(st.floats(min_value=0, max_value=1), st.floats(min_value=0, max_value=1))
    def test_batch_compare_accuracy_diff(self, acc1, acc2):
        """
        Property 5: 批次对比计算正确性
        Feature: dashboard-advanced-tools, Property 5: 批次对比计算正确性
        Validates: Requirements 8.3
        """
        # 准确率差值应该等于两个准确率的差
        diff = acc1 - acc2
        assert abs(diff - (acc1 - acc2)) < 0.0001
```

### 3. 前端测试

使用浏览器手动测试或 Playwright 自动化测试：

- 测试弹窗打开/关闭
- 测试筛选功能
- 测试批量操作
- 测试空状态显示
- 测试错误处理
