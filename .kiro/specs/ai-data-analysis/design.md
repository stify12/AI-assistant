# Design Document

## Overview

本设计文档详细说明 AI 智能数据分析功能的技术实现方案。系统在批量评估任务完成后自动触发大模型分析，支持多层级粒度（学科→书本→页码→题目）的错误分析、根因识别和优化建议生成。同时提供自动化任务管理界面，支持配置和监控所有自动化任务。

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Flask Application                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │  batch_evaluation │    │    dashboard     │    │   automation     │       │
│  │     routes        │    │     routes       │    │    routes        │       │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘       │
│           │                       │                       │                  │
│           ▼                       ▼                       ▼                  │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │                        Service Layer                              │       │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │       │
│  │  │ AI_Analysis     │  │ Automation      │  │ LLM_Service     │   │       │
│  │  │ Service         │  │ Service         │  │                 │   │       │
│  │  │                 │  │                 │  │ - DeepSeek V3.2 │   │       │
│  │  │ - analyze_task  │  │ - get_tasks     │  │ - Qwen3 Max     │   │       │
│  │  │ - drill_down    │  │ - update_config │  │                 │   │       │
│  │  │ - get_report    │  │ - get_queue     │  │                 │   │       │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘   │       │
│  │           │                    │                    │            │       │
│  └───────────┼────────────────────┼────────────────────┼────────────┘       │
│              │                    │                    │                     │
│              ▼                    ▼                    ▼                     │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │                      Analysis Queue (内存队列)                    │       │
│  │  - 任务队列管理                                                   │       │
│  │  - 并发控制                                                       │       │
│  │  - 状态追踪                                                       │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Storage                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  MySQL          │  │  JSON Files     │  │  Config         │              │
│  │  - analysis_    │  │  - batch_tasks/ │  │  - automation_  │              │
│  │    reports      │  │                 │  │    config.json  │              │
│  │  - automation_  │  │                 │  │                 │              │
│  │    logs         │  │                 │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. AI 分析服务 (ai_analysis_service.py)

```python
class AIAnalysisService:
    """AI 数据分析服务"""
    
    # 分析队列
    _queue: List[str] = []  # 待分析任务ID列表
    _running: Dict[str, dict] = {}  # 正在执行的分析 {task_id: status}
    _max_concurrent: int = 2  # 最大并发数
    
    @staticmethod
    def trigger_analysis(task_id: str) -> dict:
        """
        触发任务分析（任务完成时调用）
        
        Args:
            task_id: 批量评估任务ID
            
        Returns:
            dict: {queued: bool, position: int, message: str}
        """
        pass
    
    @staticmethod
    def analyze_task(task_id: str) -> dict:
        """
        执行任务分析
        
        Returns:
            dict: {
                report_id: str,
                task_id: str,
                summary: {...},
                drill_down: {...},
                error_patterns: [...],
                root_causes: [...],
                suggestions: [...]
            }
        """
        pass
    
    @staticmethod
    def get_drill_down_data(task_id: str, level: str, parent_id: str = None) -> dict:
        """
        获取下钻数据
        
        Args:
            task_id: 任务ID
            level: 层级 subject|book|page|question
            parent_id: 父级ID（用于下钻）
            
        Returns:
            dict: {level, items: [{id, name, error_count, error_rate, has_children}]}
        """
        pass
    
    @staticmethod
    def get_analysis_report(task_id: str) -> dict:
        """获取分析报告"""
        pass
    
    @staticmethod
    def retry_analysis(task_id: str) -> dict:
        """重新分析"""
        pass
```

### 2. 自动化管理服务 (automation_service.py)

```python
class AutomationService:
    """自动化任务管理服务"""
    
    @staticmethod
    def get_all_tasks() -> List[dict]:
        """
        获取所有自动化任务列表
        
        Returns:
            list: [{
                task_type: str,  # ai_analysis|daily_report|stats_snapshot
                name: str,
                description: str,
                trigger_type: str,  # event|cron|manual
                status: str,  # enabled|disabled|running|waiting
                last_run: str,
                last_result: str,  # success|failed
                next_run: str,
                stats: {today, week, month}
            }]
        """
        pass
    
    @staticmethod
    def get_task_config(task_type: str) -> dict:
        """获取任务配置"""
        pass
    
    @staticmethod
    def update_task_config(task_type: str, config: dict) -> dict:
        """更新任务配置"""
        pass
    
    @staticmethod
    def get_task_history(task_type: str, limit: int = 50) -> List[dict]:
        """获取任务执行历史"""
        pass
    
    @staticmethod
    def get_queue_status() -> dict:
        """
        获取队列状态
        
        Returns:
            dict: {
                waiting: int,
                running: [{task_id, task_type, started_at}],
                recent: [{task_id, task_type, completed_at, result}]
            }
        """
        pass
    
    @staticmethod
    def pause_all() -> bool:
        """暂停所有自动任务"""
        pass
    
    @staticmethod
    def resume_all() -> bool:
        """恢复所有自动任务"""
        pass
    
    @staticmethod
    def clear_queue() -> int:
        """清空等待队列，返回清除数量"""
        pass
```

### 3. API 接口设计

#### 3.1 分析报告 API

**POST /api/analysis/trigger/{task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "queued": true,
        "position": 1,
        "message": "分析任务已加入队列"
    }
}
```

**GET /api/analysis/report/{task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "report_id": "xxx",
        "task_id": "xxx",
        "status": "completed",  // pending|analyzing|completed|failed
        "created_at": "2026-01-24 16:00:00",
        "summary": {
            "total_errors": 156,
            "error_rate": 0.18,
            "main_issues": ["物理力学题漏批率高", "化学方程式配平误判"]
        },
        "drill_down": {
            "level": "subject",
            "items": [
                {"id": "3", "name": "物理", "error_count": 89, "error_rate": 0.22, "is_focus": true, "has_children": true},
                {"id": "4", "name": "化学", "error_count": 45, "error_rate": 0.15, "is_focus": false, "has_children": true}
            ]
        },
        "error_patterns": [
            {
                "pattern_id": "p1",
                "type": "识别错误-判断错误",
                "count": 45,
                "percentage": 0.29,
                "severity": "high",
                "description": "手写体识别不准确导致判断错误",
                "examples": [
                    {"homework_id": "xxx", "question": "第5题", "ai_answer": "...", "expected": "..."}
                ]
            }
        ],
        "root_causes": [
            {
                "cause_type": "ocr_issue",
                "name": "OCR识别问题",
                "count": 67,
                "percentage": 0.43,
                "is_main": true,
                "sub_causes": [
                    {"name": "手写体识别差", "count": 45},
                    {"name": "特殊符号识别错误", "count": 22}
                ],
                "evidence": [
                    {"homework_id": "xxx", "description": "学生手写'力'被识别为'刀'"}
                ]
            }
        ],
        "suggestions": [
            {
                "suggestion_id": "s1",
                "title": "优化手写体识别容错",
                "description": "在 prompt 中增加对手写体的容错处理...",
                "priority": "high",
                "expected_effect": "预计可减少 30% 的识别错误",
                "related_cause": "ocr_issue",
                "prompt_suggestion": "建议在评分 prompt 中添加：'对于手写体答案，请考虑常见的书写变体...'"
            }
        ]
    }
}
```

**GET /api/analysis/drilldown/{task_id}**
```json
// Query: level=book&parent_id=3
// Response
{
    "success": true,
    "data": {
        "level": "book",
        "parent": {"id": "3", "name": "物理"},
        "items": [
            {"id": "physics_8a", "name": "物理八上", "error_count": 56, "error_rate": 0.25, "is_focus": true, "has_children": true},
            {"id": "physics_8b", "name": "物理八下", "error_count": 33, "error_rate": 0.18, "is_focus": false, "has_children": true}
        ]
    }
}
```

#### 3.2 自动化管理 API

**GET /api/automation/tasks**
```json
// Response
{
    "success": true,
    "data": [
        {
            "task_type": "ai_analysis",
            "name": "AI 数据分析",
            "description": "批量评估完成后自动分析错误模式和根因",
            "trigger_type": "event",
            "status": "enabled",
            "last_run": "2026-01-24 15:30:00",
            "last_result": "success",
            "next_run": null,
            "stats": {"today": 5, "week": 23, "month": 89}
        },
        {
            "task_type": "daily_report",
            "name": "日报自动生成",
            "description": "每天 18:00 自动生成测试日报",
            "trigger_type": "cron",
            "status": "enabled",
            "last_run": "2026-01-23 18:00:00",
            "last_result": "success",
            "next_run": "2026-01-24 18:00:00",
            "stats": {"today": 0, "week": 7, "month": 30}
        }
    ]
}
```

**GET /api/automation/tasks/{task_type}/config**
```json
// Response (ai_analysis)
{
    "success": true,
    "data": {
        "enabled": true,
        "trigger_delay": 10,
        "max_concurrent": 2,
        "timeout": 300,
        "model": "deepseek-v3.2",
        "temperature": 0.3,
        "analysis_depth": "full"  // basic|with_root_cause|full
    }
}
```

**PUT /api/automation/tasks/{task_type}/config**
```json
// Request
{
    "enabled": true,
    "trigger_delay": 15,
    "model": "qwen3-max"
}
// Response
{
    "success": true,
    "message": "配置已更新"
}
```

**GET /api/automation/queue**
```json
// Response
{
    "success": true,
    "data": {
        "waiting": 2,
        "running": [
            {"task_id": "xxx", "task_type": "ai_analysis", "started_at": "2026-01-24 16:00:00", "progress": 45}
        ],
        "recent": [
            {"task_id": "yyy", "task_type": "ai_analysis", "completed_at": "2026-01-24 15:55:00", "result": "success", "duration": 120}
        ]
    }
}
```

**POST /api/automation/pause**
**POST /api/automation/resume**
**POST /api/automation/queue/clear**

## Data Models

### 1. 分析报告 (analysis_reports)

```sql
CREATE TABLE analysis_reports (
    report_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    status ENUM('pending', 'analyzing', 'completed', 'failed') DEFAULT 'pending',
    summary JSON,           -- 摘要信息
    drill_down_data JSON,   -- 层级分析数据
    error_patterns JSON,    -- 错误模式列表
    root_causes JSON,       -- 根因分析结果
    suggestions JSON,       -- 优化建议列表
    error_message TEXT,     -- 错误信息（失败时）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    duration_seconds INT,   -- 分析耗时
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
);
```

### 2. 自动化任务日志 (automation_logs)

```sql
CREATE TABLE automation_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,  -- ai_analysis|daily_report|stats_snapshot
    related_id VARCHAR(36),          -- 关联的任务ID
    status ENUM('started', 'completed', 'failed') NOT NULL,
    message TEXT,
    duration_seconds INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_type (task_type),
    INDEX idx_created_at (created_at)
);
```

### 3. 自动化配置 (automation_config.json)

```json
{
    "ai_analysis": {
        "enabled": true,
        "trigger_delay": 10,
        "max_concurrent": 2,
        "timeout": 300,
        "model": "deepseek-v3.2",
        "temperature": 0.3,
        "analysis_depth": "full"
    },
    "daily_report": {
        "enabled": true,
        "cron": "0 18 * * *",
        "time_range": "today"
    },
    "stats_snapshot": {
        "enabled": true,
        "cron": "0 0 * * *",
        "retention_days": 30
    },
    "global": {
        "paused": false
    }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 任务完成触发分析

*For any* 批量评估任务，当其状态变为 completed 时，应该触发一次且仅一次分析任务（加入队列或直接执行）。

**Validates: Requirements 1.1**

### Property 2: 错误样本收集完整性

*For any* 批量评估任务的分析，收集的错误样本数量应该等于该任务中所有 AI 评分与期望评分不一致的作业数量。

**Validates: Requirements 1.2**

### Property 3: 层级聚合正确性

*For any* 分析报告的层级数据，子级的错误数量之和应该等于父级的错误数量。

**Validates: Requirements 2.1, 2.3**

### Property 4: 错误率计算正确性

*For any* 层级节点，其错误率应该等于该节点的错误数量除以该节点的总题目数量。

**Validates: Requirements 2.3**

### Property 5: 重点关注标记正确性

*For any* 层级节点，当且仅当其错误率超过 20% 时，应该被标记为重点关注（is_focus=true）。

**Validates: Requirements 2.4**

### Property 6: Top 5 排序正确性

*For any* 分析报告的 Top 5 错误位置，应该按错误数量降序排列，且数量不超过 5 个。

**Validates: Requirements 2.5, 3.2**

### Property 7: 错误类型分类有效性

*For any* 错误模式，其类型应该属于预定义的类型集合（识别错误-判断错误、识别正确-判断错误、缺失题目、AI识别幻觉、答案不匹配）。

**Validates: Requirements 3.1**

### Property 8: 样本示例数量限制

*For any* 错误模式，其示例数量应该不超过 3 个。

**Validates: Requirements 3.4**

### Property 9: 严重程度有效性

*For any* 错误模式，其严重程度应该是 high、medium、low 之一。

**Validates: Requirements 3.5**

### Property 10: 根因分类有效性

*For any* 根因分析结果，其类型应该属于预定义的类型集合（OCR识别问题、评分逻辑问题、标准答案问题、Prompt问题、数据问题）。

**Validates: Requirements 4.2**

### Property 11: 根因占比总和

*For any* 分析报告的根因分析，所有根因的占比之和应该等于 100%（允许 1% 误差）。

**Validates: Requirements 4.4**

### Property 12: 主要问题标记正确性

*For any* 根因，当且仅当其占比超过 30% 时，应该被标记为主要问题（is_main=true）。

**Validates: Requirements 4.5**

### Property 13: 建议结构完整性

*For any* 优化建议，应该包含 title、description、priority、expected_effect、related_cause 字段。

**Validates: Requirements 5.2**

### Property 14: 建议优先级排序

*For any* 分析报告的建议列表，应该按优先级（high > medium > low）排序。

**Validates: Requirements 5.4**

### Property 15: 建议数量限制

*For any* 分析报告，其优化建议数量应该不超过 5 个。

**Validates: Requirements 5.5**

### Property 16: 配置即时生效

*For any* 配置更新操作，更新后立即读取配置应该返回更新后的值。

**Validates: Requirements 9.4**

## Error Handling

### 1. 分析任务错误处理

```python
class AnalysisError(Exception):
    """分析错误基类"""
    pass

class LLMCallError(AnalysisError):
    """大模型调用错误"""
    pass

class DataCollectionError(AnalysisError):
    """数据收集错误"""
    pass

class TimeoutError(AnalysisError):
    """分析超时"""
    pass

def handle_analysis_error(task_id: str, error: Exception):
    """
    处理分析错误
    1. 记录错误日志
    2. 更新报告状态为 failed
    3. 记录错误信息
    4. 支持重试
    """
    report = get_or_create_report(task_id)
    report.status = 'failed'
    report.error_message = str(error)
    save_report(report)
    
    log_automation_event('ai_analysis', task_id, 'failed', str(error))
```

### 2. 队列错误处理

```python
def process_queue():
    """处理分析队列"""
    while True:
        if is_paused():
            time.sleep(1)
            continue
            
        task_id = get_next_task()
        if not task_id:
            time.sleep(1)
            continue
        
        try:
            with timeout(get_config('timeout')):
                analyze_task(task_id)
        except TimeoutError:
            handle_analysis_error(task_id, TimeoutError("分析超时"))
        except Exception as e:
            handle_analysis_error(task_id, e)
        finally:
            remove_from_running(task_id)
```

## Testing Strategy

### 1. 单元测试

使用 pytest 测试核心逻辑：

```python
# tests/test_ai_analysis.py
class TestAIAnalysisService:
    def test_trigger_analysis_adds_to_queue(self):
        """测试触发分析加入队列"""
        result = AIAnalysisService.trigger_analysis('task_123')
        assert result['queued'] == True
        
    def test_drill_down_data_structure(self):
        """测试下钻数据结构"""
        data = AIAnalysisService.get_drill_down_data('task_123', 'subject')
        assert 'level' in data
        assert 'items' in data
        
    def test_error_rate_calculation(self):
        """测试错误率计算"""
        # 10 个错误，50 个总题目
        rate = calculate_error_rate(10, 50)
        assert rate == 0.2
```

### 2. 属性测试

使用 hypothesis 进行属性测试：

```python
# tests/test_ai_analysis_properties.py
from hypothesis import given, strategies as st

class TestAnalysisProperties:
    @given(st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=10))
    def test_child_sum_equals_parent(self, child_counts):
        """
        Property 3: 层级聚合正确性
        Feature: ai-data-analysis, Property 3: 层级聚合正确性
        Validates: Requirements 2.1, 2.3
        """
        parent_count = sum(child_counts)
        assert sum(child_counts) == parent_count
    
    @given(st.integers(min_value=0, max_value=100), 
           st.integers(min_value=1, max_value=100))
    def test_error_rate_range(self, errors, total):
        """
        Property 4: 错误率计算正确性
        Feature: ai-data-analysis, Property 4: 错误率计算正确性
        Validates: Requirements 2.3
        """
        if errors <= total:
            rate = errors / total
            assert 0 <= rate <= 1
    
    @given(st.floats(min_value=0, max_value=1))
    def test_focus_threshold(self, error_rate):
        """
        Property 5: 重点关注标记正确性
        Feature: ai-data-analysis, Property 5: 重点关注标记正确性
        Validates: Requirements 2.4
        """
        is_focus = error_rate > 0.2
        assert is_focus == (error_rate > 0.2)
    
    @given(st.lists(st.floats(min_value=0, max_value=1), min_size=1, max_size=5))
    def test_root_cause_percentages_sum(self, percentages):
        """
        Property 11: 根因占比总和
        Feature: ai-data-analysis, Property 11: 根因占比总和
        Validates: Requirements 4.4
        """
        # 归一化百分比
        total = sum(percentages)
        if total > 0:
            normalized = [p / total for p in percentages]
            assert abs(sum(normalized) - 1.0) < 0.01
```

### 3. 集成测试

测试完整的分析流程：

```python
class TestAnalysisIntegration:
    def test_full_analysis_flow(self, client, sample_task):
        """测试完整分析流程"""
        # 1. 触发分析
        response = client.post(f'/api/analysis/trigger/{sample_task.task_id}')
        assert response.status_code == 200
        
        # 2. 等待分析完成
        wait_for_analysis(sample_task.task_id)
        
        # 3. 获取报告
        response = client.get(f'/api/analysis/report/{sample_task.task_id}')
        assert response.status_code == 200
        data = response.get_json()['data']
        
        # 4. 验证报告结构
        assert 'summary' in data
        assert 'drill_down' in data
        assert 'error_patterns' in data
        assert 'root_causes' in data
        assert 'suggestions' in data
```
